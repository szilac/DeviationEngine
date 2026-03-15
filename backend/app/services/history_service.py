"""
Historical ground truth service for loading and managing historical reports.

This service provides two modes for loading historical context:
1. **RAG Mode** (default): Uses vector store for semantic retrieval (~99% token reduction)
2. **Legacy Mode** (fallback): Loads full markdown files

The service automatically falls back to legacy mode if RAG is unavailable.

Files are automatically discovered by scanning the ground_truth directory.
Expected filename format: YYYY-YYYY.md (e.g., "1900-1910.md", "1880-1890.md")
"""

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import re
import os

from app.exceptions import HistoricalContextError

# Configure logging
logger = logging.getLogger(__name__)

# Cache for loaded reports to avoid repeated file I/O
_reports_cache: Dict[str, str] = {}

# Cache for scanned period files to avoid repeated directory scanning
_periods_cache: Optional[List[Dict]] = None


class HistoryService:
    """
    Service for managing historical ground truth reports.

    Loads markdown files containing historical summaries and provides
    them based on date ranges for timeline generation context.
    """

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize the history service.

        Args:
            data_dir: Path to the data directory containing ground_truth folder.
                     If None, uses default path relative to this file.
        """
        if data_dir is None:
            # Default: backend/data/ground_truth/
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "ground_truth"
        else:
            self.data_dir = Path(data_dir)

        if not self.data_dir.exists():
            logger.error(f"Ground truth data directory not found: {self.data_dir}")
            raise HistoricalContextError(
                f"Ground truth data directory not found: {self.data_dir}",
                details={"data_dir": str(self.data_dir)}
            )

        # Scan available reports on initialization
        self._scan_available_reports()

    def _scan_available_reports(self) -> List[Dict]:
        """
        Scan the ground_truth directory for available report files.

        Returns a list of period dictionaries with start, end, and filename.
        Expected filename format: YYYY-YYYY.md (e.g., "1880-1890.md")

        Returns:
            List of dicts with 'start', 'end', and 'file' keys
        """
        global _periods_cache

        # Return cached periods if available
        if _periods_cache is not None:
            return _periods_cache

        periods = []

        # Pattern to match YYYY-YYYY.md files
        filename_pattern = re.compile(r"^(\d{4})-(\d{4})\.md$")

        try:
            for file_path in self.data_dir.glob("*.md"):
                match = filename_pattern.match(file_path.name)
                if match:
                    start_year = int(match.group(1))
                    end_year = int(match.group(2))
                    periods.append({
                        "start": start_year,
                        "end": end_year,
                        "file": file_path.name
                    })
                else:
                    logger.debug(f"Skipping file with non-standard name: {file_path.name}")

            # Sort by start year
            periods.sort(key=lambda p: p["start"])

            # Cache the results
            _periods_cache = periods

            logger.info(
                f"Scanned {len(periods)} ground truth reports from {self.data_dir}",
                extra={"report_count": len(periods), "data_dir": str(self.data_dir)}
            )

        except Exception as e:
            logger.error(f"Error scanning ground truth directory: {e}", exc_info=True)

        return periods

    def load_report(self, filename: str) -> str:
        """
        Load a historical report from file with caching.

        Args:
            filename: Name of the markdown file to load (e.g., "1900-1910.md")

        Returns:
            Content of the historical report

        Raises:
            FileNotFoundError: If the report file doesn't exist
            IOError: If there's an error reading the file
        """
        # Check cache first
        if filename in _reports_cache:
            logger.debug(f"Loading report from cache: {filename}")
            return _reports_cache[filename]

        # Load from file
        file_path = self.data_dir / filename
        if not file_path.exists():
            logger.warning(f"Historical report not found: {file_path}")
            raise HistoricalContextError(
                f"Historical report not found: {filename}",
                details={"filename": filename, "file_path": str(file_path)}
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Cache the content
            _reports_cache[filename] = content
            logger.info(
                f"Loaded and cached report: {filename}",
                extra={"report_file": filename, "content_length": len(content)}
            )
            return content

        except Exception as e:
            logger.error(
                f"Error reading report {filename}: {e}",
                exc_info=True,
                extra={"report_file": filename}
            )
            raise HistoricalContextError(
                f"Failed to read historical report: {filename}",
                details={"filename": filename, "error": str(e)}
            ) from e

    def get_reports_for_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[str]:
        """
        Get relevant historical reports for a date range.

        Dynamically scans the ground_truth directory and loads all reports
        that overlap with the specified date range.

        Args:
            start_date: Beginning of the date range
            end_date: End of the date range

        Returns:
            List of report contents covering the specified date range
        """
        reports = []
        start_year = start_date.year
        end_year = end_date.year

        # Get available report periods from directory scan
        available_periods = self._scan_available_reports()

        if not available_periods:
            logger.warning(
                f"No ground truth reports found in {self.data_dir}",
                extra={"data_dir": str(self.data_dir)}
            )
            return reports

        # Determine which reports to load based on date range overlap
        for period in available_periods:
            period_start = period["start"]
            period_end = period["end"]
            filename = period["file"]

            # Check if this period overlaps with our date range
            if period_start <= end_year and period_end >= start_year:
                try:
                    report_content = self.load_report(filename)
                    reports.append(report_content)
                    logger.debug(
                        f"Added report {filename} (covers {period_start}-{period_end}) "
                        f"for range {start_date} to {end_date}",
                        extra={
                            "report_file": filename,
                            "period_start": period_start,
                            "period_end": period_end,
                            "start_date": str(start_date),
                            "end_date": str(end_date)
                        }
                    )
                except HistoricalContextError:
                    logger.warning(
                        f"Report not found: {filename}, skipping",
                        extra={"report_file": filename}
                    )
                    # Continue with other reports even if one fails

        if not reports:
            logger.warning(
                f"No reports found for date range {start_date} to {end_date}",
                extra={
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "available_periods": len(available_periods)
                }
            )

        return reports

    def get_context_for_deviation_legacy(
        self,
        deviation_date: date,
        simulation_years: int
    ) -> str:
        """
        Get combined historical context using legacy full-text loading.

        This is the original implementation that loads complete markdown files.
        Use this as fallback when RAG is unavailable.

        Args:
            deviation_date: Date of the historical deviation
            simulation_years: Number of years being simulated forward

        Returns:
            Combined text of all relevant historical reports
        """
        end_date = date(
            deviation_date.year + simulation_years,
            deviation_date.month,
            deviation_date.day
        )

        # Get all relevant reports
        reports = self.get_reports_for_date_range(deviation_date, end_date)

        if not reports:
            logger.error(
                f"No historical context available for {deviation_date} + {simulation_years} years",
                extra={
                    "deviation_date": str(deviation_date),
                    "simulation_years": simulation_years
                }
            )
            return ""

        # Combine reports with clear separators
        combined_context = "\n\n" + "="*80 + "\n\n".join(reports)

        logger.info(
            f"[LEGACY] Generated context for {deviation_date} with {len(reports)} report(s), "
            f"total length: {len(combined_context)} characters",
            extra={
                "deviation_date": str(deviation_date),
                "simulation_years": simulation_years,
                "reports_count": len(reports),
                "total_length": len(combined_context),
                "mode": "legacy"
            }
        )

        return combined_context

    async def get_context_for_deviation_rag(
        self,
        deviation_description: str,
        scenario_type: str,
        deviation_date: date,
        simulation_years: int,
        db = None
    ) -> Tuple[str, Dict]:
        """
        Get historical context using RAG (vector store semantic retrieval).

        This provides ~99% token reduction compared to legacy full-text loading
        by retrieving only the most relevant chunks.

        Args:
            deviation_description: Description of the deviation
            scenario_type: Type of scenario (local_deviation, global_deviation, etc.)
            deviation_date: Date of the historical deviation
            simulation_years: Number of years being simulated forward
            db: Optional database session (for advanced features)

        Returns:
            Tuple of (context_string, debug_info_dict)
        """
        from app.services.vector_store_service import get_vector_store_service

        vector_service = get_vector_store_service()

        if not vector_service.enabled:
            raise Exception("Vector store is not enabled")

        year_start = deviation_date.year
        year_end = deviation_date.year + simulation_years

        # Use safe retrieval with fallback
        context, debug_info = await vector_service.retrieve_relevant_ground_truth_safe(
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            year_start=year_start,
            year_end=year_end,
            fallback_loader=lambda y1, y2: self.get_context_for_deviation_legacy(
                date(y1, 1, 1),
                y2 - y1
            ),
            debug=True
        )

        if debug_info:
            logger.info(
                f"[RAG] Generated context for {deviation_date}, "
                f"mode: {debug_info.get('mode', 'rag')}, "
                f"chunks: {debug_info.get('final_chunks', 0)}, "
                f"tokens: ~{debug_info.get('total_tokens', 0):.0f}",
                extra={
                    "deviation_date": str(deviation_date),
                    "simulation_years": simulation_years,
                    "mode": debug_info.get("mode", "rag"),
                    "chunks": debug_info.get("final_chunks", 0),
                    "tokens": debug_info.get("total_tokens", 0)
                }
            )

        return context, debug_info

    async def get_context_for_extension_rag(
        self,
        timeline_id: str,
        extension_start_year: int,
        deviation_description: str,
        scenario_type: str,
        use_rag: bool = True,
        db = None
    ) -> Tuple[str, Dict]:
        """
        Get context for timeline extension from previous generations.

        This retrieves relevant chunks from previous generations in the SAME timeline,
        not from ground truth. This provides continuity for the alternate history.

        Respects CONTEXT_RETRIEVAL_MODE setting:
        - 'rag': Uses vector search on previous generations
        - 'legacy': Returns empty context (no previous generation retrieval)

        Args:
            timeline_id: UUID of the timeline being extended
            extension_start_year: Year where the extension begins
            deviation_description: Original deviation description
            scenario_type: Type of scenario
            db: Optional database session

        Returns:
            Tuple of (context_string, debug_info)
        """
        from app.services.vector_store_service import get_vector_store_service

        # NEW: Respect use_rag parameter
        if not use_rag:
            logger.info("use_rag=False, skipping previous generation context")
            return "", {"mode": "user_disabled", "final_chunks": 0, "total_tokens": 0}

        # Check context retrieval mode
        context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
        if context_mode == "legacy":
            logger.info("Context retrieval mode set to LEGACY, skipping previous generation context")
            return "", {"mode": "legacy_mode", "final_chunks": 0, "total_tokens": 0}

        vector_service = get_vector_store_service()

        if not vector_service.enabled:
            logger.warning("Vector store disabled, cannot retrieve previous generation context")
            return "", {"mode": "disabled", "final_chunks": 0, "total_tokens": 0}

        try:
            context, debug_info = await vector_service.retrieve_previous_generation_context(
                timeline_id=timeline_id,
                current_year_start=extension_start_year,
                deviation_description=deviation_description,
                scenario_type=scenario_type,
                top_k=8,
                debug=True
            )

            if not context:
                logger.warning(
                    f"No previous generation context found for timeline {timeline_id}, "
                    f"this might be the first generation"
                )
                return "", {"mode": "empty", "final_chunks": 0, "total_tokens": 0}

            logger.info(
                f"Retrieved previous generation context for timeline {timeline_id}: "
                f"{debug_info.get('final_chunks', 0)} chunks, "
                f"~{debug_info.get('total_tokens', 0):.0f} tokens"
            )

            return context, debug_info

        except Exception as e:
            logger.error(
                f"Failed to retrieve previous generation context: {e}",
                exc_info=True
            )
            return "", {"mode": "error", "error": str(e), "final_chunks": 0, "total_tokens": 0}

    async def get_context_for_skeleton_rag(
        self,
        deviation_description: str,
        scenario_type: str,
        deviation_date: date,
        skeleton_events: list,
        use_rag: bool = True,
        db = None
    ) -> Tuple[str, Dict]:
        """
        Get ground truth historical context for skeleton historian using RAG.

        This method creates specialized queries based on the skeleton events
        to retrieve highly relevant historical context from ground truth.

        Respects CONTEXT_RETRIEVAL_MODE setting:
        - 'rag': Uses custom queries based on skeleton events
        - 'legacy': Falls back to standard legacy retrieval

        Args:
            deviation_description: Description of the deviation
            scenario_type: Type of scenario
            deviation_date: Date of the deviation
            skeleton_events: List of skeleton events (should have event_date, location, description)
            db: Optional database session

        Returns:
            Tuple of (context_string, debug_info)
        """
        # NEW: Respect use_rag parameter
        if not use_rag:
            logger.info("use_rag=False, using legacy mode for skeleton")
            # Calculate years from skeleton events
            event_years = []
            for event in skeleton_events:
                try:
                    if hasattr(event, 'event_date'):
                        if isinstance(event.event_date, str):
                            event_year = int(event.event_date.split('-')[0])
                        else:
                            event_year = event.event_date.year
                        event_years.append(event_year)
                except Exception as e:
                    logger.warning(f"Failed to parse event date: {e}")

            year_start = min(event_years) if event_years else deviation_date.year
            year_end = max(event_years) if event_years else deviation_date.year + 10

            # Use legacy retrieval
            legacy_context = self.get_context_for_deviation_legacy(
                deviation_date=deviation_date,
                simulation_years=year_end - year_start
            )
            return legacy_context, {
                "mode": "user_disabled_legacy",
                "final_chunks": 0,
                "total_tokens": len(legacy_context.split()) * 1.3
            }

        # Check context retrieval mode
        context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
        if context_mode == "legacy":
            logger.info("Context retrieval mode set to LEGACY for skeleton generation")
            # Calculate years from skeleton events
            event_years = []
            for event in skeleton_events:
                try:
                    if hasattr(event, 'event_date'):
                        if isinstance(event.event_date, str):
                            event_year = int(event.event_date.split('-')[0])
                        else:
                            event_year = event.event_date.year
                        event_years.append(event_year)
                except Exception as e:
                    logger.warning(f"Failed to parse event date: {e}")

            year_start = min(event_years) if event_years else deviation_date.year
            year_end = max(event_years) if event_years else deviation_date.year + 10

            # Use legacy retrieval
            legacy_context = self.get_context_for_deviation_legacy(
                deviation_date=deviation_date,
                simulation_years=year_end - year_start
            )
            return legacy_context, {
                "mode": "legacy_mode",
                "final_chunks": 0,
                "total_tokens": len(legacy_context.split()) * 1.3
            }

        from app.services.vector_store_service import get_vector_store_service

        vector_service = get_vector_store_service()

        if not vector_service.enabled:
            raise Exception("Vector store is not enabled")

        # Extract year range from skeleton events
        event_years = []
        for event in skeleton_events:
            try:
                # Handle both string and date objects
                if hasattr(event, 'event_date'):
                    if isinstance(event.event_date, str):
                        event_year = int(event.event_date.split('-')[0])
                    else:
                        event_year = event.event_date.year
                    event_years.append(event_year)
            except Exception as e:
                logger.warning(f"Failed to parse event date: {e}")

        year_start = min(event_years) if event_years else deviation_date.year
        year_end = max(event_years) if event_years else deviation_date.year + 10

        # Create queries based on skeleton events
        # Extract key terms from skeleton events for better queries
        event_descriptions = []
        locations = set()
        for event in skeleton_events[:10]:  # Use first 10 events to avoid too long queries
            if hasattr(event, 'description'):
                event_descriptions.append(event.description)
            if hasattr(event, 'location'):
                locations.add(event.location)

        # Build specialized queries
        custom_queries = []

        # Query 1: Based on deviation and key locations
        if locations:
            location_str = ", ".join(list(locations)[:5])
            custom_queries.append(
                f"Historical context for {deviation_description} focusing on {location_str}"
            )

        # Query 2: Based on first few event descriptions
        if event_descriptions:
            key_terms = " ".join(event_descriptions[:4][:200])  # First 4 events, max 200 chars
            custom_queries.append(
                f"Events and conditions related to: {key_terms}"
            )

        # Query 3: The human element
        custom_queries.append(
            f"Psychological impact of {key_terms} on specific historical figures, leadership, and decision-makers {year_start}-{year_end}",
        )

        # Query 4: General period context
        custom_queries.append(
            f"Historical developments and major events {year_start} to {year_end}"
        )

        # Retrieve using custom queries
        try:
            context, debug_info = await vector_service.retrieve_relevant_ground_truth(
                deviation_description=deviation_description,
                scenario_type=scenario_type,
                year_start=year_start,
                year_end=year_end,
                custom_queries=custom_queries if custom_queries else None,
                top_k=10,  # Retrieve more chunks for skeleton-based generation
                debug=True
            )

            logger.info(
                f"[RAG-Skeleton] Generated context for skeleton with {len(skeleton_events)} events, "
                f"chunks: {debug_info.get('final_chunks', 0)}, "
                f"tokens: ~{debug_info.get('total_tokens', 0):.0f}",
                extra={
                    "deviation_date": str(deviation_date),
                    "skeleton_events": len(skeleton_events),
                    "year_range": f"{year_start}-{year_end}",
                    "chunks": debug_info.get("final_chunks", 0),
                    "tokens": debug_info.get("total_tokens", 0)
                }
            )

            return context, debug_info

        except Exception as e:
            logger.error(
                f"Failed to retrieve ground truth context for skeleton: {e}",
                exc_info=True
            )
            # Fallback to standard deviation context
            return await self.get_context_for_deviation_rag(
                deviation_description=deviation_description,
                scenario_type=scenario_type,
                deviation_date=deviation_date,
                simulation_years=year_end - year_start,
                db=db
            )

    async def get_context_for_deviation(
        self,
        deviation_date: date,
        simulation_years: int,
        deviation_description: str = "",
        scenario_type: str = "local_deviation",
        use_rag: Optional[bool] = None,
        db = None
    ) -> str:
        """
        Get historical context for a deviation point.

        Automatically uses RAG if available, falls back to legacy mode if not.

        Args:
            deviation_date: Date of the historical deviation
            simulation_years: Number of years being simulated forward
            deviation_description: Description of the deviation (for RAG)
            scenario_type: Type of scenario (for RAG)
            use_rag: Force RAG (True) or legacy (False). None = auto-detect
            db: Optional database session (for RAG)

        Returns:
            Historical context string
        """
        # Determine whether to use RAG
        if use_rag is None:
            # Auto-detect: check both vector store enabled AND context retrieval mode
            vector_store_enabled = os.getenv("VECTOR_STORE_ENABLED", "true").lower() == "true"
            context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
            use_rag = vector_store_enabled and context_mode == "rag"

            if vector_store_enabled and context_mode == "legacy":
                logger.info("Context retrieval mode set to LEGACY (user preference)")
            elif not vector_store_enabled:
                logger.debug("Vector store disabled, using legacy mode")

        # Try RAG mode
        if use_rag and deviation_description:
            try:
                # Call async RAG method directly (we're in async context)
                context, debug_info = await self.get_context_for_deviation_rag(
                    deviation_description=deviation_description,
                    scenario_type=scenario_type,
                    deviation_date=deviation_date,
                    simulation_years=simulation_years,
                    db=db
                )

                # If fallback was used, log it
                if debug_info and debug_info.get("mode") == "legacy_fallback":
                    logger.warning(
                        f"RAG failed, used legacy fallback: {debug_info.get('reason', 'unknown')}",
                        extra={"reason": debug_info.get("reason")}
                    )

                return context

            except Exception as e:
                logger.warning(
                    f"RAG mode failed: {e}, falling back to legacy mode",
                    extra={"error": str(e)}
                )
                # Fall through to legacy mode

        # Legacy mode (fallback or explicit)
        return self.get_context_for_deviation_legacy(deviation_date, simulation_years)

    def clear_cache(self) -> None:
        """
        Clear the reports cache and periods cache.

        Useful for testing or if reports are updated during runtime.
        This will force a rescan of the directory on next access.
        """
        global _reports_cache, _periods_cache
        _reports_cache.clear()
        _periods_cache = None
        logger.info("Cleared reports cache and periods cache")

    def get_available_reports(self) -> List[str]:
        """
        Get list of available report filenames.

        Returns:
            List of report filenames in the ground truth directory, sorted by year range
        """
        try:
            periods = self._scan_available_reports()
            return [period["file"] for period in periods]
        except Exception as e:
            logger.error(f"Error listing available reports: {e}")
            return []

    def get_available_periods(self) -> List[Dict]:
        """
        Get list of available report periods with their year ranges.

        Returns:
            List of dicts with 'start', 'end', and 'file' keys
        """
        return self._scan_available_reports()


# Global service instance
_service_instance: HistoryService | None = None


def get_history_service() -> HistoryService:
    """
    Get the global HistoryService instance (singleton pattern).

    Returns:
        Initialized HistoryService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance