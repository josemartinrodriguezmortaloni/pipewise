"""
Gmail MCP Server for PipeWise

Provides Gmail integration capabilities through MCP protocol.
"""

import logging
from typing import Dict, Any, Optional, List
import os
import base64
import json
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class GmailMCPServer:
    """
    Gmail MCP Server for handling Gmail integrations.

    This server provides functionality to send emails, read messages,
    and manage Gmail operations using the Gmail API.
    """

    def __init__(self, access_token: Optional[str] = None):
        """Initialize Gmail MCP Server"""
        self.access_token = access_token
        self.base_url = "https://gmail.googleapis.com/gmail/v1"

        logger.info("GmailMCPServer initialized")

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        """
        Send an email through Gmail.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            cc: CC email address(es)
            bcc: BCC email address(es)
            is_html: Whether the body is HTML

        Returns:
            Result dictionary with success status and message data
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            # Create email message
            if is_html:
                message = MIMEMultipart()
                message.attach(MIMEText(body, "html"))
            else:
                message = MIMEText(body)

            message["to"] = to
            message["subject"] = subject

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Prepare API request
            email_data = {"raw": raw_message}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/users/me/messages/send",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    json=email_data,
                )

            if response.status_code == 200:
                message_data = response.json()
                logger.info(f"Successfully sent email: {message_data['id']}")
                return {
                    "success": True,
                    "message_id": message_data["id"],
                    "thread_id": message_data.get("threadId", ""),
                    "to": to,
                    "subject": subject,
                }
            else:
                logger.error(
                    f"Failed to send email: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}

    async def get_messages(
        self,
        query: str = "",
        max_results: int = 10,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get messages from Gmail inbox.

        Args:
            query: Search query (Gmail search syntax)
            max_results: Maximum number of messages to return
            label_ids: List of label IDs to filter by

        Returns:
            List of messages
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            # Prepare query parameters
            params: Dict[str, Any] = {
                "maxResults": max_results,
            }

            if query:
                params["q"] = query

            if label_ids:
                params["labelIds"] = label_ids

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/me/messages",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    params=params,
                )

            if response.status_code == 200:
                messages_data = response.json()
                messages = []

                # Get detailed information for each message
                for message_info in messages_data.get("messages", []):
                    message_detail = await self.get_message_details(message_info["id"])
                    if message_detail.get("success"):
                        messages.append(message_detail["message"])

                logger.info(f"Retrieved {len(messages)} messages")
                return {
                    "success": True,
                    "messages": messages,
                    "count": len(messages),
                    "total_estimated": messages_data.get("resultSizeEstimate", 0),
                }
            else:
                logger.error(
                    f"Failed to get messages: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return {"success": False, "error": str(e)}

    async def get_message_details(self, message_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific message.

        Args:
            message_id: Gmail message ID

        Returns:
            Detailed message information
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/me/messages/{message_id}",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                )

            if response.status_code == 200:
                message_data = response.json()

                # Extract headers
                headers = {}
                for header in message_data.get("payload", {}).get("headers", []):
                    headers[header["name"]] = header["value"]

                # Extract body
                body = self._extract_body(message_data.get("payload", {}))

                message_info = {
                    "id": message_data["id"],
                    "thread_id": message_data.get("threadId", ""),
                    "subject": headers.get("Subject", ""),
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "date": headers.get("Date", ""),
                    "body": body,
                    "snippet": message_data.get("snippet", ""),
                    "label_ids": message_data.get("labelIds", []),
                }

                return {
                    "success": True,
                    "message": message_info,
                }
            else:
                logger.error(
                    f"Failed to get message details: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting message details: {e}")
            return {"success": False, "error": str(e)}

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload."""
        body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break
                elif part.get("mimeType") == "text/html" and not body:
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
        else:
            # Single part message
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")

        return body

    async def search_emails(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for emails using Gmail search syntax.

        Args:
            query: Search query (e.g., "from:someone@gmail.com", "subject:meeting")
            max_results: Maximum number of results

        Returns:
            Search results
        """
        try:
            return await self.get_messages(query=query, max_results=max_results)
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return {"success": False, "error": str(e)}

    async def reply_to_message(
        self, message_id: str, reply_body: str, is_html: bool = False
    ) -> Dict[str, Any]:
        """
        Reply to a specific message.

        Args:
            message_id: Original message ID
            reply_body: Reply content
            is_html: Whether the reply is HTML

        Returns:
            Result of the reply operation
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            # Get original message details
            original_message = await self.get_message_details(message_id)
            if not original_message.get("success"):
                return {"success": False, "error": "Failed to get original message"}

            message_data = original_message["message"]

            # Create reply
            reply_subject = message_data.get("subject", "")
            if not reply_subject.startswith("Re:"):
                reply_subject = f"Re: {reply_subject}"

            return await self.send_email(
                to=message_data.get("from", ""),
                subject=reply_subject,
                body=reply_body,
                is_html=is_html,
            )

        except Exception as e:
            logger.error(f"Error replying to message: {e}")
            return {"success": False, "error": str(e)}

    async def get_labels(self) -> Dict[str, Any]:
        """
        Get all Gmail labels.

        Returns:
            List of Gmail labels
        """
        try:
            if not self.access_token:
                return {"success": False, "error": "No access token available"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/me/labels",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                )

            if response.status_code == 200:
                labels_data = response.json()
                labels = []

                for label in labels_data.get("labels", []):
                    labels.append(
                        {
                            "id": label["id"],
                            "name": label["name"],
                            "type": label.get("type", ""),
                            "messages_total": label.get("messagesTotal", 0),
                            "messages_unread": label.get("messagesUnread", 0),
                        }
                    )

                logger.info(f"Retrieved {len(labels)} labels")
                return {
                    "success": True,
                    "labels": labels,
                    "count": len(labels),
                }
            else:
                logger.error(
                    f"Failed to get labels: {response.status_code} - {response.text}"
                )
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return {"success": False, "error": str(e)}


# Utility functions for easier access
def create_gmail_server(access_token: str) -> GmailMCPServer:
    """Create and return a new GmailMCPServer instance."""
    return GmailMCPServer(access_token)


async def send_gmail_email(
    access_token: str,
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    is_html: bool = False,
) -> Dict[str, Any]:
    """Utility function to send an email through Gmail."""
    server = create_gmail_server(access_token)
    return await server.send_email(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        is_html=is_html,
    )


async def search_gmail_emails(
    access_token: str, query: str, max_results: int = 10
) -> Dict[str, Any]:
    """Utility function to search Gmail emails."""
    server = create_gmail_server(access_token)
    return await server.search_emails(query=query, max_results=max_results)
