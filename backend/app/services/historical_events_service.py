"""
Service for loading and parsing major historical events data.

This module provides functionality to load historical events from the markdown file
and serve them to the frontend for timeline visualization.
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Optional
import logging

from app.models import HistoricalEvent

logger = logging.getLogger(__name__)

class HistoricalEventsService:
    """Service for managing historical events data."""

    def __init__(self):
        self.events: List[HistoricalEvent] = []
        self._load_events()

    def _load_events(self) -> None:
        """Load historical events from the markdown file."""
        events_file = Path(__file__).parent.parent.parent / "data" / "major_events_1900-2000.md"

        if not events_file.exists():
            logger.warning(f"Historical events file not found: {events_file}")
            return

        try:
            content = events_file.read_text(encoding='utf-8')
            self.events = self._parse_events(content)
            logger.info(f"Loaded {len(self.events)} historical events")
        except Exception as e:
            logger.error(f"Error loading historical events: {e}")

    def _parse_events(self, content: str) -> List[HistoricalEvent]:
        """Parse events from markdown content."""
        events = []
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            event = self._parse_event_line(line)
            if event:
                events.append(event)

        # Sort events by start year
        events.sort(key=lambda e: e.start_year)
        return events

    def _parse_event_line(self, line: str) -> Optional[HistoricalEvent]:
        """Parse a single event line."""
        try:
            # Pattern for year range: "1914–1918: World War I"
            range_pattern = r'^(\d{4})[–-](\d{4}):\s*(.+)$'

            # Pattern for specific date: "December 7, 1941: Attack on Pearl Harbor"
            date_pattern = r'^([A-Za-z]+\s+\d{1,2},\s+)?(\d{4}):\s*(.+)$'

            # Pattern for single year: "1917: The Russian Revolution"
            year_pattern = r'^(\d{4}):\s*(.+)$'

            # Try year range pattern first
            match = re.match(range_pattern, line)
            if match:
                start_year = int(match.group(1))
                end_year = int(match.group(2))
                title = match.group(3).strip()
                return HistoricalEvent(
                    title=title,
                    start_year=start_year,
                    end_year=end_year,
                    event_type="period",
                    impact_level=self._determine_impact_level(title),
                    description=title
                )

            # Try specific date pattern
            match = re.match(date_pattern, line)
            if match:
                year = int(match.group(2))
                title = match.group(3).strip()
                return HistoricalEvent(
                    title=title,
                    start_year=year,
                    end_year=year,
                    event_type="milestone",
                    impact_level=self._determine_impact_level(title),
                    description=title
                )

            # Try single year pattern
            match = re.match(year_pattern, line)
            if match:
                year = int(match.group(1))
                title = match.group(2).strip()
                return HistoricalEvent(
                    title=title,
                    start_year=year,
                    end_year=year,
                    event_type="milestone",
                    impact_level=self._determine_impact_level(title),
                    description=title
                )

        except Exception as e:
            logger.warning(f"Error parsing event line '{line}': {e}")

        return None

    def _determine_impact_level(self, title: str) -> str:
        """Determine the impact level of an event based on its title."""
        title_lower = title.lower()

        # High impact events
        if any(keyword in title_lower for keyword in [
            'world war', 'cold war', 'great depression', 'soviet union'
        ]):
            return "high"

        # Medium impact events
        if any(keyword in title_lower for keyword in [
            'war', 'revolution', 'assassination', 'moon', 'berlin wall'
        ]):
            return "medium"

        # Default to low impact
        return "low"

    def get_events(self, start_year: Optional[int] = None, end_year: Optional[int] = None) -> List[HistoricalEvent]:
        """Get historical events, optionally filtered by year range."""
        if start_year is None and end_year is None:
            return self.events

        filtered_events = []
        for event in self.events:
            # Check if event overlaps with the requested range
            event_start = event.start_year
            event_end = event.end_year

            if start_year is not None and event_end < start_year:
                continue
            if end_year is not None and event_start > end_year:
                continue

            filtered_events.append(event)

        return filtered_events

    def get_events_for_year(self, year: int) -> List[HistoricalEvent]:
        """Get all events that occurred in a specific year."""
        return [
            event for event in self.events
            if event.start_year <= year <= event.end_year
        ]


# Global service instance
_historical_events_service: Optional[HistoricalEventsService] = None

def get_historical_events_service() -> HistoricalEventsService:
    """Get the global historical events service instance."""
    global _historical_events_service
    if _historical_events_service is None:
        _historical_events_service = HistoricalEventsService()
    return _historical_events_service