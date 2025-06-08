from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
import logging
from datetime import datetime

from app.agents.agent import Agents
from app.auth.middleware import get_current_user
from app.models.user import User
from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadCreate, LeadUpdate

logger = logging.getLogger(__name__)

app = FastAPI()

# Crear router para CRM
router = APIRouter(prefix="/api", tags=["CRM"])

# Inicializar cliente de CRM
crm_client = SupabaseCRMClient()


# ===================== GESTIÓN DE LEADS =====================


@router.get("/leads")
async def get_leads(
    page: int = Query(1, ge=1, description="Página actual"),
    per_page: int = Query(50, ge=1, le=100, description="Elementos por página"),
    status_filter: Optional[str] = Query(None, description="Filtrar por estado"),
    source_filter: Optional[str] = Query(None, description="Filtrar por fuente"),
    owner_filter: Optional[str] = Query(None, description="Filtrar por propietario"),
    search: Optional[str] = Query(None, description="Búsqueda de texto"),
    current_user: User = Depends(get_current_user),
):
    """Listar leads con filtros y paginación"""
    try:
        # Calcular offset para paginación
        offset = (page - 1) * per_page

        # Construir filtros
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if owner_filter:
            filters["owner_id"] = owner_filter

        # Agregar filtro por usuario
        filters["user_id"] = str(current_user.id)

        # Obtener leads desde la base de datos
        leads = crm_client.list_leads(limit=per_page, offset=offset, **filters)

        # Para la demo, también incluir algunos leads de ejemplo si la BD está vacía
        if not leads:
            leads = [
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
                    "owner_id": str(current_user.id),
                    "user_id": str(current_user.id),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
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
                    "owner_id": str(current_user.id),
                    "user_id": str(current_user.id),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
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
                    "owner_id": str(current_user.id),
                    "user_id": str(current_user.id),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                },
            ]

        # Simular total count (en producción sería una query separada)
        total = len(leads) if leads else 3

        return {
            "leads": leads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    except Exception as e:
        logger.error(f"Get leads error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leads",
        )


@router.post("/leads")
async def create_lead(lead_data: dict):
    """Crear nuevo lead - endpoint existente mantenido"""
    agents = Agents()
    # ✅ Workflow completamente automatizado
    result = await agents.run_workflow(lead_data)
    return result


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener lead específico"""
    try:
        lead = crm_client.get_lead(lead_id)

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
            )

        return lead

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get lead error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lead",
        )


@router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    updates: LeadUpdate,
    current_user: User = Depends(get_current_user),
):
    """Actualizar lead"""
    try:
        updated_lead = crm_client.update_lead(lead_id, updates)
        return updated_lead

    except Exception as e:
        logger.error(f"Update lead error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lead",
        )


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
):
    """Eliminar lead"""
    try:
        success = crm_client.delete_lead(lead_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
            )

        return {"message": "Lead deleted successfully", "id": lead_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete lead error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete lead",
        )


# ===================== HEALTH CHECK =====================


@router.get("/health")
async def api_health_check():
    """Health check del API CRM"""
    try:
        # Verificar conexión a base de datos
        db_health = crm_client.health_check()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_health,
            "version": "2.0.0",
        }

    except Exception as e:
        logger.error(f"API health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
