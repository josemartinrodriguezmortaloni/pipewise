import os
import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class EmailClient:
    """Cliente para enviar emails usando SMTP o SendGrid API"""

    def __init__(self, provider: str = "smtp", **kwargs):
        self.provider = provider.lower()

        if self.provider == "sendgrid":
            self.api_key = kwargs.get("api_key") or os.getenv("SENDGRID_API_KEY")
            self.base_url = "https://api.sendgrid.com/v3"
            self.enabled = bool(self.api_key)
        else:  # SMTP
            self.smtp_server = kwargs.get("smtp_server") or os.getenv(
                "SMTP_SERVER", "smtp.gmail.com"
            )
            self.smtp_port = kwargs.get("smtp_port") or int(
                os.getenv("SMTP_PORT", "587")
            )
            self.smtp_username = kwargs.get("smtp_username") or os.getenv(
                "SMTP_USERNAME"
            )
            self.smtp_password = kwargs.get("smtp_password") or os.getenv(
                "SMTP_PASSWORD"
            )
            self.enabled = bool(self.smtp_username and self.smtp_password)

        self.from_email = kwargs.get("from_email") or os.getenv(
            "FROM_EMAIL", "noreply@pipewise.com"
        )
        self.from_name = kwargs.get("from_name") or os.getenv(
            "FROM_NAME", "PipeWise CRM"
        )

        if self.enabled:
            logger.info(f"Email client initialized with {self.provider} provider")
        else:
            logger.warning(
                f"Email client initialized without credentials - using demo mode"
            )

    def _send_via_sendgrid(
        self, to_email: str, subject: str, content: str, content_type: str = "text/html"
    ) -> Dict:
        """Enviar email usando SendGrid API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "personalizations": [{"to": [{"email": to_email}], "subject": subject}],
            "from": {"email": self.from_email, "name": self.from_name},
            "content": [{"type": content_type, "value": content}],
        }

        try:
            response = requests.post(
                f"{self.base_url}/mail/send", headers=headers, json=data
            )
            response.raise_for_status()

            return {
                "success": True,
                "message_id": response.headers.get("X-Message-Id"),
                "provider": "sendgrid",
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending email via SendGrid: {e}")
            return {"success": False, "error": str(e), "provider": "sendgrid"}

    def _send_via_smtp(
        self, to_email: str, subject: str, content: str, content_type: str = "html"
    ) -> Dict:
        """Enviar email usando SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Crear contenido
            if content_type == "html":
                part = MIMEText(content, "html")
            else:
                part = MIMEText(content, "plain")

            msg.attach(part)

            # Conectar y enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return {
                "success": True,
                "message_id": f"smtp_{datetime.now().timestamp()}",
                "provider": "smtp",
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return {"success": False, "error": str(e), "provider": "smtp"}

    def send_email(
        self, to_email: str, subject: str, content: str, content_type: str = "html"
    ) -> Dict:
        """Enviar email usando el proveedor configurado"""
        if not self.enabled:
            logger.info(f"[DEMO] Email to {to_email}: {subject}")
            return {
                "success": True,
                "message_id": f"demo_email_{datetime.now().timestamp()}",
                "provider": f"{self.provider}_demo",
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "platform": "email",
            }

        if self.provider == "sendgrid":
            return self._send_via_sendgrid(
                to_email,
                subject,
                content,
                "text/html" if content_type == "html" else "text/plain",
            )
        else:
            return self._send_via_smtp(to_email, subject, content, content_type)

    def send_template_email(
        self, to_email: str, template_name: str, variables: Dict[str, str] = None
    ) -> Dict:
        """Enviar email usando un template predefinido"""
        templates = {
            "welcome": {
                "subject": "¡Bienvenido a PipeWise CRM!",
                "content": """
                <html>
                <body>
                    <h2>¡Hola {name}!</h2>
                    <p>Bienvenido a PipeWise CRM, la plataforma que revolucionará tu gestión de leads.</p>
                    <p>Estamos emocionados de tenerte a bordo y ayudarte a optimizar tu proceso de ventas.</p>
                    <br>
                    <p>Saludos,<br>El equipo de PipeWise</p>
                </body>
                </html>
                """,
            },
            "meeting_invitation": {
                "subject": "Reunión agendada - PipeWise CRM",
                "content": """
                <html>
                <body>
                    <h2>¡Hola {name}!</h2>
                    <p>Tu reunión ha sido agendada exitosamente.</p>
                    <p><strong>Enlace de la reunión:</strong> <a href="{meeting_url}">{meeting_url}</a></p>
                    <p>Te esperamos para mostrarte cómo PipeWise puede transformar tu negocio.</p>
                    <br>
                    <p>Saludos,<br>El equipo de PipeWise</p>
                </body>
                </html>
                """,
            },
            "follow_up": {
                "subject": "Seguimiento - PipeWise CRM",
                "content": """
                <html>
                <body>
                    <h2>¡Hola {name}!</h2>
                    <p>Queremos hacer seguimiento a tu interés en PipeWise CRM.</p>
                    <p>¿Te gustaría agendar una demostración personalizada?</p>
                    <p>Estamos aquí para responder cualquier pregunta que tengas.</p>
                    <br>
                    <p>Saludos,<br>El equipo de PipeWise</p>
                </body>
                </html>
                """,
            },
        }

        if template_name not in templates:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found",
                "available_templates": list(templates.keys()),
            }

        template = templates[template_name]
        variables = variables or {}

        # Reemplazar variables en el template
        subject = template["subject"].format(**variables)
        content = template["content"].format(**variables)

        return self.send_email(to_email, subject, content)

    def send_bulk_email(
        self, recipients: List[str], subject: str, content: str
    ) -> Dict:
        """Enviar email a múltiples destinatarios"""
        results = []
        successful = 0
        failed = 0

        for recipient in recipients:
            result = self.send_email(recipient, subject, content)
            results.append(
                {
                    "recipient": recipient,
                    "success": result["success"],
                    "message_id": result.get("message_id"),
                    "error": result.get("error"),
                }
            )

            if result["success"]:
                successful += 1
            else:
                failed += 1

        return {
            "total_sent": len(recipients),
            "successful": successful,
            "failed": failed,
            "results": results,
            "sent_at": datetime.now().isoformat(),
            "platform": "email",
        }

    def validate_email(self, email: str) -> Dict:
        """Validar formato de email"""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(pattern, email))

        return {
            "email": email,
            "valid": is_valid,
            "reason": "Valid email format" if is_valid else "Invalid email format",
        }

    def create_email_campaign(
        self,
        campaign_name: str,
        recipients: List[str],
        template_name: str,
        variables: Dict[str, str] = None,
    ) -> Dict:
        """Crear y enviar una campaña de emails"""
        campaign_id = f"campaign_{datetime.now().timestamp()}"

        if not self.enabled:
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "status": "demo_sent",
                "recipients": len(recipients),
                "template": template_name,
                "created_at": datetime.now().isoformat(),
                "platform": "email",
            }

        results = []
        for recipient in recipients:
            # Personalizar variables por destinatario si es necesario
            recipient_vars = variables.copy() if variables else {}
            if "name" not in recipient_vars:
                recipient_vars["name"] = recipient.split("@")[0].title()

            result = self.send_template_email(recipient, template_name, recipient_vars)
            results.append(
                {
                    "recipient": recipient,
                    "success": result["success"],
                    "message_id": result.get("message_id"),
                }
            )

        successful = sum(1 for r in results if r["success"])

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "status": "sent",
            "recipients": len(recipients),
            "successful": successful,
            "failed": len(recipients) - successful,
            "template": template_name,
            "results": results,
            "created_at": datetime.now().isoformat(),
            "platform": "email",
        }

    def health_check(self) -> Dict:
        """Verificar estado de la conexión"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": f"{self.provider} not configured",
                    "demo_mode": True,
                }

            if self.provider == "sendgrid":
                # Test SendGrid API
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(
                    f"{self.base_url}/user/profile", headers=headers
                )
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "provider": "sendgrid",
                    "from_email": self.from_email,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                # Test SMTP connection
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)

                return {
                    "status": "healthy",
                    "provider": "smtp",
                    "server": self.smtp_server,
                    "port": self.smtp_port,
                    "from_email": self.from_email,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


def get_email_client(provider: str = "smtp") -> EmailClient:
    """Obtener instancia del cliente de email"""
    return EmailClient(provider=provider)
