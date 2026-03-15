"""
Historical events and ground truth reports API endpoints.

This module handles:
- Historical events retrieval with date range filtering
- Ground truth historical reports listing
- Individual ground truth report retrieval
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from pathlib import Path
import logging
import re

from app.models import HistoricalEvent
from app.services.historical_events_service import get_historical_events_service

logger = logging.getLogger(__name__)

# Create router with /api prefix
router = APIRouter(prefix="/api", tags=["historical-events", "ground-truth"])


def scan_ground_truth_files() -> List[dict]:
    """
    Automatically scan the ground_truth directory for report files.

    Returns a list of period dictionaries with start, end, and filename.
    Expected filename format: YYYY-YYYY.md (e.g., "1880-1890.md")
    """
    periods = []
    ground_truth_dir = Path("data/ground_truth")

    if not ground_truth_dir.exists():
        logger.warning(f"Ground truth directory not found: {ground_truth_dir}")
        return periods

    # Pattern to match YYYY-YYYY.md files
    filename_pattern = re.compile(r"^(\d{4})-(\d{4})\.md$")

    try:
        for file_path in ground_truth_dir.glob("*.md"):
            match = filename_pattern.match(file_path.name)
            if match:
                start_year = int(match.group(1))
                end_year = int(match.group(2))
                periods.append({
                    "start": start_year,
                    "end": end_year,
                    "file": file_path.name,
                })
            else:
                logger.debug(f"Skipping file with non-standard name: {file_path.name}")

        # Sort by start year
        periods.sort(key=lambda p: p["start"])
        logger.info(f"Scanned {len(periods)} ground truth reports from directory")

    except Exception as e:
        logger.error(f"Error scanning ground truth directory: {e}", exc_info=True)

    return periods


@router.get("/historical-events", response_model=List[HistoricalEvent])
async def get_historical_events(start_year: int = 1900, end_year: int = 2000):
    """
    Get historical events for the original timeline.

    This endpoint returns major historical events that can be displayed
    on the original timeline (1900-2000).

    Args:
        start_year: Start year for filtering events (default: 1900)
        end_year: End year for filtering events (default: 2000)

    Returns:
        List[HistoricalEvent]: List of historical events in the specified range
    """
    logger.info(f"Retrieving historical events from {start_year} to {end_year}")

    try:
        historical_events_service = get_historical_events_service()
        events = historical_events_service.get_events(start_year, end_year)

        logger.info(f"Retrieved {len(events)} historical events")
        return events

    except Exception as e:
        logger.error(f"Error retrieving historical events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical events",
        )


@router.get(
    "/ground-truth-reports",
    response_model=List[dict],
    summary="Get ground truth historical reports",
    description="Retrieve ground truth historical reports for different time periods (automatically scanned from data/ground_truth folder)",
)
async def get_ground_truth_reports():
    """
    Get ground truth historical reports for the original timeline.

    Automatically scans the data/ground_truth directory for reports.
    Supported filename format: YYYY-YYYY.md (e.g., "1880-1890.md")
    """
    try:
        logger.info("Retrieving ground truth reports")

        reports = []
        # Automatically scan the ground_truth directory
        periods = scan_ground_truth_files()

        for period in periods:
            try:
                # Read ground truth report file directly
                file_path = Path(f"data/ground_truth/{period['file']}")
                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")
                    reports.append(
                        {
                            "id": f"ground-truth-{period['start']}-{period['end']}",
                            "start_year": period["start"],
                            "end_year": period["end"],
                            "period_years": period["end"] - period["start"] + 1,
                            "title": f"Historical Period {period['start']}-{period['end']}",
                            "content": content[:500] + "..."
                            if len(content) > 500
                            else content,  # Truncate for list view
                            "type": "ground_truth",
                        }
                    )
                else:
                    logger.warning(f"Ground truth file not found: {file_path}")
            except Exception as e:
                logger.warning(
                    f"Could not load ground truth for {period['start']}-{period['end']}: {e}"
                )
                continue

        logger.info(f"Retrieved {len(reports)} ground truth reports")
        return reports

    except Exception as e:
        logger.error(f"Error retrieving ground truth reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ground truth reports",
        )


@router.get(
    "/ground-truth-reports/{report_id}",
    response_model=dict,
    summary="Get individual ground truth historical report",
    description="Retrieve a specific ground truth historical report by ID",
)
async def get_ground_truth_report(report_id: str):
    """
    Get a specific ground truth historical report by ID.

    Args:
        report_id: The ID of the ground truth report (e.g., "ground-truth-1921-1930")

    Returns:
        dict: The ground truth report with full content
    """
    try:
        logger.info(f"Retrieving ground truth report: {report_id}")

        # Extract years from report_id
        # Expected format: "ground-truth-1921-1930"
        if not report_id.startswith("ground-truth-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ground truth report ID format",
            )

        # Parse years from ID
        years_part = report_id.replace("ground-truth-", "")
        if "-" not in years_part:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ground truth report ID format",
            )

        start_year, end_year = years_part.split("-")
        start_year = int(start_year)
        end_year = int(end_year)

        # Find corresponding file by scanning the ground_truth directory
        periods = scan_ground_truth_files()

        matching_period = None
        for period in periods:
            if period["start"] == start_year and period["end"] == end_year:
                matching_period = period
                break

        if not matching_period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ground truth report not found for period {start_year}-{end_year}",
            )

        # Read the full content
        file_path = Path(f"data/ground_truth/{matching_period['file']}")
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ground truth report file not found: {matching_period['file']}",
            )

        content = file_path.read_text(encoding="utf-8")

        report = {
            "id": report_id,
            "start_year": start_year,
            "end_year": end_year,
            "period_years": end_year - start_year + 1,
            "title": f"Historical Period {start_year}-{end_year}",
            "content": content,  # Full content, not truncated
            "type": "ground_truth",
        }

        logger.info(f"Successfully retrieved ground truth report: {report_id}")
        return report

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.error(f"Invalid year format in report ID {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year format in report ID",
        )
    except Exception as e:
        logger.error(
            f"Error retrieving ground truth report {report_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ground truth report",
        )
