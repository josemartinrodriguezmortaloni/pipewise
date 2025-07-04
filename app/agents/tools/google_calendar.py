"""
Google Calendar MCP Server for PipeWise

Provides Google Calendar integration capabilities through MCP protocol.
"""

import logging
from typing import Dict, Any, Optional, List
import os
from datetime import datetime, timedelta
import json
import httpx

logger = logging.getLogger(__name__)


class GoogleCalendarMCPServer:
    """
    Google Calendar MCP Server for handling Google Calendar integrations.

    This server provides functionality to create events, check availability,
    and manage calendar operations using the Google Calendar API.
    """

    def __init__(self, access_token: Optional[str] = None):
        """Initialize Google Calendar MCP Server"""
        self.access_token = access_token
        self.base_url = "https://www.googleapis.com/calendar/v3"

        logger.info("GoogleCalendarMCPServer initialized")

    async def create_event(
        self,
        calendar_id: str = "primary",
        title: str = "",
        description: str = "",
        start_time: str = "",
        end_time: str = "",
        attendees: Optional[List[str]] = None,
        location: str = "",
        timezone: str = "America/New_York",
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            calendar_id: Calendar ID (default: "primary")
            title: Event title
            description: Event description
            start_time: Start time in ISO format
            end_time: End time in ISO format
            attendees: List of attendee email addresses
            location: Event location
            timezone: Event timezone

        Returns:
            Result dictionary with success status and event data
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            # Prepare event data
            event_data = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone,
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone,
                },
                "location": location,
            }

            # Add attendees if provided
            if attendees:
                event_data["attendees"] = [{"email": email} for email in attendees]

            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/calendars/{calendar_id}/events",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    json=event_data,
                )

            if response.status_code == 200:
                event = response.json()
                logger.info(f"Successfully created calendar event: {event['id']}")
                return {
                    "success": True,
                    "event_id": event["id"],
                    "html_link": event.get("htmlLink", ""),
                    "title": event.get("summary", ""),
                    "start": event.get("start", {}).get("dateTime", ""),
                    "end": event.get("end", {}).get("dateTime", ""),
                }
            else:
                logger.error(
                    f"Failed to create event: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {"success": False, "error": str(e)}

    async def check_availability(
        self,
        calendar_id: str = "primary",
        start_time: str = "",
        end_time: str = "",
        timezone: str = "America/New_York",
    ) -> Dict[str, Any]:
        """
        Check calendar availability for a specific time range.

        Args:
            calendar_id: Calendar ID to check
            start_time: Start time in ISO format
            end_time: End time in ISO format
            timezone: Timezone for the query

        Returns:
            Availability information
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            # Query for busy times
            query_data = {
                "timeMin": start_time,
                "timeMax": end_time,
                "timeZone": timezone,
                "items": [{"id": calendar_id}],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/freeBusy",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    json=query_data,
                )

            if response.status_code == 200:
                busy_data = response.json()
                busy_times = (
                    busy_data.get("calendars", {}).get(calendar_id, {}).get("busy", [])
                )

                is_available = len(busy_times) == 0

                logger.info(
                    f"Availability check: {'Available' if is_available else 'Busy'}"
                )
                return {
                    "success": True,
                    "is_available": is_available,
                    "busy_times": busy_times,
                    "time_range": {
                        "start": start_time,
                        "end": end_time,
                    },
                }
            else:
                logger.error(
                    f"Failed to check availability: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {"success": False, "error": str(e)}

    async def list_calendars(self) -> Dict[str, Any]:
        """
        List available calendars.

        Returns:
            List of available calendars
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/me/calendarList",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                )

            if response.status_code == 200:
                calendars_data = response.json()
                calendars = []

                for calendar in calendars_data.get("items", []):
                    calendars.append(
                        {
                            "id": calendar["id"],
                            "name": calendar.get("summary", ""),
                            "description": calendar.get("description", ""),
                            "primary": calendar.get("primary", False),
                            "access_role": calendar.get("accessRole", ""),
                        }
                    )

                logger.info(f"Retrieved {len(calendars)} calendars")
                return {
                    "success": True,
                    "calendars": calendars,
                    "count": len(calendars),
                }
            else:
                logger.error(
                    f"Failed to list calendars: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            return {"success": False, "error": str(e)}

    async def get_upcoming_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 10,
        timezone: str = "America/New_York",
    ) -> Dict[str, Any]:
        """
        Get upcoming events from calendar.

        Args:
            calendar_id: Calendar ID
            max_results: Maximum number of events to return
            timezone: Timezone for the query

        Returns:
            List of upcoming events
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            now = datetime.utcnow().isoformat() + "Z"

            params = {
                "timeMin": now,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
                "timeZone": timezone,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/calendars/{calendar_id}/events",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    params=params,
                )

            if response.status_code == 200:
                events_data = response.json()
                events = []

                for event in events_data.get("items", []):
                    events.append(
                        {
                            "id": event["id"],
                            "title": event.get("summary", ""),
                            "description": event.get("description", ""),
                            "start": event.get("start", {}).get("dateTime", ""),
                            "end": event.get("end", {}).get("dateTime", ""),
                            "location": event.get("location", ""),
                            "html_link": event.get("htmlLink", ""),
                            "attendees": [
                                attendee.get("email", "")
                                for attendee in event.get("attendees", [])
                            ],
                        }
                    )

                logger.info(f"Retrieved {len(events)} upcoming events")
                return {
                    "success": True,
                    "events": events,
                    "count": len(events),
                }
            else:
                logger.error(
                    f"Failed to get events: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return {"success": False, "error": str(e)}


# Utility functions for easier access
def create_google_calendar_server(access_token: str) -> GoogleCalendarMCPServer:
    """Create and return a new GoogleCalendarMCPServer instance."""
    return GoogleCalendarMCPServer(access_token)


async def create_calendar_event(
    access_token: str,
    title: str,
    description: str,
    start_time: str,
    end_time: str,
    attendees: Optional[List[str]] = None,
    location: str = "",
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """Utility function to create a calendar event."""
    server = create_google_calendar_server(access_token)
    return await server.create_event(
        calendar_id=calendar_id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        attendees=attendees,
        location=location,
    )


async def check_calendar_availability(
    access_token: str, start_time: str, end_time: str, calendar_id: str = "primary"
) -> Dict[str, Any]:
    """Utility function to check calendar availability."""
    server = create_google_calendar_server(access_token)
    return await server.check_availability(
        calendar_id=calendar_id,
        start_time=start_time,
        end_time=end_time,
    )
