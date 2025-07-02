"""
OAuth Router for PipeWise Integrations

Provides OAuth 2.0 endpoints for external service integrations.
Handles authorization initiation and callback processing.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional
import logging

from app.api.oauth_handler import oauth_handler
from app.auth.middleware import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["oauth"])


# OAuth Start Endpoints (Redirect to Provider)
@router.get("/calendly/oauth/start")
async def start_calendly_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Calendly OAuth flow"""
    logger.info("🚀 Calendly OAuth start endpoint called")
    logger.info(f"👤 Current user: {current_user.id if current_user else 'None'}")
    logger.debug(f"📋 Redirect URL: {redirect_url}")

    try:
        logger.info(f"Iniciando OAuth Calendly para user_id={current_user.id}")
        auth_url = await oauth_handler.generate_authorization_url(
            service="calendly", user_id=str(current_user.id), redirect_url=redirect_url
        )
        logger.info(f"✅ Successfully generated Calendly auth URL")
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"❌ Error starting Calendly OAuth: {e}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/google_calendar/oauth/start")
async def start_google_calendar_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Google Calendar OAuth flow"""
    logger.info("🚀 Google Calendar OAuth start endpoint called")
    logger.info(f"👤 Current user: {current_user.id if current_user else 'None'}")
    logger.debug(f"📋 Redirect URL: {redirect_url}")

    try:
        logger.info(f"Iniciando OAuth Google Calendar para user_id={current_user.id}")
        auth_url = await oauth_handler.generate_authorization_url(
            service="google_calendar",
            user_id=str(current_user.id),
            redirect_url=redirect_url,
        )
        logger.info(f"✅ Successfully generated Google Calendar auth URL")
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"❌ Error starting Google Calendar OAuth: {e}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/pipedrive/oauth/start")
async def start_pipedrive_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Pipedrive OAuth flow"""
    logger.info("🚀 Pipedrive OAuth start endpoint called")
    logger.info(f"👤 Current user: {current_user.id if current_user else 'None'}")
    logger.debug(f"📋 Redirect URL: {redirect_url}")

    try:
        auth_url = await oauth_handler.generate_authorization_url(
            service="pipedrive", user_id=str(current_user.id), redirect_url=redirect_url
        )
        logger.info(f"✅ Successfully generated Pipedrive auth URL")
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"❌ Error starting Pipedrive OAuth: {e}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/salesforce_rest_api/oauth/start")
async def start_salesforce_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Salesforce OAuth flow"""
    try:
        auth_url = await oauth_handler.generate_authorization_url(
            service="salesforce_rest_api",
            user_id=str(current_user.id),
            redirect_url=redirect_url,
        )
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"Error starting Salesforce OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/zoho_crm/oauth/start")
async def start_zoho_crm_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Zoho CRM OAuth flow"""
    try:
        auth_url = await oauth_handler.generate_authorization_url(
            service="zoho_crm", user_id=str(current_user.id), redirect_url=redirect_url
        )
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"Error starting Zoho CRM OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/twitter_account/oauth/start")
async def start_twitter_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Twitter OAuth flow"""
    try:
        auth_url = await oauth_handler.generate_authorization_url(
            service="twitter_account",
            user_id=str(current_user.id),
            redirect_url=redirect_url,
        )
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"Error starting Twitter OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/instagram_account/oauth/start")
async def start_instagram_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start Instagram OAuth flow"""
    try:
        auth_url = await oauth_handler.generate_authorization_url(
            service="instagram_account",
            user_id=str(current_user.id),
            redirect_url=redirect_url,
        )
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"Error starting Instagram OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/sendgrid_email/oauth/start")
async def start_sendgrid_oauth(
    current_user: User = Depends(get_current_user),
    redirect_url: Optional[str] = Query(
        None, description="Frontend redirect URL after completion"
    ),
):
    """Start SendGrid OAuth flow"""
    try:
        auth_url = await oauth_handler.generate_authorization_url(
            service="sendgrid_email",
            user_id=str(current_user.id),
            redirect_url=redirect_url,
        )
        return JSONResponse({"authorization_url": auth_url})
    except Exception as e:
        logger.error(f"Error starting SendGrid OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


# OAuth Callback Endpoints (Handle Provider Response)
@router.get("/calendly/oauth/callback")
async def calendly_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Calendly OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="calendly", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=calendly")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Calendly OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=calendly", status_code=302)


@router.get("/google_calendar/oauth/callback")
async def google_calendar_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Google Calendar OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="google_calendar", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get(
            "redirect_url", "/integrations?success=google_calendar"
        )
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google Calendar OAuth callback error: {e}")
        return RedirectResponse(
            url="/integrations?error=google_calendar", status_code=302
        )


@router.get("/pipedrive/oauth/callback")
async def pipedrive_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Pipedrive OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="pipedrive", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=pipedrive")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipedrive OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=pipedrive", status_code=302)


@router.get("/salesforce_rest_api/oauth/callback")
async def salesforce_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Salesforce OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="salesforce_rest_api", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=salesforce")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Salesforce OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=salesforce", status_code=302)


@router.get("/zoho_crm/oauth/callback")
async def zoho_crm_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Zoho CRM OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="zoho_crm", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=zoho_crm")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zoho CRM OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=zoho_crm", status_code=302)


@router.get("/twitter_account/oauth/callback")
async def twitter_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Twitter OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="twitter_account", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=twitter")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Twitter OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=twitter", status_code=302)


@router.get("/instagram_account/oauth/callback")
async def instagram_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle Instagram OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="instagram_account", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=instagram")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Instagram OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=instagram", status_code=302)


@router.get("/sendgrid_email/oauth/callback")
async def sendgrid_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle SendGrid OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(
                status_code=400, detail="Missing code or state parameter"
            )

        result = await oauth_handler.handle_oauth_callback(
            service="sendgrid_email", code=code, state=state, error=error
        )

        # Redirect to frontend with success
        frontend_url = result.get("redirect_url", "/integrations?success=sendgrid")
        return RedirectResponse(url=frontend_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SendGrid OAuth callback error: {e}")
        return RedirectResponse(url="/integrations?error=sendgrid", status_code=302)


# Generic OAuth Management Endpoints
@router.post("/{service}/oauth/disconnect")
async def disconnect_oauth_service(
    service: str, current_user: User = Depends(get_current_user)
):
    """Disconnect an OAuth service"""
    try:
        # Remove the integration from database
        supabase = oauth_handler.supabase
        result = (
            supabase.table("user_accounts")
            .delete()
            .eq("user_id", str(current_user.id))
            .eq("service", service)
            .execute()
        )

        if result.data:
            logger.info(
                f"Successfully disconnected {service} for user {current_user.id}"
            )
            return {"success": True, "message": f"Disconnected from {service}"}
        else:
            raise HTTPException(status_code=404, detail="Integration not found")

    except Exception as e:
        logger.error(f"Error disconnecting {service}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect service")


@router.get("/{service}/oauth/status")
async def get_oauth_status(
    service: str, current_user: User = Depends(get_current_user)
):
    """Get OAuth connection status for a service"""
    try:
        supabase = oauth_handler.supabase
        result = (
            supabase.table("user_accounts")
            .select("connected, connected_at, profile_data")
            .eq("user_id", str(current_user.id))
            .eq("service", service)
            .execute()
        )

        if result.data:
            account = result.data[0]
            return {
                "service": service,
                "connected": account.get("connected", False),
                "connected_at": account.get("connected_at"),
                "profile": account.get("profile_data", {}),
            }
        else:
            return {
                "service": service,
                "connected": False,
                "connected_at": None,
                "profile": {},
            }

    except Exception as e:
        logger.error(f"Error getting OAuth status for {service}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service status")


@router.post("/{service}/oauth/refresh")
async def refresh_oauth_token(
    service: str, current_user: User = Depends(get_current_user)
):
    """Manually refresh OAuth token for a service"""
    try:
        success = await oauth_handler.refresh_token_if_needed(
            user_id=str(current_user.id), service=service
        )

        if success:
            return {"success": True, "message": f"Token refreshed for {service}"}
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to refresh token. Re-authentication may be required.",
            )

    except Exception as e:
        logger.error(f"Error refreshing token for {service}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")
