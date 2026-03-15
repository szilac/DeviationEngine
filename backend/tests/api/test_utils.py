"""
Utility functions and helpers for API endpoint testing.

Provides common assertions, data validators, and test helpers.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID


def assert_valid_uuid(uuid_string: str) -> UUID:
    """
    Assert that a string is a valid UUID and return it.

    Args:
        uuid_string: String to validate as UUID

    Returns:
        UUID object if valid

    Raises:
        AssertionError: If string is not a valid UUID
    """
    try:
        return UUID(uuid_string)
    except (ValueError, AttributeError) as e:
        raise AssertionError(f"Invalid UUID: {uuid_string}") from e


def assert_valid_iso_datetime(datetime_string: str) -> datetime:
    """
    Assert that a string is a valid ISO datetime and return it.

    Args:
        datetime_string: String to validate as ISO datetime

    Returns:
        datetime object if valid

    Raises:
        AssertionError: If string is not a valid ISO datetime
    """
    try:
        return datetime.fromisoformat(datetime_string.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise AssertionError(f"Invalid ISO datetime: {datetime_string}") from e


def assert_response_has_keys(response_data: Dict[str, Any], required_keys: List[str]):
    """
    Assert that response data contains all required keys.

    Args:
        response_data: Response dictionary
        required_keys: List of keys that must be present

    Raises:
        AssertionError: If any required key is missing
    """
    missing_keys = [key for key in required_keys if key not in response_data]
    if missing_keys:
        raise AssertionError(
            f"Response missing required keys: {missing_keys}. "
            f"Available keys: {list(response_data.keys())}"
        )


def assert_list_length(data_list: List[Any], expected_length: Optional[int] = None,
                       min_length: Optional[int] = None, max_length: Optional[int] = None):
    """
    Assert list has expected length constraints.

    Args:
        data_list: List to check
        expected_length: Exact expected length
        min_length: Minimum acceptable length
        max_length: Maximum acceptable length

    Raises:
        AssertionError: If length constraints are violated
    """
    actual_length = len(data_list)

    if expected_length is not None and actual_length != expected_length:
        raise AssertionError(
            f"Expected list length {expected_length}, got {actual_length}"
        )

    if min_length is not None and actual_length < min_length:
        raise AssertionError(
            f"List length {actual_length} below minimum {min_length}"
        )

    if max_length is not None and actual_length > max_length:
        raise AssertionError(
            f"List length {actual_length} exceeds maximum {max_length}"
        )


def assert_timeline_structure(timeline_data: Dict[str, Any]):
    """
    Assert that timeline data has correct structure.

    Args:
        timeline_data: Timeline response data

    Raises:
        AssertionError: If structure is invalid
    """
    required_keys = [
        "id",
        "root_deviation_date",
        "root_deviation_description",
        "scenario_type",
        "created_at",
    ]
    assert_response_has_keys(timeline_data, required_keys)
    assert_valid_uuid(timeline_data["id"])
    assert_valid_iso_datetime(timeline_data["created_at"])


def assert_generation_structure(generation_data: Dict[str, Any]):
    """
    Assert that generation data has correct structure.

    Args:
        generation_data: Generation response data

    Raises:
        AssertionError: If structure is invalid
    """
    required_keys = [
        "id",
        "timeline_id",
        "generation_order",
        "generation_type",
        "start_year",
        "end_year",
        "period_years",
        "executive_summary",
        "political_changes",
        "economic_impacts",
        "social_developments",
        "technological_shifts",
        "conflicts_and_wars",
        "key_figures",
        "long_term_implications",
    ]
    assert_response_has_keys(generation_data, required_keys)
    assert_valid_uuid(generation_data["id"])
    assert_valid_uuid(generation_data["timeline_id"])


def assert_skeleton_structure(skeleton_data: Dict[str, Any]):
    """
    Assert that skeleton data has correct structure.

    Args:
        skeleton_data: Skeleton response data

    Raises:
        AssertionError: If structure is invalid
    """
    required_keys = [
        "id",
        "skeleton_type",
        "status",
        "created_at",
    ]
    assert_response_has_keys(skeleton_data, required_keys)
    assert_valid_uuid(skeleton_data["id"])
    assert_valid_iso_datetime(skeleton_data["created_at"])


def assert_error_response(response_data: Dict[str, Any], expected_status: int = None):
    """
    Assert that response is a valid error response.

    Args:
        response_data: Error response data
        expected_status: Optional expected HTTP status code

    Raises:
        AssertionError: If error structure is invalid
    """
    # FastAPI error responses have "detail" key
    assert "detail" in response_data, "Error response must have 'detail' key"

    if expected_status:
        # If we have the full response object, check status code
        if hasattr(response_data, "status_code"):
            assert response_data.status_code == expected_status


def create_mock_timeline_response(timeline_id: str = None) -> Dict[str, Any]:
    """
    Create a mock timeline response for testing.

    Args:
        timeline_id: Optional UUID string for timeline ID

    Returns:
        Mock timeline response data
    """
    from uuid import uuid4

    return {
        "id": timeline_id or str(uuid4()),
        "root_deviation_date": "1914-06-28",
        "root_deviation_description": "Test deviation",
        "scenario_type": "local_deviation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "generations": [],
    }


def create_mock_generation_response(
    generation_id: str = None,
    timeline_id: str = None
) -> Dict[str, Any]:
    """
    Create a mock generation response for testing.

    Args:
        generation_id: Optional UUID string for generation ID
        timeline_id: Optional UUID string for timeline ID

    Returns:
        Mock generation response data
    """
    from uuid import uuid4

    return {
        "id": generation_id or str(uuid4()),
        "timeline_id": timeline_id or str(uuid4()),
        "generation_order": 1,
        "generation_type": "initial",
        "start_year": 0,
        "end_year": 10,
        "period_years": 10,
        "executive_summary": "Test summary",
        "political_changes": "Test political changes",
        "economic_impacts": "Test economic impacts",
        "social_developments": "Test social developments",
        "technological_shifts": "Test technological shifts",
        "conflicts_and_wars": "Test conflicts",
        "key_figures": "Test figures",
        "long_term_implications": "Test implications",
        "created_at": datetime.now().isoformat(),
    }


def create_mock_skeleton_response(skeleton_id: str = None) -> Dict[str, Any]:
    """
    Create a mock skeleton response for testing.

    Args:
        skeleton_id: Optional UUID string for skeleton ID

    Returns:
        Mock skeleton response data
    """
    from uuid import uuid4

    return {
        "id": skeleton_id or str(uuid4()),
        "skeleton_type": "timeline_draft",
        "status": "pending",
        "deviation_date": "1914-06-28",
        "deviation_description": "Test deviation",
        "scenario_type": "local_deviation",
        "created_at": datetime.now().isoformat(),
        "events": [],
    }
