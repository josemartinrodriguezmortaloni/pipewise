# app/api/webhooks.py - Rutas para webhooks y notificaciones
from fastapi import APIRouter, HTTPException, status, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime

from app.auth.middleware import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.crm_schema import (
    WebhookEvent,
    NotificationRequest,
    NotificationResponse,
    IntegrationConfig,
)
from app.auth.utils import get_client_ip, hash_token

logger = logging.getLogger(__name__)

# Crear router para webhooks
router = APIRouter(prefix="/webhooks", tags=["Webhooks & Notifications"])


# ===================== WEBHOOKS ENTRANTES =====================


@router.post("/lead-capture")
async def capture_lead_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Capturar leads desde formularios web externos"""
    try:
        client_ip = get_client_ip(request)
        data = await request.json()

        # Validar datos mínimos requeridos
        required_fields = ["name", "email"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        # Procesar lead en background
        background_tasks.add_task(process_webhook_lead, data, client_ip)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Lead received and will be processed",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Webhook lead capture error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to process webhook", "detail": str(e)},
        )


@router.post("/form-submission")
async def form_submission_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Webhook para formularios de contacto"""
    try:
        data = await request.json()
        client_ip = get_client_ip(request)

        # Agregar metadata
        data["source"] = "form_webhook"
        data["ip_address"] = client_ip
        data["received_at"] = datetime.utcnow().isoformat()

        # Procesar en background
        background_tasks.add_task(process_form_submission, data)

        return {"status": "received", "message": "Form submission processed"}

    except Exception as e:
        logger.error(f"Form submission webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process form submission",
        )


@router.post("/email-event")
async def email_event_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Webhook para eventos de email (opens, clicks, bounces)"""
    try:
        data = await request.json()

        # Procesar evento de email
        background_tasks.add_task(process_email_event, data)

        return {"status": "received"}

    except Exception as e:
        logger.error(f"Email event webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process email event",
        )


# ===================== NOTIFICACIONES =====================


@router.post("/notifications", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationRequest,
    current_user: User = Depends(get_current_user),
):
    """Crear nueva notificación"""
    try:
        # Simular creación de notificación
        return NotificationResponse(
            id="notif_123",
            title=notification_data.title,
            message=notification_data.message,
            type=notification_data.type,
            read=False,
            user_id=notification_data.user_id or str(current_user.id),
            entity_type=notification_data.entity_type,
            entity_id=notification_data.entity_id,
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Create notification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification",
        )


@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
):
    """Obtener notificaciones del usuario"""
    try:
        # Simular respuesta de notificaciones
        notifications = []  # Implementar consulta real

        return notifications

    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notifications",
        )


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """Marcar notificación como leída"""
    try:
        # Implementar marcado como leída
        return {"message": "Notification marked as read", "id": notification_id}

    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read",
        )


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """Eliminar notificación"""
    try:
        # Implementar eliminación
        return {"message": "Notification deleted", "id": notification_id}

    except Exception as e:
        logger.error(f"Delete notification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification",
        )


# ===================== CONFIGURACIÓN DE INTEGRACIONES =====================


@router.get("/integrations")
async def get_integrations(
    current_user: User = Depends(get_current_user),
):
    """Obtener configuraciones de integración"""
    try:
        # Solo admins pueden ver todas las integraciones
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        # Simular integraciones
        integrations = [
            {
                "id": "zapier_001",
                "name": "Zapier Integration",
                "type": "automation",
                "enabled": True,
                "webhook_url": "https://hooks.zapier.com/hooks/catch/...",
                "events": ["lead_created", "opportunity_won"],
            },
            {
                "id": "mailchimp_001",
                "name": "MailChimp Sync",
                "type": "email_marketing",
                "enabled": False,
                "webhook_url": None,
                "events": ["lead_created", "contact_updated"],
            },
        ]

        return {"integrations": integrations}

    except Exception as e:
        logger.error(f"Get integrations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integrations",
        )


@router.post("/integrations")
async def create_integration(
    integration_data: IntegrationConfig,
    admin_user: User = Depends(get_admin_user),
):
    """Crear nueva integración"""
    try:
        # Implementar creación de integración
        return {
            "id": "integration_123",
            "name": integration_data.name,
            "type": integration_data.type,
            "enabled": integration_data.enabled,
            "webhook_url": integration_data.webhook_url,
            "created_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Create integration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create integration",
        )


# ===================== WEBHOOKS SALIENTES =====================


@router.post("/trigger/{event_type}")
async def trigger_webhook_event(
    event_type: str,
    event_data: Dict[str, Any],
    admin_user: User = Depends(get_admin_user),
):
    """Disparar evento de webhook manualmente"""
    try:
        # Crear evento
        webhook_event = WebhookEvent(
            event_type=event_type,
            entity_type=event_data.get("entity_type", "unknown"),
            entity_id=event_data.get("entity_id", ""),
            data=event_data,
            timestamp=datetime.utcnow(),
            source="manual_trigger",
        )

        # Procesar webhook en background
        # background_tasks.add_task(send_webhook_event, webhook_event)

        return {
            "success": True,
            "event_type": event_type,
            "message": "Webhook event triggered",
            "timestamp": webhook_event.timestamp.isoformat(),
        }

    except Exception as e:
        logger.error(f"Trigger webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger webhook event",
        )


# ===================== FUNCIONES AUXILIARES =====================


async def process_webhook_lead(lead_data: dict, ip_address: str):
    """Procesar lead recibido por webhook"""
    try:
        logger.info(f"Processing webhook lead: {lead_data['email']}")

        # Aquí integrar con el sistema de CRM
        # 1. Validar y limpiar datos
        # 2. Crear lead en la base de datos
        # 3. Ejecutar agentes de IA si es necesario
        # 4. Enviar notificaciones

        # Simular procesamiento
        lead_id = f"lead_{hash_token(lead_data['email'])[:8]}"

        logger.info(f"Webhook lead processed successfully: {lead_id}")

    except Exception as e:
        logger.error(f"Error processing webhook lead: {e}")


async def process_form_submission(form_data: dict):
    """Procesar envío de formulario"""
    try:
        logger.info(
            f"Processing form submission from {form_data.get('source', 'unknown')}"
        )

        # Implementar lógica de procesamiento
        # 1. Validar datos del formulario
        # 2. Crear lead o contacto
        # 3. Enviar email de confirmación
        # 4. Notificar al equipo de ventas

    except Exception as e:
        logger.error(f"Error processing form submission: {e}")


async def process_email_event(event_data: dict):
    """Procesar evento de email"""
    try:
        event_type = event_data.get("event", "unknown")
        logger.info(f"Processing email event: {event_type}")

        # Implementar lógica según el tipo de evento
        # - open: Marcar email como abierto
        # - click: Registrar click en enlace
        # - bounce: Marcar email como inválido
        # - complaint: Manejar queja de spam

    except Exception as e:
        logger.error(f"Error processing email event: {e}")


async def send_webhook_event(webhook_event: WebhookEvent):
    """Enviar evento a webhooks configurados"""
    try:
        logger.info(f"Sending webhook event: {webhook_event.event_type}")

        # Implementar envío a URLs configuradas
        # 1. Obtener integraciones activas para este evento
        # 2. Preparar payload
        # 3. Enviar HTTP POST a cada webhook URL
        # 4. Manejar reintentos en caso de error

    except Exception as e:
        logger.error(f"Error sending webhook event: {e}")
