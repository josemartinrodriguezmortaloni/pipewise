#!/usr/bin/env python3
"""
Script de debugging para el backend - versión con conexión a Supabase
"""

import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Importar cliente de Supabase
try:
    from app.supabase.supabase_client import SupabaseCRMClient

    SUPABASE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import Supabase client: {e}")
    SUPABASE_AVAILABLE = False

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI simple
app = FastAPI(
    title="PipeWise CRM Debug with Supabase",
    description="Debug version with real database connection",
    version="0.2.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Inicializar cliente de base de datos
db_client = None
if SUPABASE_AVAILABLE:
    try:
        db_client = SupabaseCRMClient()
        logger.info("✅ Connected to Supabase database")
    except Exception as e:
        logger.warning(f"⚠️ Could not connect to Supabase: {e}")
        db_client = None

# Datos de demo (fallback)
DEMO_LEADS = [
    {
        "id": "demo_lead_1",
        "name": "John Smith",
        "email": "john.smith@acme.com",
        "company": "Acme Corporation",
        "phone": "+1 (555) 123-4567",
        "status": "new",
        "qualified": False,
        "contacted": False,
        "meeting_scheduled": False,
        "source": "website",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
    },
    {
        "id": "demo_lead_2",
        "name": "Jane Doe",
        "email": "jane.doe@techsolutions.com",
        "company": "Tech Solutions Inc",
        "phone": "+1 (555) 987-6543",
        "status": "qualified",
        "qualified": True,
        "contacted": True,
        "meeting_scheduled": False,
        "source": "referral",
        "created_at": "2024-01-14T15:20:00Z",
        "updated_at": "2024-01-16T09:45:00Z",
    },
    {
        "id": "demo_lead_3",
        "name": "Bob Johnson",
        "email": "bob.johnson@startup.io",
        "company": "Startup.io",
        "phone": "+1 (555) 456-7890",
        "status": "contacted",
        "qualified": True,
        "contacted": True,
        "meeting_scheduled": True,
        "source": "linkedin",
        "created_at": "2024-01-13T08:15:00Z",
        "updated_at": "2024-01-17T14:30:00Z",
    },
]


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "PipeWise CRM Debug API with Supabase",
        "version": "0.2.0",
        "status": "running",
        "database": "Connected" if db_client else "Fallback mode",
        "endpoints": ["/api/leads", "/health"],
    }


@app.get("/health")
async def health_check():
    """Health check"""
    status = {
        "status": "healthy",
        "service": "debug_backend",
        "database": "connected" if db_client else "fallback",
    }

    if db_client:
        try:
            # Test database connection
            health_result = db_client.health_check()
            status["database_details"] = health_result
        except Exception as e:
            status["database"] = "error"
            status["database_error"] = str(e)

    return status


def format_lead_for_frontend(lead_obj):
    """Convertir objeto lead de Supabase al formato esperado por el frontend"""
    try:
        # Manejar tanto objetos como diccionarios
        if hasattr(lead_obj, "__dict__"):
            lead_data = {
                "id": str(lead_obj.id),
                "name": lead_obj.name,
                "email": lead_obj.email,
                "company": lead_obj.company,
                "phone": lead_obj.phone,
                "status": lead_obj.status,
                "qualified": lead_obj.qualified,
                "contacted": lead_obj.contacted,
                "meeting_scheduled": lead_obj.meeting_scheduled,
                "source": lead_obj.source,
                "created_at": lead_obj.created_at.isoformat()
                if hasattr(lead_obj.created_at, "isoformat")
                else str(lead_obj.created_at),
                "updated_at": getattr(lead_obj, "updated_at", None),
            }
        else:
            # Si es un diccionario
            lead_data = {
                "id": str(lead_obj.get("id", "")),
                "name": lead_obj.get("name", ""),
                "email": lead_obj.get("email", ""),
                "company": lead_obj.get("company", ""),
                "phone": lead_obj.get("phone"),
                "status": lead_obj.get("status", "new"),
                "qualified": lead_obj.get("qualified", False),
                "contacted": lead_obj.get("contacted", False),
                "meeting_scheduled": lead_obj.get("meeting_scheduled", False),
                "source": lead_obj.get("source"),
                "created_at": lead_obj.get("created_at"),
                "updated_at": lead_obj.get("updated_at"),
            }

        return lead_data
    except Exception as e:
        logger.error(f"Error formatting lead: {e}")
        return None


@app.get("/api/leads")
async def get_leads(
    page: int = 1,
    per_page: int = 50,
    status_filter: str = None,
    source_filter: str = None,
):
    """Listar leads con filtros y paginación"""
    try:
        logger.info(f"GET /api/leads - page: {page}, per_page: {per_page}")

        # Intentar obtener datos reales de Supabase
        if db_client:
            try:
                logger.info("📊 Fetching leads from Supabase...")

                # Construir filtros
                filters = {}
                if status_filter:
                    filters["status"] = status_filter
                if source_filter:
                    filters["source"] = source_filter

                # Calcular offset
                offset = (page - 1) * per_page

                # Obtener leads desde Supabase
                leads_data = db_client.list_leads(
                    limit=per_page, offset=offset, **filters
                )

                # Formatear leads para el frontend
                formatted_leads = []
                for lead in leads_data:
                    formatted_lead = format_lead_for_frontend(lead)
                    if formatted_lead:
                        formatted_leads.append(formatted_lead)

                # Obtener total count (simplificado)
                total = len(formatted_leads) + offset  # Aproximación

                if formatted_leads:
                    logger.info(
                        f"✅ Found {len(formatted_leads)} real leads from database"
                    )

                    response = {
                        "leads": formatted_leads,
                        "total": total,
                        "page": page,
                        "per_page": per_page,
                        "total_pages": (total + per_page - 1) // per_page,
                        "source": "supabase",
                    }

                    logger.info(f"Returning {len(formatted_leads)} leads from Supabase")
                    return response
                else:
                    logger.info("📝 No real leads found, using demo data")

            except Exception as e:
                logger.error(f"Error fetching from Supabase: {e}")
                logger.info("📝 Falling back to demo data")

        # Fallback a datos de demo
        filtered_leads = DEMO_LEADS

        if status_filter:
            filtered_leads = [
                lead for lead in filtered_leads if lead["status"] == status_filter
            ]

        if source_filter:
            filtered_leads = [
                lead for lead in filtered_leads if lead["source"] == source_filter
            ]

        # Paginación
        start = (page - 1) * per_page
        end = start + per_page
        paginated_leads = filtered_leads[start:end]

        total = len(filtered_leads)
        total_pages = (total + per_page - 1) // per_page

        response = {
            "leads": paginated_leads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "source": "demo",
        }

        logger.info(f"Returning {len(paginated_leads)} demo leads")
        return response

    except Exception as e:
        logger.error(f"Error in get_leads: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/leads")
async def create_lead(lead_data: dict):
    """Crear nuevo lead"""
    try:
        logger.info(f"POST /api/leads - data: {lead_data}")

        if db_client:
            try:
                # Intentar crear en Supabase
                from app.schemas.lead_schema import LeadCreate

                lead_create = LeadCreate(
                    name=lead_data.get("name", ""),
                    email=lead_data.get("email", ""),
                    company=lead_data.get("company", ""),
                    phone=lead_data.get("phone"),
                    message=lead_data.get("message"),
                    source=lead_data.get("source", "api"),
                    utm_params=lead_data.get("utm_params", {}),
                    metadata=lead_data.get("metadata", {}),
                )

                new_lead = db_client.create_lead(lead_create)
                formatted_lead = format_lead_for_frontend(new_lead)

                logger.info(f"✅ Created lead in Supabase: {new_lead.id}")

                return {
                    "status": "success",
                    "lead": formatted_lead,
                    "message": "Lead created successfully in database",
                }

            except Exception as e:
                logger.error(f"Error creating lead in Supabase: {e}")

        # Fallback a simulación
        new_lead = {
            "id": f"demo_lead_{len(DEMO_LEADS) + 1}",
            "name": lead_data.get("name", "Unknown"),
            "email": lead_data.get("email", ""),
            "company": lead_data.get("company", ""),
            "phone": lead_data.get("phone"),
            "status": "new",
            "qualified": False,
            "contacted": False,
            "meeting_scheduled": False,
            "source": lead_data.get("source", "api"),
            "created_at": "2024-01-20T10:00:00Z",
            "updated_at": "2024-01-20T10:00:00Z",
        }

        DEMO_LEADS.append(new_lead)
        logger.info(f"Created demo lead: {new_lead['id']}")

        return {
            "status": "success",
            "lead": new_lead,
            "message": "Lead created successfully (demo mode)",
        }

    except Exception as e:
        logger.error(f"Error in create_lead: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def main():
    """Iniciar servidor de debug"""
    logger.info("🚀 Starting PipeWise Debug Backend with Supabase on port 8001...")

    if db_client:
        logger.info("✅ Database connection available - will show real leads")
    else:
        logger.info("⚠️ No database connection - using demo data only")

    try:
        uvicorn.run(
            "debug_backend:app",
            host="0.0.0.0",
            port=8001,
            reload=True,
            access_log=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("🛑 Debug server stopped by user")
    except Exception as e:
        logger.error(f"❌ Debug server error: {e}")


if __name__ == "__main__":
    main()
