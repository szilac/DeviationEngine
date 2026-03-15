"""
Import/Export API endpoints.

This module handles:
- Timeline export as .devtl files
- Timeline import from .devtl files
- File validation and format checking
"""

import json
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.database import get_db
from app.models import Timeline
from app.services import timeline_service, export_service, import_service
from app.exceptions import TimelineNotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Create router with /api prefix
router = APIRouter(prefix="/api", tags=["timelines", "export-import"])


@router.get(
    "/timeline/{timeline_id}/export",
    summary="Export timeline as .devtl file",
    description="Export complete timeline with all reports and skeleton snapshots as downloadable JSON file",
)
async def export_timeline_endpoint(timeline_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Export timeline as downloadable .devtl file.

    This endpoint exports a complete timeline including all reports, skeleton
    snapshots, and metadata in a portable JSON format that can be imported
    into any Deviation Engine installation.

    Args:
        timeline_id: UUID of the timeline to export

    Returns:
        FileResponse: Downloadable .devtl JSON file

    Raises:
        HTTPException: 404 if timeline not found, 500 if export fails
    """
    logger.info(f"Exporting timeline: {timeline_id}")

    try:
        # Get timeline data from database
        db_timeline = await timeline_service.get_timeline_by_id(db, timeline_id)

        if not db_timeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeline {timeline_id} not found",
            )

        # Export to JSON format
        export_data = await export_service.export_timeline_to_json(db, timeline_id)

        # Generate filename
        filename = export_service.generate_export_filename(db_timeline)

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".devtl", delete=False, encoding="utf-8"
        )

        try:
            # Write JSON data to temp file
            json.dump(export_data, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()

            logger.info(f"Successfully exported timeline {timeline_id} as {filename}")

            # Return file as download
            return FileResponse(
                path=temp_file.name,
                filename=filename,
                media_type="application/json",
                background=None,  # File will be cleaned up after response
            )

        finally:
            # Schedule file cleanup after response
            # FastAPI handles this automatically with FileResponse
            pass

    except TimelineNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Timeline {timeline_id} not found"
        )
    except Exception as e:
        logger.error(f"Error exporting timeline {timeline_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to export timeline"
        )


@router.post(
    "/timeline/import",
    response_model=Timeline,
    status_code=status.HTTP_201_CREATED,
    summary="Import timeline from .devtl file",
    description="Import a timeline from uploaded .devtl file with validation and new UUID generation",
)
async def import_timeline_endpoint(
    file: UploadFile = File(..., description="Timeline .devtl file to import"),
    db: AsyncSession = Depends(get_db),
):
    """
    Import timeline from uploaded .devtl file.

    This endpoint accepts a .devtl file upload, validates the content,
    and creates a new timeline with new UUIDs while preserving all
    report data and skeleton snapshots.

    Args:
        file: Uploaded .devtl file
        db: Database session

    Returns:
        Timeline: Newly created timeline with new UUID

    Raises:
        HTTPException: 400 for validation errors, 413 for file too large,
                      422 for invalid format, 500 for server errors
    """
    logger.info(f"Received timeline import request: {file.filename}")

    try:
        # Validate file extension
        if not file.filename or not file.filename.endswith(".devtl"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only .devtl files are accepted.",
            )

        # Read file content
        try:
            content = await file.read()
        except Exception as e:
            logger.error(f"Failed to read uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file"
            )

        # Validate file size (10 MB limit)
        max_size_bytes = 10 * 1024 * 1024  # 10 MB
        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of 10 MB",
            )

        # Parse JSON
        try:
            timeline_data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid JSON format: {str(e)}",
            )
        except UnicodeDecodeError as e:
            logger.error(f"Invalid encoding in uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File must be UTF-8 encoded",
            )

        # Import timeline
        try:
            new_timeline_id = await import_service.import_timeline_from_json(
                db=db, timeline_data=timeline_data
            )

            await db.commit()

            # Retrieve the newly created timeline
            db_timeline = await timeline_service.get_timeline_by_id(db, new_timeline_id)

            if not db_timeline:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Timeline was created but could not be retrieved",
                )

            # Convert to Pydantic model
            imported_timeline = Timeline.model_validate(db_timeline)

            logger.info(f"Successfully imported timeline {new_timeline_id} from {file.filename}")

            return imported_timeline

        except import_service.InvalidFileFormatError as e:
            logger.error(f"Invalid file format: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        except import_service.UnsupportedVersionError as e:
            logger.error(f"Unsupported format version: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        except ValidationError as e:
            logger.error(f"Validation error during import: {e.message}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during timeline import: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during import",
        )
