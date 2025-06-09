# Technical Improvements Document for PipeWise: Comprehensive B2B SaaS Modernization 2025

This document presents a complete roadmap for modernizing the PipeWise project, incorporating current B2B SaaS development best practices, from OpenAI AgentSDK implementation to scalable production infrastructure, including a modern frontend with React 19, Next.js 15, and Tailwind CSS 4. The proposed improvements will transform PipeWise into a robust, secure, and scalable platform that meets the most demanding industry standards.

## Modernization with OpenAI AgentSDK

### Migration from Traditional Function Calling

**The most significant change** is migrating from traditional function calling to the new OpenAI AgentSDK, which **drastically reduces code complexity** while providing advanced agent coordination capabilities.

```python
# Traditional implementation (before)
import openai
import json

client = openai.OpenAI()

def get_crm_data(client_id):
    return f"Client data for {client_id}"

tools = [{
    "type": "function",
    "function": {
        "name": "get_crm_data",
        "description": "Gets CRM data",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string"}
            }
        }
    }
}]

# Manual handling of complete loop
messages = [{"role": "user", "content": "Analyze client ABC123"}]
response = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=tools
)
# Manual processing of tool_calls...
```

```python
# Modern implementation with AgentSDK (after)
from agents import Agent, Runner, function_tool

@function_tool
def get_crm_data(client_id: str) -> str:
    """Gets complete client data from CRM.
    
    Args:
        client_id: Unique client ID
    """
    return f"Client data for {client_id}"

# Specialized agent with automatic validations
crm_agent = Agent(
    name="CRM Specialist",
    instructions="Analyze client data and generate insights",
    tools=[get_crm_data],
    model="gpt-4o"
)

# Automatic loop execution
result = Runner.run_sync(crm_agent, "Analyze client ABC123")
```

### Multi-Agent System for PipeWise

**Implementation of specialized agent architecture:**

```python
# agents/pipewise_agents.py
from agents import Agent, function_tool
from pydantic import BaseModel
from typing import List

class OpportunityAnalysis(BaseModel):
    client_id: str
    probability_score: float
    key_factors: List[str]
    recommendations: List[str]

@function_tool
def analyze_salesforce_opportunity(opportunity_id: str) -> str:
    """Analyzes a specific opportunity in Salesforce."""
    # Salesforce API integration
    return f"Opportunity analysis {opportunity_id}"

@function_tool
def generate_hubspot_proposal(contact_id: str) -> str:
    """Generates personalized proposal based on HubSpot data."""
    # HubSpot API integration
    return f"Proposal for contact {contact_id}"

# Agent specialized in opportunity analysis
opportunity_agent = Agent(
    name="Opportunity Analyst",
    instructions="""
    You are a B2B sales opportunity analysis specialist.
    Your role is to evaluate opportunities using CRM data and generate
    strategic recommendations for the sales team.
    """,
    tools=[analyze_salesforce_opportunity],
    output_type=OpportunityAnalysis,
    handoff_description="For detailed opportunity analysis"
)

# Agent specialized in proposal generation
proposal_agent = Agent(
    name="Proposal Generator",
    instructions="""
    Specialist in creating personalized commercial proposals.
    Use CRM data to generate relevant and compelling proposals.
    """,
    tools=[generate_hubspot_proposal],
    handoff_description="For commercial proposal creation"
)

# Main coordinator agent
coordinator_agent = Agent(
    name="PipeWise Coordinator",
    instructions="""
    You are the main coordinator of the PipeWise system.
    Route queries to specialized agents based on context:
    - Opportunity analysis → Opportunity Analyst
    - Proposal generation → Proposal Generator
    """,
    handoffs=[opportunity_agent, proposal_agent]
)
```

## Modern B2B SaaS Architecture

### Scalable Project Structure with FastAPI

**Implementation of hexagonal architecture with dependency injection:**

```python
# app/core/dependencies.py
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

async def get_tenant_context(
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db)
) -> Tenant:
    """Gets tenant context for multi-tenancy."""
    tenant = db.query(Tenant).filter(Tenant.id == x_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

class TenantService:
    def __init__(self, db: Session, tenant: Tenant):
        self.db = db
        self.tenant = tenant
    
    async def get_tenant_data(self, filters: dict = None):
        """Gets data filtered by tenant."""
        query = self.db.query(PipelineData).filter(
            PipelineData.tenant_id == self.tenant.id
        )
        if filters:
            for key, value in filters.items():
                query = query.filter(getattr(PipelineData, key) == value)
        return query.all()

def get_tenant_service(
    tenant: Tenant = Depends(get_tenant_context),
    db: Session = Depends(get_db)
) -> TenantService:
    return TenantService(db, tenant)
```

```python
# app/api/v1/endpoints/pipelines.py
from fastapi import APIRouter, Depends, BackgroundTasks
from app.core.dependencies import get_tenant_service
from app.schemas.pipeline import PipelineCreate, PipelineResponse
from app.tasks.analysis import analyze_pipeline_async

router = APIRouter()

@router.post("/pipelines/", response_model=PipelineResponse)
async def create_pipeline(
    pipeline_data: PipelineCreate,
    background_tasks: BackgroundTasks,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """Creates new pipeline with asynchronous analysis."""
    pipeline = await tenant_service.create_pipeline(pipeline_data)
    
    # Asynchronous processing with Celery
    background_tasks.add_task(
        analyze_pipeline_async.delay, 
        pipeline.id, 
        tenant_service.tenant.id
    )
    
    return pipeline
```

### Frontend Architecture with Next.js 14

**Implementation with App Router and Server Components:**

```typescript
// app/dashboard/layout.tsx
import { Providers } from './providers'
import { TenantProvider } from '@/components/providers/tenant-provider'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Providers>
      <TenantProvider>
        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm">
            {/* Navigation */}
          </nav>
          <main className="container mx-auto py-6">
            {children}
          </main>
        </div>
      </TenantProvider>
    </Providers>
  )
}
```

```typescript
// app/dashboard/pipelines/page.tsx - Server Component
import { PipelinesList } from './pipelines-list'
import { apiClient } from '@/lib/api-client'

async function getPipelines() {
  return await apiClient.get('/pipelines')
}

export default async function PipelinesPage() {
  const pipelines = await getPipelines()
  
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Pipeline Management</h1>
      <PipelinesList initialData={pipelines} />
    </div>
  )
}
```

```typescript
// app/dashboard/pipelines/pipelines-list.tsx - Client Component
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

interface PipelinesListProps {
  initialData: Pipeline[]
}

export function PipelinesList({ initialData }: PipelinesListProps) {
  const queryClient = useQueryClient()
  
  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => apiClient.get('/pipelines'),
    initialData,
  })

  const createPipelineMutation = useMutation({
    mutationFn: (data: CreatePipelineData) => 
      apiClient.post('/pipelines', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
    },
  })

  return (
    <div className="space-y-4">
      {pipelines.map(pipeline => (
        <PipelineCard key={pipeline.id} pipeline={pipeline} />
      ))}
    </div>
  )
}
```

## Comprehensive Testing System

### Comprehensive Testing for FastAPI

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
async def async_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def authenticated_client(async_client, db_session):
    # Create test user with tenant
    test_tenant = Tenant(name="Test Tenant", domain="test.com")
    test_user = User(email="test@test.com", tenant=test_tenant)
    db_session.add_all([test_tenant, test_user])
    db_session.commit()
    
    # Configure authentication
    token = create_access_token({"sub": test_user.email, "tenant_id": test_tenant.id})
    async_client.headers["Authorization"] = f"Bearer {token}"
    async_client.headers["X-Tenant-ID"] = test_tenant.id
    
    return async_client
```

```python
# tests/test_pipelines.py
import pytest
from unittest.mock import patch, AsyncMock

class TestPipelineEndpoints:
    
    @pytest.mark.asyncio
    async def test_create_pipeline_success(self, authenticated_client):
        pipeline_data = {
            "name": "Test Pipeline",
            "description": "Test pipeline",
            "config": {"stage_count": 5}
        }
        
        response = await authenticated_client.post("/api/v1/pipelines/", json=pipeline_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == pipeline_data["name"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, authenticated_client, db_session):
        # Create pipeline for current tenant
        current_pipeline = await authenticated_client.post(
            "/api/v1/pipelines/", 
            json={"name": "Current Tenant Pipeline"}
        )
        
        # Create pipeline for another tenant
        other_tenant = Tenant(name="Other Tenant", domain="other.com")
        db_session.add(other_tenant)
        db_session.commit()
        
        other_pipeline = Pipeline(name="Other Tenant Pipeline", tenant_id=other_tenant.id)
        db_session.add(other_pipeline)
        db_session.commit()
        
        # Verify only current tenant pipelines are visible
        response = await authenticated_client.get("/api/v1/pipelines/")
        pipelines = response.json()
        
        assert len(pipelines) == 1
        assert pipelines[0]["name"] == "Current Tenant Pipeline"

    @patch('app.tasks.analysis.analyze_pipeline_async.delay')
    @pytest.mark.asyncio
    async def test_async_processing_triggered(self, mock_task, authenticated_client):
        pipeline_data = {"name": "Async Test Pipeline"}
        
        response = await authenticated_client.post("/api/v1/pipelines/", json=pipeline_data)
        pipeline_id = response.json()["id"]
        
        # Verify async task was executed
        mock_task.assert_called_once_with(pipeline_id, authenticated_client.headers["X-Tenant-ID"])
```

### E2E Testing with Playwright

```python
# tests/e2e/test_pipeline_workflow.py
import pytest
from playwright.async_api import Page, expect

class TestPipelineWorkflow:
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_creation_flow(self, page: Page):
        # Login
        await page.goto("http://localhost:3000/login")
        await page.fill('[data-testid="email-input"]', "admin@test.com")
        await page.fill('[data-testid="password-input"]', "password123")
        await page.click('[data-testid="login-button"]')
        
        # Navigate to pipelines
        await page.click('[data-testid="nav-pipelines"]')
        await expect(page).to_have_url("http://localhost:3000/dashboard/pipelines")
        
        # Create new pipeline
        await page.click('[data-testid="create-pipeline-button"]')
        await page.fill('[data-testid="pipeline-name"]', "E2E Test Pipeline")
        await page.fill('[data-testid="pipeline-description"]', "Pipeline created in E2E test")
        
        # Configure stages
        await page.click('[data-testid="add-stage-button"]')
        await page.fill('[data-testid="stage-name-0"]', "Prospect")
        await page.fill('[data-testid="stage-probability-0"]', "25")
        
        # Save pipeline
        await page.click('[data-testid="save-pipeline-button"]')
        
        # Verify successful creation
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("Pipeline created successfully")
        await expect(page.locator('[data-testid="pipeline-list"]')).to_contain_text("E2E Test Pipeline")
```

## CRM Integration and Multi-Tenancy Security

### Secure Salesforce Integration

```python
# app/services/crm/salesforce.py
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from app.core.config import settings
from app.models.tenant import Tenant

class SalesforceIntegration:
    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.base_url = f"https://{tenant.salesforce_instance}.my.salesforce.com"
        self.client_id = tenant.salesforce_client_id
        self.client_secret = tenant.salesforce_client_secret
        
    async def get_access_token(self) -> str:
        """Gets access token using Client Credentials flow."""
        async with aiohttp.ClientSession() as session:
            auth_url = f"{self.base_url}/services/oauth2/token"
            
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            async with session.post(auth_url, data=payload) as response:
                if response.status == 200:
                    token_data = await response.json()
                    return token_data['access_token']
                else:
                    raise Exception(f"Error getting token: {response.status}")
    
    async def get_opportunities(self, filters: Dict[str, Any] = None) -> List[Dict]:
        """Gets opportunities with optional filters."""
        access_token = await self.get_access_token()
        
        # Dynamic SOQL query construction
        soql = "SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity"
        if filters:
            conditions = []
            for field, value in filters.items():
                if isinstance(value, str):
                    conditions.append(f"{field} = '{value}'")
                else:
                    conditions.append(f"{field} = {value}")
            
            if conditions:
                soql += " WHERE " + " AND ".join(conditions)
        
        soql += " ORDER BY CloseDate DESC LIMIT 100"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            query_url = f"{self.base_url}/services/data/v54.0/query"
            params = {'q': soql}
            
            async with session.get(query_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['records']
                else:
                    raise Exception(f"Error querying Salesforce: {response.status}")
```

### Multi-Tenancy Security System

```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User

security = HTTPBearer()

class TenantSecurityContext:
    def __init__(self, user: User, tenant: Tenant, permissions: List[str]):
        self.user = user
        self.tenant = tenant
        self.permissions = permissions
    
    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or 'admin' in self.permissions

async def get_current_security_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> TenantSecurityContext:
    """Gets complete security context with tenant and permissions."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        user_email: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        
        if user_email is None or tenant_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user and tenant
    user = db.query(User).filter(User.email == user_email).first()
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if user is None or tenant is None:
        raise credentials_exception
    
    # Verify user belongs to tenant
    if user.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to tenant"
        )
    
    # Get user permissions
    permissions = [role.name for role in user.roles]
    
    return TenantSecurityContext(user, tenant, permissions)

def require_permission(permission: str):
    """Decorator to require specific permissions."""
    def dependency(context: TenantSecurityContext = Depends(get_current_security_context)):
        if not context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return context
    return dependency
```

## Production Infrastructure

### Celery Configuration for Asynchronous Processing

```python
# app/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "pipewise",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Production-optimized configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker configuration
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Queue configuration
    task_routes={
        'app.tasks.crm_sync.*': {'queue': 'crm_sync'},
        'app.tasks.analysis.*': {'queue': 'analysis'},
        'app.tasks.notifications.*': {'queue': 'notifications'},
    },
    
    # Result configuration
    result_expires=3600,
    task_compression='gzip',
    result_compression='gzip',
    
    # Retry configuration
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Beat configuration for scheduled tasks
celery_app.conf.beat_schedule = {
    'sync-crm-data': {
        'task': 'app.tasks.crm_sync.sync_all_tenants',
        'schedule': 300.0,  # every 5 minutes
    },
    'cleanup-old-results': {
        'task': 'app.tasks.maintenance.cleanup_old_task_results',
        'schedule': 3600.0,  # every hour
    },
}
```

```python
# app/tasks/analysis.py
from app.celery_app import celery_app
from app.services.agents.coordinator import coordinator_agent
from agents import Runner
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def analyze_pipeline_async(self, pipeline_id: str, tenant_id: str):
    """Asynchronous pipeline analysis using AgentSDK."""
    try:
        # Get pipeline data
        pipeline_data = get_pipeline_data(pipeline_id, tenant_id)
        
        # Analysis with AgentSDK
        prompt = f"""
        Analyze the following sales pipeline:
        - ID: {pipeline_id}
        - Data: {pipeline_data}
        
        Provide:
        1. Performance analysis
        2. Bottleneck identification
        3. Optimization recommendations
        4. Conversion predictions
        """
        
        result = Runner.run_sync(coordinator_agent, prompt)
        
        # Save results
        save_analysis_results(pipeline_id, result.final_output)
        
        # Notify user
        send_analysis_notification.delay(pipeline_id, tenant_id)
        
        return {
            "status": "completed",
            "pipeline_id": pipeline_id,
            "analysis": result.final_output
        }
        
    except Exception as exc:
        logger.error(f"Error analyzing pipeline {pipeline_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        raise exc
```

### Containerization and Deployment

```dockerfile
# Dockerfile.backend
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed dependencies
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Configure PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.pipewise.com`)"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    environment:
      - NEXT_PUBLIC_API_URL=https://api.pipewise.com
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`app.pipewise.com`)"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"

  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    deploy:
      replicas: 2

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  traefik:
    image: traefik:v2.9
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
      - ./acme.json:/acme.json
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

## Modern CI/CD Pipeline

### Complete GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yml
name: PipeWise CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test-backend:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8 and black
      run: |
        flake8 app tests
        black --check app tests
        isort --check-only app tests
    
    - name: Type check with mypy
      run: mypy app
    
    - name: Test with pytest
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        CELERY_BROKER_URL: redis://localhost:6379/0
        CELERY_RESULT_BACKEND: redis://localhost:6379/0
        JWT_SECRET_KEY: test_secret_key
      run: |
        pytest --cov=app --cov-report=xml --cov-report=term -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  test-frontend:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Lint and type check
      run: |
        cd frontend
        npm run lint
        npm run type-check
    
    - name: Run tests
      run: |
        cd frontend
        npm run test -- --coverage --watchAll=false
    
    - name: Build application
      run: |
        cd frontend
        npm run build

  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-deploy:
    needs: [test-backend, test-frontend, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
    
    - name: Build and push Docker images
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.backend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
    
    - name: Deploy to production
      run: |
        echo "Deploying to production..."
        # Deployment logic here
```

## Monitoring and Observability

### Metrics and Alerts Configuration

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps

# Application metrics
REQUEST_COUNT = Counter('pipewise_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status', 'tenant_id'])
REQUEST_DURATION = Histogram('pipewise_http_request_duration_seconds', 'HTTP request duration')
ACTIVE_USERS = Gauge('pipewise_active_users', 'Active users by tenant', ['tenant_id'])
PIPELINE_OPERATIONS = Counter('pipewise_pipeline_operations_total', 'Pipeline operations', ['operation', 'tenant_id'])
CELERY_TASK_DURATION = Histogram('pipewise_celery_task_duration_seconds', 'Celery task duration', ['task_name'])
CRM_API_CALLS = Counter('pipewise_crm_api_calls_total', 'CRM API calls', ['crm_type', 'status'])

# Application info
APP_INFO = Info('pipewise_app_info', 'Application information')
APP_INFO.info({
    'version': '2.0.0',
    'environment': 'production',
    'build_date': '2025-01-15'
})

def track_request_metrics(func):
    """Decorator to track request metrics."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=kwargs.get('endpoint', 'unknown'),
                status='success'
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=kwargs.get('endpoint', 'unknown'),
                status='error'
            ).inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    
    return wrapper

def track_celery_task(task_name: str):
    """Decorator to track Celery task metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                CELERY_TASK_DURATION.labels(task_name=task_name).observe(time.time() - start_time)
        
        return wrapper
    return decorator
```

```yaml
# monitoring/grafana-dashboards/pipewise-overview.json
{
  "dashboard": {
    "title": "PipeWise - Overview",
    "tags": ["pipewise", "saas"],
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(pipewise_http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time (95th percentile)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(pipewise_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Active Users by Tenant",
        "type": "graph",
        "targets": [
          {
            "expr": "pipewise_active_users",
            "legendFormat": "{{tenant_id}}"
          }
        ]
      },
      {
        "title": "Celery Task Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(pipewise_celery_task_duration_seconds_count[5m])",
            "legendFormat": "{{task_name}}"
          }
        ]
      }
    ]
  }
}
```

## Modern Frontend with React 19

### Component Architecture with Server Components

**Implementation of React Server Components by default:**

```typescript
// app/components/leads/LeadsDashboard.tsx
// Server Component - Runs on the server
export default async function LeadsDashboard() {
  // Direct fetch without client state
  const leads = await fetchLeadsFromDB();
  const analytics = await getLeadAnalytics();
  
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <LeadsTable leads={leads} />
      </div>
      <div>
        <LeadAnalytics data={analytics} />
        <QuickActions /> {/* Client Component for interactivity */}
      </div>
    </div>
  );
}

// app/components/leads/QuickActions.tsx
'use client'; // Only when we need hooks/events

import { useState, useTransition } from 'react';
import { processLeadAction } from '@/app/actions/leads';

export function QuickActions() {
  const [isPending, startTransition] = useTransition();
  
  const handleQuickProcess = () => {
    startTransition(async () => {
      await processLeadAction();
    });
  };
  
  return (
    <button 
      onClick={handleQuickProcess}
      disabled={isPending}
      className="btn-primary"
    >
      {isPending ? 'Processing...' : 'Quick Process'}
    </button>
  );
}
```

### Actions System for Forms

**Simplified form handling with Server Actions:**

```typescript
// app/actions/leads.ts
'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const LeadSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
  company: z.string().min(1),
  score: z.number().min(0).max(100),
});

export async function createLead(prevState: any, formData: FormData) {
  try {
    const validatedData = LeadSchema.parse({
      name: formData.get('name'),
      email: formData.get('email'),
      company: formData.get('company'),
      score: parseInt(formData.get('score') as string),
    });
    
    // Save to database
    const lead = await db.lead.create({
      data: {
        ...validatedData,
        tenantId: getTenantId(),
      },
    });
    
    // Trigger AgentSDK for processing
    await agentCoordinator.processNewLead(lead.id);
    
    revalidatePath('/leads');
    
    return { 
      success: true, 
      message: 'Lead created successfully',
      leadId: lead.id 
    };
  } catch (error) {
    return { 
      success: false, 
      message: error.message 
    };
  }
}

// app/components/leads/CreateLeadForm.tsx
'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { createLead } from '@/app/actions/leads';

function SubmitButton() {
  const { pending } = useFormStatus();
  
  return (
    <button
      type="submit"
      disabled={pending}
      className="btn-primary"
    >
      {pending ? 'Creating...' : 'Create Lead'}
    </button>
  );
}

export function CreateLeadForm() {
  const [state, formAction] = useFormState(createLead, null);
  
  return (
    <form action={formAction} className="space-y-4">
      {state?.message && (
        <div className={`alert ${state.success ? 'alert-success' : 'alert-error'}`}>
          {state.message}
        </div>
      )}
      
      <input
        name="name"
        placeholder="Lead Name"
        required
        className="input"
      />
      
      <input
        name="email"
        type="email"
        placeholder="Email"
        required
        className="input"
      />
      
      <input
        name="company"
        placeholder="Company"
        required
        className="input"
      />
      
      <input
        name="score"
        type="number"
        min="0"
        max="100"
        placeholder="Score (0-100)"
        className="input"
      />
      
      <SubmitButton />
    </form>
  );
}
```

### Optimization with React Compiler

**Elimination of manual memoization hooks:**

```typescript
// ❌ BEFORE - React 18 with manual optimization
import { useMemo, useCallback, memo } from 'react';

const LeadCard = memo(({ lead, onSelect }) => {
  const formattedScore = useMemo(() => {
    return `${lead.score}% - ${getScoreLabel(lead.score)}`;
  }, [lead.score]);
  
  const handleClick = useCallback(() => {
    onSelect(lead.id);
  }, [lead.id, onSelect]);
  
  return (
    <div onClick={handleClick} className="lead-card">
      <h3>{lead.name}</h3>
      <p>{formattedScore}</p>
    </div>
  );
});

// ✅ NOW - React 19 with automatic compiler
// No need for memo, useMemo or useCallback
function LeadCard({ lead, onSelect }) {
  const formattedScore = `${lead.score}% - ${getScoreLabel(lead.score)}`;
  
  const handleClick = () => {
    onSelect(lead.id);
  };
  
  return (
    <div onClick={handleClick} className="lead-card">
      <h3>{lead.name}</h3>
      <p>{formattedScore}</p>
    </div>
  );
}
```

## Next.js 15 Architecture

### Scalable Project Structure

```
pipewise-frontend/
├── src/
│   ├── app/                          # App Router
│   │   ├── (auth)/                  # Authentication group
│   │   │   ├── login/
│   │   │   │   ├── page.tsx
│   │   │   │   └── layout.tsx
│   │   │   └── register/
│   │   ├── (dashboard)/             # Main group
│   │   │   ├── layout.tsx          # Layout with sidebar
│   │   │   ├── leads/
│   │   │   │   ├── page.tsx        # Leads list
│   │   │   │   ├── [id]/           # Lead detail
│   │   │   │   │   └── page.tsx
│   │   │   │   └── new/
│   │   │   │       └── page.tsx
│   │   │   ├── analytics/
│   │   │   └── settings/
│   │   ├── api/                     # Route handlers
│   │   │   ├── leads/
│   │   │   └── webhooks/
│   │   └── actions/                 # Server actions
│   │       ├── leads.ts
│   │       └── auth.ts
│   ├── components/
│   │   ├── ui/                      # Base components
│   │   │   ├── button/
│   │   │   ├── card/
│   │   │   └── form/
│   │   └── features/                # By domain
│   │       ├── leads/
│   │       ├── analytics/
│   │       └── auth/
│   ├── lib/
│   │   ├── api/                     # API client
│   │   ├── auth/                    # Auth utilities
│   │   └── ai/                      # AgentSDK integration
│   └── types/
│       └── index.ts
├── public/
├── middleware.ts                     # Next.js middleware
└── next.config.js
```

### App Router Implementation with Layouts

```typescript
// app/(dashboard)/layout.tsx
import { Sidebar } from '@/components/features/navigation/Sidebar';
import { TopBar } from '@/components/features/navigation/TopBar';
import { getTenant } from '@/lib/auth/tenant';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const tenant = await getTenant();
  
  return (
    <div className="min-h-screen bg-background">
      <TopBar tenant={tenant} />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

// app/(dashboard)/leads/page.tsx
import { Suspense } from 'react';
import { LeadsTable } from '@/components/features/leads/LeadsTable';
import { LeadsFilters } from '@/components/features/leads/LeadsFilters';
import { LeadsSkeleton } from '@/components/features/leads/LeadsSkeleton';

export const metadata = {
  title: 'Leads | PipeWise',
  description: 'Manage your sales leads',
};

export default function LeadsPage({
  searchParams,
}: {
  searchParams: { status?: string; search?: string };
}) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Leads</h1>
        <Link href="/leads/new" className="btn-primary">
          New Lead
        </Link>
      </div>
      
      <LeadsFilters />
      
      <Suspense fallback={<LeadsSkeleton />}>
        <LeadsTable filters={searchParams} />
      </Suspense>
    </div>
  );
}
```

### Middleware for Multi-Tenancy

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { verifyAuth } from '@/lib/auth';

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  // Public routes
  if (pathname.startsWith('/login') || pathname.startsWith('/register')) {
    return NextResponse.next();
  }
  
  // Verify authentication
  const token = request.cookies.get('auth-token');
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  try {
    const payload = await verifyAuth(token.value);
    
    // Extract tenant from token or domain
    const hostname = request.headers.get('host') || '';
    const subdomain = hostname.split('.')[0];
    
    // Verify tenant matches
    if (payload.tenant !== subdomain && process.env.NODE_ENV === 'production') {
      return NextResponse.redirect(new URL('/unauthorized', request.url));
    }
    
    // Add tenant headers
    const response = NextResponse.next();
    response.headers.set('x-tenant-id', payload.tenant);
    response.headers.set('x-user-id', payload.userId);
    
    return response;
  } catch (error) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
```

## Design System with Tailwind CSS 4

### Configuration with CSS Variables

```css
/* app/globals.css */
@import "tailwindcss";

/* Custom theme with CSS variables */
@theme {
  /* Brand colors with wide gamut */
  --color-primary-50: oklch(0.95 0.02 250);
  --color-primary-100: oklch(0.90 0.04 250);
  --color-primary-200: oklch(0.82 0.08 250);
  --color-primary-300: oklch(0.70 0.15 250);
  --color-primary-400: oklch(0.58 0.22 250);
  --color-primary-500: oklch(0.50 0.28 250);
  --color-primary-600: oklch(0.42 0.30 250);
  --color-primary-700: oklch(0.35 0.28 250);
  --color-primary-800: oklch(0.28 0.25 250);
  --color-primary-900: oklch(0.20 0.20 250);
  
  /* Adaptive colors for light/dark mode */
  --color-background: light-dark(
    oklch(0.98 0 0),      /* light */
    oklch(0.15 0 0)       /* dark */
  );
  
  --color-foreground: light-dark(
    oklch(0.10 0 0),      /* light */
    oklch(0.95 0 0)       /* dark */
  );
  
  --color-border: light-dark(
    oklch(0.90 0 0),      /* light */
    oklch(0.25 0 0)       /* dark */
  );
  
  /* Custom spacing */
  --spacing-18: 4.5rem;
  --spacing-22: 5.5rem;
  
  /* Typography */
  --font-sans: "Inter var", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

/* Custom utilities with @utility */
@utility btn-primary {
  background-color: theme(colors.primary.600);
  color: white;
  padding: theme(spacing.2) theme(spacing.4);
  border-radius: theme(borderRadius.md);
  font-weight: 500;
  transition: all 150ms;
}

@utility btn-primary:hover {
  background-color: theme(colors.primary.700);
  transform: translateY(-1px);
}

@utility card {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: theme(borderRadius.lg);
  padding: theme(spacing.6);
  box-shadow: theme(boxShadow.sm);
}

@utility input {
  width: 100%;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: theme(borderRadius.md);
  padding: theme(spacing.2) theme(spacing.3);
  transition: all 150ms;
}

@utility input:focus {
  outline: 2px solid theme(colors.primary.500);
  outline-offset: 2px;
}
```

### Components with Tailwind CSS 4

```typescript
// components/ui/Card.tsx
interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export function Card({ children, className = '', hover = false }: CardProps) {
  return (
    <div 
      className={`
        card
        ${hover ? 'transition-transform hover:scale-[1.02]' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

// components/features/leads/LeadCard.tsx
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export function LeadCard({ lead }: { lead: Lead }) {
  return (
    <Card hover className="space-y-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold">{lead.name}</h3>
          <p className="text-sm text-foreground/60">{lead.company}</p>
        </div>
        <Badge variant={getScoreVariant(lead.score)}>
          {lead.score}%
        </Badge>
      </div>
      
      <div className="flex gap-2 text-sm">
        <span className="text-foreground/60">Status:</span>
        <span className="font-medium">{lead.status}</span>
      </div>
      
      <div className="flex gap-2">
        <button className="btn-primary text-sm">
          Process
        </button>
        <button className="btn-secondary text-sm">
          Details
        </button>
      </div>
    </Card>
  );
}
```

## Frontend-Backend Integration

### API Client with TypeScript

```typescript
// lib/api/client.ts
import { z } from 'zod';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private tenantId: string | null = null;
  
  setTenant(tenantId: string) {
    this.tenantId = tenantId;
  }
  
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      'X-Tenant-ID': this.tenantId || '',
      ...options.headers,
    };
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new APIError(response.status, await response.text());
    }
    
    return response.json();
  }
  
  // Leads API
  async getLeads(filters?: LeadFilters) {
    const params = new URLSearchParams(filters as any);
    return this.request<Lead[]>(`/api/v1/leads?${params}`);
  }
  
  async createLead(data: CreateLeadDto) {
    return this.request<Lead>('/api/v1/leads', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async processLead(leadId: string) {
    return this.request<ProcessResult>(`/api/v1/leads/${leadId}/process`, {
      method: 'POST',
    });
  }
}

export const apiClient = new APIClient();
```

### Custom Hooks for Data Fetching

```typescript
// hooks/useLeads.ts
import { use } from 'react';
import { apiClient } from '@/lib/api/client';

// For Server Components
export function useLeadsPromise(filters?: LeadFilters) {
  return apiClient.getLeads(filters);
}

// For Client Components with SWR
import useSWR from 'swr';

export function useLeads(filters?: LeadFilters) {
  const key = filters 
    ? `/api/leads?${new URLSearchParams(filters as any)}`
    : '/api/leads';
    
  return useSWR(key, () => apiClient.getLeads(filters), {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });
}

// Hook for optimistic actions
export function useOptimisticLead(lead: Lead) {
  const [optimisticLead, setOptimisticLead] = useState(lead);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const processLead = async () => {
    setIsProcessing(true);
    
    // Optimistic update
    setOptimisticLead(prev => ({
      ...prev,
      status: 'processing',
    }));
    
    try {
      const result = await apiClient.processLead(lead.id);
      setOptimisticLead(result.lead);
    } catch (error) {
      // Revert on error
      setOptimisticLead(lead);
      throw error;
    } finally {
      setIsProcessing(false);
    }
  };
  
  return { lead: optimisticLead, processLead, isProcessing };
}
```

## Frontend Testing

### Testing with React Testing Library

```typescript
// __tests__/components/LeadCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { LeadCard } from '@/components/features/leads/LeadCard';

describe('LeadCard', () => {
  const mockLead = {
    id: '1',
    name: 'John Doe',
    company: 'Acme Corp',
    score: 85,
    status: 'qualified',
  };
  
  it('renders lead information correctly', () => {
    render(<LeadCard lead={mockLead} />);
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });
  
  it('handles process action', async () => {
    const onProcess = jest.fn();
    render(<LeadCard lead={mockLead} onProcess={onProcess} />);
    
    const processButton = screen.getByText('Process');
    fireEvent.click(processButton);
    
    expect(onProcess).toHaveBeenCalledWith(mockLead.id);
  });
});
```

### E2E Testing with Playwright

```typescript
// e2e/leads-workflow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Leads Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@pipewise.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/leads');
  });
  
  test('create and process lead', async ({ page }) => {
    // Create new lead
    await page.click('text=New Lead');
    
    await page.fill('[name="name"]', 'Test Lead');
    await page.fill('[name="email"]', 'lead@example.com');
    await page.fill('[name="company"]', 'Test Company');
    await page.fill('[name="score"]', '75');
    
    await page.click('button:has-text("Create Lead")');
    
    // Verify creation
    await expect(page.locator('.alert-success')).toContainText('Lead created successfully');
    
    // Process lead
    const leadCard = page.locator('text=Test Lead').locator('..');
    await leadCard.locator('button:has-text("Process")').click();
    
    // Verify processing
    await expect(leadCard).toContainText('processing');
    
    // Wait for result
    await expect(leadCard).toContainText('qualified', { timeout: 10000 });
  });
});
```

## Implementation Roadmap

### Phase 1: Backend Fundamentals (Weeks 1-4)
- **AgentSDK Migration**: Replace traditional function calling
- **Multi-tenancy architecture**: Implement tenant isolation
- **CI/CD configuration**: Basic pipeline setup
- **Testing framework**: Configure pytest and basic testing

### Phase 2: Frontend Fundamentals (Weeks 5-8)
- **Next.js 15 Setup**: Configure project with App Router
- **React 19 Components**: Migrate to Server Components
- **Tailwind CSS 4**: Implement design system
- **API Integration**: Connect frontend with backend

### Phase 3: Integrations (Weeks 9-12)
- **Salesforce Integration**: Implement bidirectional sync
- **HubSpot Integration**: Configure data flows
- **Queue System**: Implement Celery for async processing
- **Advanced Security**: JWT, RBAC, and validations

### Phase 4: Infrastructure (Weeks 13-16)
- **Containerization**: Docker multi-stage builds
- **Orchestration**: Kubernetes or Docker Compose for production
- **Monitoring**: Prometheus, Grafana, and alerts
- **Automated Deployment**: Complete CD pipelines

### Phase 5: Optimization (Weeks 17-20)
- **Performance tuning**: Query optimization and caching
- **Scalability**: Auto-scaling and load balancing
- **Advanced Observability**: Distributed tracing
- **E2E Testing**: Playwright and complete testing

This comprehensive modernization will transform PipeWise into a robust, scalable, and maintainable B2B SaaS platform that leverages the best industry practices and the most advanced technologies available in 2025. The sequential implementation ensures a controlled migration without service interruptions.