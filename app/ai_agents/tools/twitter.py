"""
Twitter MCP Server for PipeWise CRM

This module provides Twitter/X integration capabilities for the AI agents
to interact with Twitter API for lead generation and outreach.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TwitterMCPServer:
    """Twitter MCP Server for agent-based Twitter interactions"""

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

        # Check if Twitter is configured
        self.enabled = bool(self.bearer_token or (self.api_key and self.api_secret))

        if not self.enabled:
            logger.warning(
                "⚠️ Twitter API credentials not found. Twitter features will be limited."
            )
        else:
            logger.info("✅ Twitter MCP Server initialized")

    def is_configured(self) -> bool:
        """Check if Twitter API is properly configured"""
        return self.enabled

    def send_dm(self, username: str, message: str) -> Dict[str, Any]:
        """Send a direct message to a Twitter user"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Twitter API not configured",
                "demo_mode": True,
                "simulated_result": f"Would send DM to @{username}: {message[:50]}...",
            }

        try:
            # In a real implementation, you would use the Twitter API here
            # For now, return a simulated success
            return {
                "success": True,
                "username": username,
                "message_sent": message,
                "timestamp": "2025-01-07T12:00:00Z",
                "demo_mode": True,
            }
        except Exception as e:
            logger.error(f"Error sending Twitter DM: {e}")
            return {"success": False, "error": str(e), "username": username}

    def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get information about a Twitter user"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Twitter API not configured",
                "demo_mode": True,
                "user": {
                    "username": username,
                    "display_name": username.title(),
                    "followers_count": 1234,
                    "following_count": 567,
                    "bio": f"Sample bio for @{username}",
                    "verified": False,
                },
            }

        try:
            # In a real implementation, you would use the Twitter API here
            return {
                "success": True,
                "user": {
                    "username": username,
                    "display_name": username.title(),
                    "followers_count": 1234,
                    "following_count": 567,
                    "bio": f"Bio for @{username}",
                    "verified": False,
                },
                "demo_mode": True,
            }
        except Exception as e:
            logger.error(f"Error getting Twitter user info: {e}")
            return {"success": False, "error": str(e), "username": username}

    def reply_to_tweet(self, tweet_id: str, message: str) -> Dict[str, Any]:
        """Reply to a specific tweet"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Twitter API not configured",
                "demo_mode": True,
                "simulated_result": f"Would reply to tweet {tweet_id}: {message[:50]}...",
            }

        try:
            # In a real implementation, you would use the Twitter API here
            return {
                "success": True,
                "tweet_id": tweet_id,
                "reply_message": message,
                "timestamp": "2025-01-07T12:00:00Z",
                "demo_mode": True,
            }
        except Exception as e:
            logger.error(f"Error replying to tweet: {e}")
            return {"success": False, "error": str(e), "tweet_id": tweet_id}

    def search_tweets(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search for tweets based on a query"""
        if not self.enabled:
            return {
                "success": False,
                "error": "Twitter API not configured",
                "demo_mode": True,
                "simulated_results": [
                    {
                        "id": "123456789",
                        "text": f"Sample tweet mentioning {query}",
                        "author": "sample_user",
                        "created_at": "2025-01-07T12:00:00Z",
                    }
                ],
            }

        try:
            # In a real implementation, you would use the Twitter API here
            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "id": "123456789",
                        "text": f"Sample tweet about {query}",
                        "author": "sample_user",
                        "created_at": "2025-01-07T12:00:00Z",
                    }
                ],
                "max_results": max_results,
                "demo_mode": True,
            }
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return {"success": False, "error": str(e), "query": query}


def get_twitter_mcp_server(user_id: Optional[str] = None) -> TwitterMCPServer:
    """Get instance of Twitter MCP Server"""
    return TwitterMCPServer(user_id=user_id)


# Demo and testing
if __name__ == "__main__":
    print("🐦 Testing Twitter MCP Server")
    print("=" * 50)

    # Initialize server
    server = TwitterMCPServer("test_user")

    # Test configuration
    print(f"📋 Twitter configured: {server.is_configured()}")

    # Test DM
    dm_result = server.send_dm("JoseMartinAI", "Hello from PipeWise!")
    print(f"📩 DM Result: {dm_result}")

    # Test user info
    user_info = server.get_user_info("JoseMartinAI")
    print(f"👤 User Info: {user_info}")

    # Test reply
    reply_result = server.reply_to_tweet("123456", "Great post!")
    print(f"💬 Reply Result: {reply_result}")

    print("\n✅ Twitter MCP Server Test Complete!")
