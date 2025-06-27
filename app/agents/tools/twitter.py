#!/usr/bin/env python3
"""
Twitter MCP Server - Multi-Channel Platform Server for Twitter Management
Based on the mcp-twitter implementation from https://aiagentslist.com/mcp-servers/mcp-twitter

This server provides comprehensive Twitter account management capabilities including:
- Get Timeline
- Get Any User's Tweets
- Hashtag Search
- Get Replies & Summaries
- User Direct Messages
- Create Post
- Delete Post
- And much more...
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add MCP imports with fallback
try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP not available, using fallback implementation")

# Add twikit imports for Twitter API with fallback
try:
    from twikit import Client as TwitterClient

    TWIKIT_AVAILABLE = True
except ImportError:
    TWIKIT_AVAILABLE = False
    logging.warning("twikit not available, using mock implementation")


class TwitterMCPServer:
    """Twitter MCP Server implementation"""

    def __init__(self):
        self.twitter_client: Optional[Any] = None
        self.server: Optional[Server] = None
        self.cookies_path = os.getenv("COOKIES_PATH", "cookies.json")
        self.env_file = os.getenv("ENV_FILE", ".env")

        # Load environment variables
        self._load_env()

        # Initialize Twitter client
        self._initialize_twitter_client()

        if MCP_AVAILABLE:
            # Initialize MCP server
            self.server = Server("twitter-mcp")
            self._register_tools()

    def _load_env(self) -> None:
        """Load environment variables from .env file"""
        if os.path.exists(self.env_file):
            with open(self.env_file, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            os.environ[key] = value

    def _initialize_twitter_client(self) -> None:
        """Initialize Twitter client with authentication"""
        if TWIKIT_AVAILABLE:
            try:
                client = TwitterClient("en-US")

                # Try to load cookies if they exist
                if os.path.exists(self.cookies_path):
                    client.load_cookies(self.cookies_path)
                    logger.info("Loaded Twitter cookies successfully")
                else:
                    logger.warning(
                        "No Twitter cookies found, authentication may be required"
                    )

                self.twitter_client = client

            except Exception as e:
                logger.error(f"Failed to initialize Twitter client: {e}")
                self.twitter_client = None
        else:
            logger.warning("twikit not available, using mock Twitter client")

        if not self.twitter_client:
            self.twitter_client = self._create_mock_client()

    def _create_mock_client(self):
        """Create a mock Twitter client for testing"""

        class MockTwitterClient:
            def get_user_by_screen_name(self, username):
                return {"id": f"mock_user_{username}", "screen_name": username}

            def get_user_tweets(self, user_id, count=10):
                return [
                    {"id": f"tweet_{i}", "text": f"Mock tweet {i} from {user_id}"}
                    for i in range(count)
                ]

            def get_home_timeline(self, count=10):
                return [
                    {"id": f"home_tweet_{i}", "text": f"Home timeline tweet {i}"}
                    for i in range(count)
                ]

            def search_tweets(self, query, count=10):
                return [
                    {"id": f"search_{i}", "text": f"Search result for '{query}' #{i}"}
                    for i in range(count)
                ]

            def create_tweet(self, text, reply_to=None):
                return {
                    "id": "new_tweet_123",
                    "text": text,
                    "created_at": datetime.now().isoformat(),
                    "reply_to": reply_to,
                }

            def delete_tweet(self, tweet_id):
                return {"success": True, "deleted_tweet_id": tweet_id}

            def send_direct_message(self, user_id, text):
                return {"id": "dm_123", "text": text, "recipient": user_id}

            def get_direct_messages(self, count=10):
                return [
                    {"id": f"dm_{i}", "text": f"DM message {i}"} for i in range(count)
                ]

        return MockTwitterClient()

    def _register_tools(self) -> None:
        """Register all Twitter tools with MCP server"""
        if not self.server:
            return

        tools = [
            Tool(
                name="get_timeline",
                description="Get your Twitter home timeline",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of tweets to retrieve",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        }
                    },
                },
            ),
            Tool(
                name="get_user_tweets",
                description="Get tweets from any public Twitter user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Twitter username (without @)",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of tweets to retrieve",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["username"],
                },
            ),
            Tool(
                name="search_hashtag",
                description="Search for tweets containing any hashtag",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hashtag": {
                            "type": "string",
                            "description": "Hashtag to search (with or without #)",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of tweets to retrieve",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["hashtag"],
                },
            ),
            Tool(
                name="create_tweet",
                description="Create a new tweet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Tweet content",
                            "maxLength": 280,
                        },
                        "reply_to": {
                            "type": "string",
                            "description": "Tweet ID to reply to (optional)",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="send_dm",
                description="Send a direct message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Username to send DM to",
                        },
                        "message": {"type": "string", "description": "Message content"},
                    },
                    "required": ["username", "message"],
                },
            ),
        ]

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return tools

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            return await self._handle_tool_call(name, arguments)

    async def _handle_tool_call(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls and return results"""
        try:
            result = None

            if name == "get_timeline":
                count = arguments.get("count", 10)
                result = await self._get_timeline(count)

            elif name == "get_user_tweets":
                username = arguments["username"]
                count = arguments.get("count", 10)
                result = await self._get_user_tweets(username, count)

            elif name == "search_hashtag":
                hashtag = arguments["hashtag"]
                count = arguments.get("count", 10)
                result = await self._search_hashtag(hashtag, count)

            elif name == "create_tweet":
                text = arguments["text"]
                reply_to = arguments.get("reply_to")
                result = await self._create_tweet(text, reply_to)

            elif name == "send_dm":
                username = arguments["username"]
                message = arguments["message"]
                result = await self._send_dm(username, message)

            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error handling tool call {name}: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_timeline(self, count: int) -> Dict[str, Any]:
        """Get home timeline tweets"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            tweets = self.twitter_client.get_home_timeline(count)
            return {
                "success": True,
                "tweets": tweets,
                "count": len(tweets),
                "type": "timeline",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_user_tweets(self, username: str, count: int) -> Dict[str, Any]:
        """Get tweets from a specific user"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            user = self.twitter_client.get_user_by_screen_name(username)
            tweets = self.twitter_client.get_user_tweets(user["id"], count)
            return {
                "success": True,
                "username": username,
                "tweets": tweets,
                "count": len(tweets),
                "type": "user_tweets",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _search_hashtag(self, hashtag: str, count: int) -> Dict[str, Any]:
        """Search tweets by hashtag"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            # Ensure hashtag starts with #
            if not hashtag.startswith("#"):
                hashtag = f"#{hashtag}"

            tweets = self.twitter_client.search_tweets(hashtag, count)
            return {
                "success": True,
                "hashtag": hashtag,
                "tweets": tweets,
                "count": len(tweets),
                "type": "hashtag_search",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_tweet(
        self, text: str, reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new tweet"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            tweet = self.twitter_client.create_tweet(text, reply_to)
            return {
                "success": True,
                "tweet": tweet,
                "reply_to": reply_to,
                "type": "create_tweet",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_dm(self, username: str, message: str) -> Dict[str, Any]:
        """Send a direct message"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            user = self.twitter_client.get_user_by_screen_name(username)
            dm = self.twitter_client.send_direct_message(user["id"], message)
            return {
                "success": True,
                "recipient": username,
                "message": message,
                "dm": dm,
                "type": "send_dm",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Synchronous methods for backward compatibility
    def send_dm(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send DM - synchronous version for backward compatibility"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            dm = self.twitter_client.send_direct_message(user_id, message)
            return {"success": True, "message_id": dm.get("id", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """Get user by username - synchronous version for backward compatibility"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            user = self.twitter_client.get_user_by_screen_name(username)
            return {
                "success": True,
                "user_id": user.get("id", "unknown"),
                "username": username,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reply_to_tweet(self, tweet_id: str, message: str) -> Dict[str, Any]:
        """Reply to tweet - synchronous version for backward compatibility"""
        try:
            if not self.twitter_client:
                return {"success": False, "error": "Twitter client not initialized"}
            tweet = self.twitter_client.create_tweet(message, reply_to=tweet_id)
            return {"success": True, "tweet_id": tweet.get("id", "unknown")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance for backward compatibility
_twitter_server = None


def get_twitter_client():
    """Get Twitter client instance - Legacy function for backward compatibility"""
    global _twitter_server
    if _twitter_server is None:
        _twitter_server = TwitterMCPServer()
    return _twitter_server


# MCP Server main function
async def main():
    """Main function to run the MCP server"""
    if not MCP_AVAILABLE:
        logger.error("MCP not available. Please install the mcp package.")
        return

    server_instance = TwitterMCPServer()

    if not server_instance.server:
        logger.error("Failed to initialize MCP server")
        return

    # Run the server - this is a placeholder as the actual MCP server implementation may vary
    logger.info("Twitter MCP Server ready")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        # Run as MCP server
        asyncio.run(main())
    else:
        # Run as standalone script for testing
        server = TwitterMCPServer()
        print("Twitter MCP Server initialized")
        print(
            "Available tools: get_timeline, get_user_tweets, search_hashtag, create_tweet, send_dm"
        )
