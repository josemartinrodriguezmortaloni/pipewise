# app/api/config.py - Configuración de rutas para el frontend
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, List, Any
import logging
from datetime import datetime

from app.auth.middleware import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

# Crear router para configuración
router = APIRouter(prefix="/config", tags=["Configuration"])


# ===================== CONFIGURACIÓN DEL FRONTEND =====================


@router.get("/routes")
async def get_available_routes(
    current_user: User = Depends(get_current_user),
):
    """Obtener todas las rutas disponibles para el frontend"""
    try:
        user_role = current_user.role.value

        # Rutas base disponibles para todos los usuarios
        base_routes = {
            "auth": {
                "login": "/auth/login",
                "logout": "/auth/logout",
                "register": "/auth/register",
                "profile": "/auth/profile",
                "change_password": "/auth/change-password",
                "refresh_token": "/auth/refresh",
                "validate_token": "/auth/validate",
                "2fa": {
                    "enable": "/auth/2fa/enable",
                    "verify": "/auth/2fa/verify",
                    "disable": "/auth/2fa/disable",
                    "login": "/auth/login/2fa",
                },
            },
            "crm": {
                "leads": {
                    "list": "/api/leads",
                    "create": "/api/leads",
                    "detail": "/api/leads/{id}",
                    "update": "/api/leads/{id}",
                    "delete": "/api/leads/{id}",
                },
                "opportunities": {
                    "list": "/api/opportunities",
                    "create": "/api/opportunities",
                    "detail": "/api/opportunities/{id}",
                    "update": "/api/opportunities/{id}",
                    "delete": "/api/opportunities/{id}",
                },
                "contacts": {
                    "list": "/api/contacts",
                    "create": "/api/contacts",
                    "detail": "/api/contacts/{id}",
                    "update": "/api/contacts/{id}",
                    "delete": "/api/contacts/{id}",
                },
                "activities": {
                    "list": "/api/activities",
                    "create": "/api/activities",
                    "detail": "/api/activities/{id}",
                    "update": "/api/activities/{id}",
                    "delete": "/api/activities/{id}",
                },
                "dashboard": "/api/dashboard",
                "pipeline": "/api/pipeline",
                "reports": {
                    "list": "/api/reports",
                    "generate": "/api/reports",
                },
            },
            "search": {
                "search": "/search/",
                "suggestions": "/search/suggestions",
                "recent": "/search/recent",
                "export": {
                    "leads": "/search/export/leads",
                    "opportunities": "/search/export/opportunities",
                    "contacts": "/search/export/contacts",
                },
            },
            "notifications": {
                "list": "/webhooks/notifications",
                "create": "/webhooks/notifications",
                "mark_read": "/webhooks/notifications/{id}/read",
                "delete": "/webhooks/notifications/{id}",
            },
            "webhooks": {
                "lead_capture": "/webhooks/lead-capture",
                "form_submission": "/webhooks/form-submission",
                "email_event": "/webhooks/email-event",
            },
        }

        # Rutas adicionales para managers
        if user_role in ["manager", "admin"]:
            base_routes["search"]["import"] = {
                "leads": "/search/import/leads",
                "status": "/search/import/status/{import_id}",
            }

        # Rutas adicionales para admins
        if user_role == "admin":
            base_routes["admin"] = {
                "users": {
                    "list": "/auth/admin/users",
                    "update": "/auth/admin/users/{user_id}",
                    "stats": "/auth/admin/stats",
                },
                "system": {
                    "users": "/api/admin/users",
                    "stats": "/api/admin/stats",
                },
                "integrations": {
                    "list": "/webhooks/integrations",
                    "create": "/webhooks/integrations",
                    "trigger": "/webhooks/trigger/{event_type}",
                },
            }

        return {
            "routes": base_routes,
            "user_role": user_role,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Get routes error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available routes",
        )


@router.get("/frontend")
async def get_frontend_config(
    current_user: User = Depends(get_current_user),
):
    """Obtener configuración completa para el frontend"""
    try:
        user_role = current_user.role.value

        config = {
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "full_name": current_user.full_name,
                "role": user_role,
                "permissions": get_user_permissions(user_role),
                "has_2fa": current_user.has_2fa,
                "email_confirmed": current_user.email_confirmed,
            },
            "app": {
                "name": "PipeWise CRM",
                "version": "2.0.0",
                "features": get_available_features(user_role),
                "limits": get_user_limits(user_role),
            },
            "ui": {
                "theme": "default",
                "navigation": get_navigation_config(user_role),
                "dashboard_widgets": get_dashboard_widgets(user_role),
            },
            "api": {
                "base_url": "/",
                "timeout": 30000,
                "rate_limits": get_rate_limits(user_role),
            },
            "notifications": {
                "enabled": True,
                "sound": False,
                "desktop": True,
                "email": True,
            },
        }

        return config

    except Exception as e:
        logger.error(f"Get frontend config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get frontend configuration",
        )


@router.get("/permissions")
async def get_user_permissions_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Obtener permisos del usuario actual"""
    try:
        permissions = get_user_permissions(current_user.role.value)
        return {
            "user_id": str(current_user.id),
            "role": current_user.role.value,
            "permissions": permissions,
        }

    except Exception as e:
        logger.error(f"Get permissions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user permissions",
        )


@router.get("/features")
async def get_available_features_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Obtener funcionalidades disponibles para el usuario"""
    try:
        features = get_available_features(current_user.role.value)
        return {
            "user_role": current_user.role.value,
            "features": features,
        }

    except Exception as e:
        logger.error(f"Get features error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available features",
        )


# ===================== FUNCIONES AUXILIARES =====================


def get_user_permissions(role: str) -> Dict[str, List[str]]:
    """Obtener permisos basados en el rol del usuario"""
    base_permissions = {
        "leads": ["read", "create"],
        "contacts": ["read", "create"],
        "activities": ["read", "create", "update"],
        "opportunities": ["read"],
        "notifications": ["read", "create"],
        "profile": ["read", "update"],
    }

    if role == "user":
        return base_permissions

    elif role == "manager":
        return {
            **base_permissions,
            "leads": ["read", "create", "update", "delete"],
            "contacts": ["read", "create", "update", "delete"],
            "opportunities": ["read", "create", "update"],
            "reports": ["read", "create"],
            "team": ["read"],
            "import": ["create"],
        }

    elif role == "admin":
        return {
            "leads": ["read", "create", "update", "delete", "export"],
            "contacts": ["read", "create", "update", "delete", "export"],
            "activities": ["read", "create", "update", "delete"],
            "opportunities": ["read", "create", "update", "delete", "export"],
            "reports": ["read", "create", "update", "delete"],
            "users": ["read", "create", "update", "delete"],
            "system": ["read", "update"],
            "integrations": ["read", "create", "update", "delete"],
            "notifications": ["read", "create", "update", "delete"],
            "profile": ["read", "update"],
            "import": ["create", "read"],
            "export": ["create"],
        }

    return base_permissions


def get_available_features(role: str) -> List[str]:
    """Obtener funcionalidades disponibles por rol"""
    base_features = [
        "leads_management",
        "contacts_management",
        "activities_tracking",
        "basic_reporting",
        "notifications",
        "search",
        "profile_management",
        "2fa_authentication",
    ]

    if role == "manager":
        base_features.extend(
            [
                "opportunities_management",
                "advanced_reporting",
                "team_overview",
                "data_import",
                "pipeline_view",
            ]
        )

    elif role == "admin":
        base_features.extend(
            [
                "opportunities_management",
                "advanced_reporting",
                "user_management",
                "system_administration",
                "integrations_management",
                "data_import",
                "data_export",
                "pipeline_view",
                "webhook_management",
                "system_metrics",
            ]
        )

    return base_features


def get_user_limits(role: str) -> Dict[str, int]:
    """Obtener límites por rol de usuario"""
    if role == "user":
        return {
            "leads_per_month": 100,
            "contacts_per_month": 200,
            "activities_per_day": 50,
            "export_per_month": 0,
            "storage_mb": 100,
        }
    elif role == "manager":
        return {
            "leads_per_month": 1000,
            "contacts_per_month": 2000,
            "activities_per_day": 500,
            "export_per_month": 10,
            "storage_mb": 1000,
        }
    elif role == "admin":
        return {
            "leads_per_month": -1,  # Ilimitado
            "contacts_per_month": -1,
            "activities_per_day": -1,
            "export_per_month": -1,
            "storage_mb": -1,
        }

    return {}


def get_navigation_config(role: str) -> List[Dict[str, Any]]:
    """Obtener configuración de navegación por rol"""
    base_navigation = [
        {
            "name": "Dashboard",
            "path": "/dashboard",
            "icon": "dashboard",
            "order": 1,
        },
        {
            "name": "Leads",
            "path": "/leads",
            "icon": "people",
            "order": 2,
        },
        {
            "name": "Contacts",
            "path": "/contacts",
            "icon": "contacts",
            "order": 3,
        },
        {
            "name": "Activities",
            "path": "/activities",
            "icon": "event",
            "order": 4,
        },
    ]

    if role in ["manager", "admin"]:
        base_navigation.extend(
            [
                {
                    "name": "Opportunities",
                    "path": "/opportunities",
                    "icon": "trending_up",
                    "order": 5,
                },
                {
                    "name": "Reports",
                    "path": "/reports",
                    "icon": "bar_chart",
                    "order": 6,
                },
            ]
        )

    if role == "admin":
        base_navigation.extend(
            [
                {
                    "name": "Users",
                    "path": "/admin/users",
                    "icon": "people",
                    "order": 7,
                },
                {
                    "name": "Settings",
                    "path": "/admin/settings",
                    "icon": "settings",
                    "order": 8,
                },
            ]
        )

    return sorted(base_navigation, key=lambda x: x["order"])


def get_dashboard_widgets(role: str) -> List[Dict[str, Any]]:
    """Obtener widgets disponibles para el dashboard"""
    base_widgets = [
        {
            "id": "leads_summary",
            "name": "Leads Summary",
            "type": "metrics",
            "size": "medium",
            "enabled": True,
        },
        {
            "id": "recent_activities",
            "name": "Recent Activities",
            "type": "list",
            "size": "large",
            "enabled": True,
        },
        {
            "id": "contacts_chart",
            "name": "Contacts Growth",
            "type": "chart",
            "size": "medium",
            "enabled": True,
        },
    ]

    if role in ["manager", "admin"]:
        base_widgets.extend(
            [
                {
                    "id": "pipeline_overview",
                    "name": "Sales Pipeline",
                    "type": "pipeline",
                    "size": "large",
                    "enabled": True,
                },
                {
                    "id": "revenue_chart",
                    "name": "Revenue Forecast",
                    "type": "chart",
                    "size": "large",
                    "enabled": True,
                },
            ]
        )

    if role == "admin":
        base_widgets.extend(
            [
                {
                    "id": "system_health",
                    "name": "System Health",
                    "type": "status",
                    "size": "small",
                    "enabled": True,
                },
                {
                    "id": "user_activity",
                    "name": "User Activity",
                    "type": "chart",
                    "size": "medium",
                    "enabled": True,
                },
            ]
        )

    return base_widgets


def get_rate_limits(role: str) -> Dict[str, int]:
    """Obtener límites de rate limiting por rol"""
    if role == "user":
        return {
            "requests_per_minute": 60,
            "search_per_minute": 10,
            "export_per_hour": 0,
        }
    elif role == "manager":
        return {
            "requests_per_minute": 120,
            "search_per_minute": 30,
            "export_per_hour": 5,
        }
    elif role == "admin":
        return {
            "requests_per_minute": 300,
            "search_per_minute": 100,
            "export_per_hour": 20,
        }

    return {}
