"""
NotebookLM CLI service — wraps the `nlm` command-line tool.

All subprocess calls to nlm go through this module.
Uses asyncio.create_subprocess_exec for non-blocking execution.
"""

import asyncio
import json
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import select

from app.db_models import GenerationDB, NotebookLMJobDB, TimelineDB

logger = logging.getLogger(__name__)

AUDIO_DIR = Path(__file__).parent.parent.parent / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

UUID_PATTERN = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')
ARTIFACT_ID_PATTERN = re.compile(r'Artifact ID:\s*([0-9a-f-]{36})', re.IGNORECASE)


async def _run_nlm(*args: str, timeout: int = 300) -> tuple[int, str, str]:
    """
    Run an nlm CLI command and return (returncode, stdout, stderr).

    Args:
        *args: Command arguments after 'nlm', e.g. ('notebook', 'create', 'Title')
        timeout: Seconds before killing the process (default 300s / 5min)

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    cmd = ["nlm"] + list(args)
    logger.debug(f"Running: {' '.join(cmd)}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"nlm command timed out after {timeout}s: {' '.join(cmd)}")

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    logger.debug(f"nlm exit={proc.returncode} stdout={stdout[:200]}")
    return proc.returncode, stdout, stderr


async def check_available() -> dict:
    """Check if nlm is installed and the session is authenticated."""
    try:
        rc, stdout, stderr = await _run_nlm("login", "--check", timeout=15)
        authenticated = rc == 0  # exit code 0 means valid auth ("Authentication valid!")
        return {"available": True, "authenticated": authenticated, "error": None}
    except FileNotFoundError:
        return {"available": False, "authenticated": False, "error": "nlm not found in PATH"}
    except Exception as e:
        return {"available": False, "authenticated": False, "error": str(e)}


async def create_notebook(title: str) -> str:
    """Create a new NotebookLM notebook. Returns the notebook ID."""
    rc, stdout, stderr = await _run_nlm("notebook", "create", title, timeout=30)
    if rc != 0:
        raise RuntimeError(f"nlm notebook create failed (rc={rc}): {stderr}")

    match = UUID_PATTERN.search(stdout)
    if not match:
        raise RuntimeError(f"Could not parse notebook ID from output: {stdout!r}")

    notebook_id = match.group(1)
    logger.info(f"Created notebook: {notebook_id}")
    return notebook_id


async def add_source(notebook_id: str, file_path: Path, title: str) -> None:
    """Upload a local file as a source and wait for processing."""
    rc, stdout, stderr = await _run_nlm(
        "source", "add", notebook_id,
        "--file", str(file_path),
        "--title", title,
        "--wait",
        timeout=120,
    )
    if rc != 0:
        raise RuntimeError(f"nlm source add failed (rc={rc}): {stderr}")
    logger.info(f"Added source '{title}' to notebook {notebook_id}")


async def create_audio(
    notebook_id: str,
    nlm_format: str,
    nlm_length: str,
    language_code: str,
    focus: Optional[str] = None,
) -> str:
    """Trigger audio generation. Returns the artifact ID."""
    args = [
        "audio", "create", notebook_id,
        "--format", nlm_format,
        "--length", nlm_length,
        "--language", language_code,
        "--confirm",
    ]
    if focus:
        args += ["--focus", focus]

    rc, stdout, stderr = await _run_nlm(*args, timeout=60)
    if rc != 0:
        raise RuntimeError(f"nlm audio create failed (rc={rc}): {stderr}")

    match = ARTIFACT_ID_PATTERN.search(stdout)
    if not match:
        raise RuntimeError(f"Could not parse artifact ID from output: {stdout!r}")

    artifact_id = match.group(1)
    logger.info(f"Audio generation started, artifact: {artifact_id}")
    return artifact_id


async def poll_status(notebook_id: str, artifact_id: str) -> str:
    """
    Check artifact status.

    Returns:
        'completed', 'in_progress', or 'failed'
    """
    rc, stdout, stderr = await _run_nlm(
        "studio", "status", notebook_id, "--json", timeout=30
    )
    if rc != 0:
        logger.warning(f"nlm studio status failed (rc={rc}): {stderr}")
        return "in_progress"  # assume still running, retry next poll

    try:
        artifacts = json.loads(stdout)
        for artifact in artifacts:
            if artifact.get("id") == artifact_id:
                status_str = artifact.get("status", "")
                if "completed" in status_str:
                    return "completed"
                elif "failed" in status_str or "error" in status_str:
                    return "failed"
                return "in_progress"
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse studio status JSON: {e}, raw: {stdout[:200]}")

    return "in_progress"


async def download_audio(notebook_id: str, artifact_id: str) -> Path:
    """Download completed audio to the audio directory. Returns the saved path."""
    output_path = AUDIO_DIR / f"{uuid4()}.m4a"
    rc, stdout, stderr = await _run_nlm(
        "download", "audio", notebook_id,
        "--id", artifact_id,
        "--output", str(output_path),
        "--no-progress",
        timeout=120,
    )
    if rc != 0:
        raise RuntimeError(f"nlm download audio failed (rc={rc}): {stderr}")
    if not output_path.exists():
        raise RuntimeError(f"Download completed but file not found at {output_path}")

    logger.info(f"Audio downloaded: {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


async def delete_notebook(notebook_id: str) -> None:
    """Delete a NotebookLM notebook (cleanup after job completes)."""
    rc, stdout, stderr = await _run_nlm("notebook", "delete", notebook_id, timeout=30)
    if rc != 0:
        logger.warning(f"Failed to delete notebook {notebook_id}: {stderr}")
    else:
        logger.info(f"Deleted notebook: {notebook_id}")


async def _export_generation_content(
    generation: GenerationDB,
    include_reports: bool,
    include_narratives: bool,
) -> str:
    """Render a generation's content as markdown text for NLM upload."""
    lines = [f"# {generation.start_year}–{generation.end_year} Alternate History Report\n"]

    if include_reports:
        report_sections = [
            ("executive_summary", "Executive Summary"),
            ("political_changes", "Political Changes"),
            ("conflicts_and_wars", "Conflicts and Wars"),
            ("economic_impacts", "Economic Impacts"),
            ("social_developments", "Social Developments"),
            ("technological_shifts", "Technological Shifts"),
            ("key_figures", "Key Figures"),
            ("long_term_implications", "Long Term Implications"),
        ]
        for field, title in report_sections:
            content = getattr(generation, field, None)
            if content:
                lines.append(f"## {title}\n\n{content}\n")

    if include_narratives and generation.narrative_prose:
        lines.append(f"## Narrative\n\n{generation.narrative_prose}\n")

    return "\n".join(lines)


async def run_notebooklm_job(job_id: str, include_reports: bool, include_narratives: bool) -> None:
    """
    Background task: runs the full NLM pipeline for a job.

    Stages:
      pending → creating (create notebook, export + upload sources)
      creating → uploading (per-source upload)
      uploading → generating (nlm audio create)
      generating → polling (wait for NLM)
      polling → completed (download, save path on job row)
      any stage → failed (on error)

    Uses a separate DB session (background tasks can't share the request session).
    audio_local_path and audio_url are stored directly on NotebookLMJobDB —
    AudioFileDB is NOT used because its script_id FK is NOT NULL.
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Load job
            result = await db.execute(
                select(NotebookLMJobDB).where(NotebookLMJobDB.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job not found: {job_id}")
                return

            job.status = "creating"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Load generations
            gen_result = await db.execute(
                select(GenerationDB).where(GenerationDB.id.in_(job.generation_ids))
            )
            generations = gen_result.scalars().all()
            if not generations:
                raise RuntimeError("No generations found for job")

            # Determine notebook title from timeline name
            timeline_name = None
            if job.timeline_id:
                tl_result = await db.execute(
                    select(TimelineDB).where(TimelineDB.id == job.timeline_id)
                )
                tl = tl_result.scalar_one_or_none()
                if tl:
                    timeline_name = tl.timeline_name or tl.root_deviation_description[:50]
            title = f"DE — {timeline_name}" if timeline_name else "Deviation Engine"

            # Create notebook
            notebook_id = await create_notebook(title)
            job.notebook_id = notebook_id
            await db.commit()

            # Export + upload each generation as a separate source
            job.status = "uploading"
            await db.commit()

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                for gen in sorted(generations, key=lambda g: g.start_year):
                    content = await _export_generation_content(gen, include_reports, include_narratives)
                    source_title = f"{gen.start_year}–{gen.end_year}"
                    file_path = tmpdir_path / f"{gen.id}.md"
                    file_path.write_text(content, encoding="utf-8")
                    await add_source(notebook_id, file_path, source_title)

                # Trigger audio generation
                job.status = "generating"
                await db.commit()

                artifact_id = await create_audio(
                    notebook_id=notebook_id,
                    nlm_format=job.nlm_format,
                    nlm_length=job.nlm_length,
                    language_code=job.language_code,
                    focus=job.nlm_focus,
                )
                job.artifact_id = artifact_id
                await db.commit()

            # Poll until complete (max 30 min, check every 30s)
            job.status = "polling"
            await db.commit()

            max_polls = 60
            for poll_num in range(max_polls):
                await asyncio.sleep(30)
                status = await poll_status(notebook_id, artifact_id)
                logger.info(f"Job {job_id} poll {poll_num + 1}/{max_polls}: {status}")

                if status == "completed":
                    break
                elif status == "failed":
                    raise RuntimeError("NotebookLM reported generation failure")
            else:
                raise RuntimeError("Timed out waiting for NotebookLM (30 min)")

            # Download audio
            audio_path = await download_audio(notebook_id, artifact_id)

            # Rename to a stable UUID-based filename
            final_filename = f"{uuid4()}.m4a"
            final_path = AUDIO_DIR / final_filename
            audio_path.rename(final_path)

            now = datetime.now(timezone.utc)
            job.audio_local_path = str(final_path.absolute())
            job.audio_url = f"/audio/{final_filename}"
            job.status = "completed"
            job.completed_at = now
            await db.commit()

            logger.info(f"NLM job {job_id} completed: audio={final_filename}")

            # Cleanup: delete the notebook from NotebookLM (non-fatal — never corrupt completed status)
            try:
                await delete_notebook(notebook_id)
            except Exception as cleanup_err:
                logger.warning(f"Notebook cleanup failed (non-fatal): {cleanup_err}")

        except Exception as e:
            logger.error(f"NLM job {job_id} failed: {e}", exc_info=True)
            try:
                result = await db.execute(
                    select(NotebookLMJobDB).where(NotebookLMJobDB.id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    await db.commit()
            except Exception as inner:
                logger.error(f"Failed to update job status to failed: {inner}")
