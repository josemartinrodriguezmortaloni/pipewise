# app/services/email_service.py
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio de envío de emails"""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.enabled = bool(self.smtp_username and self.smtp_password)

        if not self.enabled:
            logger.warning("Email service disabled - missing SMTP credentials")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Enviar email"""
        try:
            if not self.enabled:
                logger.info(
                    f"Email service disabled - would send to {to_email}: {subject}"
                )
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Agregar contenido de texto
            text_part = MIMEText(body, "plain")
            msg.attach(text_part)

            # Agregar contenido HTML si existe
            if html_body:
                html_part = MIMEText(html_body, "html")
                msg.attach(html_part)

            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_confirmation_email(self, email: str, token: str) -> bool:
        """Enviar email de confirmación"""
        subject = "Confirm your email - PipeWise CRM"
        body = f"""
        Please confirm your email address by clicking the link below:
        
        {os.getenv("FRONTEND_URL", "http://localhost:3000")}/confirm-email?token={token}
        
        If you didn't create an account, please ignore this email.
        """
        return await self.send_email(email, subject, body)

    async def send_password_reset_email(self, email: str, token: str) -> bool:
        """Enviar email de reset de contraseña"""
        subject = "Password Reset - PipeWise CRM"
        body = f"""
        You requested a password reset. Click the link below to reset your password:
        
        {os.getenv("FRONTEND_URL", "http://localhost:3000")}/reset-password?token={token}
        
        This link will expire in 1 hour.
        If you didn't request this reset, please ignore this email.
        """
        return await self.send_email(email, subject, body)

    async def send_2fa_backup_codes(self, email: str, backup_codes: list) -> bool:
        """Enviar códigos de respaldo 2FA"""
        subject = "2FA Backup Codes - PipeWise CRM"
        codes_text = "\n".join([f"- {code}" for code in backup_codes])
        body = f"""
        Your 2FA backup codes:
        
        {codes_text}
        
        Keep these codes safe. You can use them to access your account if you lose your authenticator device.
        Each code can only be used once.
        """
        return await self.send_email(email, subject, body)

    async def health_check(self) -> Dict[str, Any]:
        """Health check del servicio de email"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "SMTP credentials not configured",
                }

            # Test básico de conexión
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                # No hacer login en health check para evitar rate limits

            return {
                "status": "healthy",
                "smtp_server": self.smtp_server,
                "smtp_port": self.smtp_port,
                "enabled": self.enabled,
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "enabled": self.enabled}


# Instancia global del servicio
email_service = EmailService()


# ===================== FUNCIONES DE CONVENIENCIA =====================


async def get_email_service() -> EmailService:
    """Obtener servicio de email para dependency injection"""
    return email_service


async def send_auth_email(email_type: str, user_email: str, **kwargs) -> bool:
    """Función de conveniencia para enviar emails de autenticación"""
    email_methods = {
        "welcome": email_service.send_welcome_email,
        "confirmation": email_service.send_email_confirmation,
        "password_reset": email_service.send_password_reset,
        "password_changed": email_service.send_password_changed_notification,
        "2fa_enabled": email_service.send_2fa_enabled_notification,
        "2fa_disabled": email_service.send_2fa_disabled_notification,
        "login_alert": email_service.send_login_alert,
        "suspicious_activity": email_service.send_suspicious_activity_alert,
        "account_locked": email_service.send_account_locked_notification,
    }

    method = email_methods.get(email_type)
    if method:
        return await method(user_email, **kwargs)
    else:
        logger.error(f"Unknown email type: {email_type}")
        return False
