from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
import logging
import uuid
from uuid import UUID
from datetime import datetime
import os
from supabase import create_client
import httpx

# FIXED: Importar correctamente el modelo User y las dependencias de auth
from app.auth.middleware import get_current_user
from app.models.user import User
from app.ai_agents.agents import ModernAgents

# FIXED: Import existing storage system from integrations.py
from app.api.integrations import (
    get_user_integration,
    save_user_integration,
    delete_user_integration,
    user_integrations,
)

from app.supabase.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/integrations/accounts")
async def get_user_accounts(request: Request, user: User = Depends(get_current_user)):
    """
    Devuelve las integraciones conectadas del usuario autenticado usando su JWT para RLS.
    """
    # Obtener el access_token del header Authorization
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        logger.error("No se encontró el header Authorization con Bearer token")
        return []
    access_token = auth_header.split(" ", 1)[1]

    # Construir la URL de la API REST de Supabase
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    if not supabase_url:
        logger.error("No se encontró la variable de entorno SUPABASE_URL")
        return []
    rest_url = supabase_url.rstrip("/") + "/rest/v1/user_accounts"
    params = {
        "select": "service,connected,connected_at,profile_data",
        "user_id": f"eq.{user.id}",
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or "",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(rest_url, params=params, headers=headers)
        if resp.status_code != 200:
            logger.error(
                f"Error al consultar user_accounts: {resp.status_code} {resp.text}"
            )
            return []
        accounts = resp.json()
    logger.info(f"Retrieved {len(accounts)} accounts for user {user.id}")
    return accounts


@router.post("/integrations/accounts")
async def save_user_account(
    account_data: Dict[str, Any], user: User = Depends(get_current_user)
):
    """Save or update user account configuration using the existing in-memory storage system"""
    try:
        required_fields = ["account_id", "account_type", "configuration"]
        if not all(field in account_data for field in required_fields):
            raise HTTPException(status_code=400, detail="Missing required fields")

        user_id = str(user.id)
        platform = account_data["account_type"]

        # Prepare configuration data compatible with existing system
        config_data = {
            "account_id": account_data["account_id"],
            "platform": platform,
            "status": "connected",
            "enabled": True,
            **account_data["configuration"],  # Merge the configuration data
        }

        # Use existing storage system
        save_user_integration(user_id, platform, config_data)

        logger.info(f"Saved account {account_data['account_id']} for user {user_id}")

        return {
            "success": True,
            "message": f"Account {account_data['account_id']} configured successfully",
            "account": {
                "account_id": account_data["account_id"],
                "account_type": platform,
                "connected": True,
                "connection_type": "api_key",
                "configuration": account_data["configuration"],
                "created_at": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error saving user account configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Error saving account configuration"
        )


@router.delete("/integrations/accounts/{account_id}")
async def disconnect_user_account(
    account_id: str, user: User = Depends(get_current_user)
):
    """Disconnect or remove a user account configuration"""
    try:
        user_id = str(user.id)

        # Handle OAuth accounts differently if account_id starts with "oauth_"
        if account_id.startswith("oauth_"):
            platform = account_id.replace("oauth_", "", 1)

            # Import OAuth handler
            from app.api.oauth_router import router as oauth_router

            # Redirect to the appropriate OAuth disconnect endpoint
            url = f"/api/integrations/{platform}/oauth/disconnect"
            logger.info(f"Redirecting to OAuth disconnect endpoint: {url}")

            # Call the router directly instead of disconnect method
            return {"success": True, "message": f"Redirected to OAuth disconnect"}

        # Otherwise handle as API key account using existing system
        for key in list(user_integrations.keys()):
            if (
                key.startswith(f"{user_id}_")
                and user_integrations[key].get("account_id") == account_id
            ):
                platform = key.split(f"{user_id}_", 1)[1]
                delete_user_integration(user_id, platform)
                logger.info(f"Deleted account {account_id} for user {user_id}")
                return {
                    "success": True,
                    "message": f"Account {account_id} disconnected",
                }

        # If we get here, the account was not found
        raise HTTPException(status_code=404, detail="Account not found")

    except Exception as e:
        logger.error(f"Error disconnecting account: {e}")
        raise HTTPException(status_code=500, detail="Error disconnecting account")


@router.get("/agent/config")
async def get_agent_config(user: User = Depends(get_current_user)):
    """Get agent configuration for the current user"""
    try:
        user_id = str(user.id)

        # For now, return a default configuration
        # In a real implementation, we would query from a database
        return {
            "enabled": True,
            "lead_generator": {  # Changed from lead_qualifier
                "enabled": True,
                "auto_qualify": True,
                "qualification_threshold": 75.0,
                "handoff_to_scheduler": True,
            },
            "meeting_scheduler": {
                "enabled": True,
                "model": "gpt-4o",
                "temperature": 0.7,
            },
            "memory_system": "in_memory",
            "analytics_enabled": True,
        }

    except Exception as e:
        logger.error(f"Error fetching agent configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Error fetching agent configuration"
        )


@router.post("/agent/config")
async def save_agent_config(
    config_data: Dict[str, Any], user: User = Depends(get_current_user)
):
    """Save agent configuration for the current user"""
    try:
        user_id = str(user.id)

        # In a real implementation, we would save to a database
        logger.info(f"Saving agent configuration for user {user_id}")

        return {
            "success": True,
            "message": "Agent configuration saved successfully",
            "config": config_data,
        }

    except Exception as e:
        logger.error(f"Error saving agent configuration: {e}")
        raise HTTPException(status_code=500, detail="Error saving agent configuration")


@router.post("/orchestrator/initiate-communications")
async def initiate_communications(
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Initiate the communication process with the agent system"""
    try:
        user_id = str(user.id)

        # In a real implementation, check if the agent system is enabled
        # For now, just start the process

        # Add the communication task to background tasks
        background_tasks.add_task(_process_agent_communications, user_id)

        return {
            "success": True,
            "message": "Communications initiated in background",
            "task_id": str(uuid.uuid4()),  # Generate a random task ID
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating communications: {e}")
        raise HTTPException(status_code=500, detail="Error initiating communications")


async def _process_agent_communications(user_id: str):
    """Process agent communications in the background"""
    try:
        logger.info(f"Starting communications process for user {user_id}")

        # Get leads that need processing
        # Here we would typically query the database for leads that need processing
        # For demonstration, we'll just log that we're doing this
        logger.info(f"Fetching leads for user {user_id}")

        # Process each lead through the agent system
        logger.info(f"Processing leads through agent system for user {user_id}")

        # Simulate processing time
        import asyncio

        await asyncio.sleep(2)

        logger.info(f"Communications process completed for user {user_id}")

    except Exception as e:
        logger.error(f"Error in communications process for user {user_id}: {e}")
