# Rules.md - Complete Implementation Rules Guide for PipeWise

This document establishes the fundamental rules for correctly implementing the improvements proposed in the Improvements.md document, for both backend (FastAPI, Python) and frontend (React 19, Next.js 15, Tailwind CSS 4), optimizing development times, increasing precision and efficiency of the artificial intelligence model.

## Table of Contents
1. [Rules for OpenAI AgentSDK Migration](#1-rules-for-openai-agentsdk-migration)
2. [FastAPI Architecture Rules](#2-fastapi-architecture-rules)
3. [Multi-Tenancy B2B SaaS Rules](#3-multi-tenancy-b2b-saas-rules)
4. [Testing and Quality Rules](#4-testing-and-quality-rules)
5. [CI/CD Rules](#5-cicd-rules)
6. [Containerization Rules](#6-containerization-rules)
7. [Asynchronous Processing Rules](#7-asynchronous-processing-rules)
8. [Monitoring and Observability Rules](#8-monitoring-and-observability-rules)
9. [React 19 Rules](#9-react-19-rules)
10. [Tailwind CSS 4 Rules](#10-tailwind-css-4-rules)
11. [Next.js 15 Rules](#11-nextjs-15-rules)

---

## 1. Rules for OpenAI AgentSDK Migration

### Rule 1.1: Always Use @function_tool Decorators
**Source**: [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- **Extracted information**: "Function tools: Turn any Python function into a tool, with automatic schema generation and Pydantic-powered validation" (index 1-1)
- **Location**: Main features section
- **How to use**: Every function that interacts with external services must use the `@function_tool` decorator to leverage automatic validation and schema generation.

```python
# ✅ CORRECT
@function_tool
def search_crm_client(client_id: str) -> str:
    """Searches for client information in the CRM."""
    return f"Client data for {client_id}"

# ❌ INCORRECT - Don't use traditional function calling
def search_crm_client_old(client_id):
    # Manual implementation without validation
    pass
```

### Rule 1.2: Implement Typed Context for Agents
**Source**: [Agents Documentation](https://openai.github.io/openai-agents-python/agents/)
- **Extracted information**: "Agents are generic on their context type... You can provide any Python object as the context" (index 3-1)
- **Location**: Context Configuration section
- **How to use**: Always define a typed context for dependency injection and state management.

```python
from dataclasses import dataclass
from agents import Agent

@dataclass
class TenantContext:
    tenant_id: str
    user_id: str
    is_premium: bool
    api_limits: dict

# Create agent with typed context
agent = Agent[TenantContext](
    name="Lead Processor",
    instructions="Process leads considering tenant limits"
)
```

### Rule 1.3: Use output_type for Structured Responses
**Source**: [OpenAI Agents SDK Tutorial](https://www.datacamp.com/tutorial/openai-agents-sdk-tutorial)
- **Extracted information**: "By defining clear data models and using the output_type parameter, your agents can produce exactly the data structures your application needs" (index 8-1)
- **Location**: Structured Outputs section
- **How to use**: Define Pydantic models for all agent responses.

```python
from pydantic import BaseModel

class LeadAnalysis(BaseModel):
    score: float
    qualification: str
    next_actions: List[str]
    
agent = Agent(
    name="Analyzer",
    instructions="Analyze and qualify leads",
    output_type=LeadAnalysis  # ✅ Structured response
)
```

---

## 2. FastAPI Architecture Rules

### Rule 2.1: Always Use Async Functions
**Source**: [FastAPI Best Practices - GitHub](https://github.com/zhanymkanov/fastapi-best-practices)
- **Extracted information**: "FastAPI is an async framework... If you violate that trust and execute blocking operations within async routes, the event loop will not be able to run subsequent tasks" (index 11-1)
- **Location**: Async/Sync guidelines section
- **How to use**: Every route and service function should be asynchronous, use `asyncio` for I/O operations.

```python
# ✅ CORRECT
@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one()

# ❌ INCORRECT
@router.get("/leads/{lead_id}")
def get_lead(lead_id: str):  # Not async
    # Blocks the event loop
    time.sleep(1)
    return {"lead_id": lead_id}
```

### Rule 2.2: Structure Project by Domain
**Source**: [FastAPI Best Practices - GitHub](https://github.com/zhanymkanov/fastapi-best-practices)
- **Extracted information**: "The structure I found more scalable and evolvable... is inspired by Netflix's Dispatch" (index 11-1)
- **Location**: Project Structure section
- **How to use**: Organize code by business domains, not by file type.

```
pipewise/
├── src/
│   ├── leads/
│   │   ├── router.py      # Lead endpoints
│   │   ├── schemas.py     # Pydantic models
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── services.py    # Business logic
│   │   └── dependencies.py
│   ├── auth/
│   ├── integrations/
│   └── agents/
```

### Rule 2.3: Use Dependency Injection for Everything
**Source**: [FastAPI in Containers Documentation](https://fastapi.tiangolo.com/deployment/docker/)
- **Extracted information**: "Decouple & Reuse dependencies. Dependency calls are cached" (index 11-1)
- **Location**: Best practices section
- **How to use**: Encapsulate all shared logic in dependencies.

```python
# ✅ CORRECT - Reusable dependency
async def get_current_tenant(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Tenant:
    # Validation logic
    return tenant

# Use in multiple endpoints
@router.get("/data")
async def get_data(tenant: Tenant = Depends(get_current_tenant)):
    return {"tenant_id": tenant.id}
```

---

## 3. Multi-Tenancy B2B SaaS Rules

### Rule 3.1: Data Isolation by Tenant ID
**Source**: [Re-defining multi-tenancy - AWS](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/re-defining-multi-tenancy.html)
- **Extracted information**: "The product service shares all of its resources... However, if you look at the order service, you'll see that it has shared compute, but separate storage for each tenant" (index 31-1)
- **Location**: Multi-tenancy patterns section
- **How to use**: Implement Row Level Security and automatic filtering by tenant.

```python
# Implement tenant middleware
class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return JSONResponse(status_code=403, content={"error": "Missing tenant"})
        
        # Inject into context
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response

# Always filter queries by tenant
query = select(Lead).where(
    Lead.tenant_id == request.state.tenant_id
)
```

### Rule 3.2: Shared Resource Pool with Limits
**Source**: [The Need for Multi-Tenancy in Modern B2B SaaS - Frontegg](https://frontegg.com/blog/the-need-for-multi-tenancy-in-modern-b2b-saas)
- **Extracted information**: "Frontegg sidesteps this problem completely... by allowing you to pool all of your tenants into the same environment" (index 32-1)
- **Location**: Resource pooling section
- **How to use**: Share resources but with limits per tenant.

```python
# Rate limiting per tenant
from slowapi import Limiter

def get_tenant_id(request: Request):
    return request.state.tenant_id

limiter = Limiter(key_func=get_tenant_id)

@app.get("/api/leads")
@limiter.limit("100/minute")  # Per tenant, not global
async def get_leads(request: Request):
    pass
```

### Rule 3.3: Configuration and Customization per Tenant
**Source**: [SaaS Multitenancy Components - Frontegg](https://frontegg.com/blog/saas-multitenancy)
- **Extracted information**: "Frontegg enables each tenant to maintain its own configurations, user sets, and security policies" (index 36-1)
- **Location**: Tenant configuration section
- **How to use**: Store tenant-specific configurations.

```python
class TenantConfig(BaseModel):
    tenant_id: str
    features: Dict[str, bool]
    api_limits: Dict[str, int]
    custom_branding: Dict[str, str]
    webhook_urls: List[str]

# Configuration cache
@lru_cache(maxsize=1000)
async def get_tenant_config(tenant_id: str) -> TenantConfig:
    # Load from DB with cache
    pass
```

---

## 4. Testing and Quality Rules

### Rule 4.1: Use FastAPI TestClient with Fixtures
**Source**: [Testing FastAPI Applications - OddBird](https://www.oddbird.net/2024/02/09/testing-fastapi/)
- **Extracted information**: "I consider it a best practice to use a real database when testing, instead of using mocks" (index 46-1)
- **Location**: Testing best practices section
- **How to use**: Create reusable fixtures with real databases.

```python
# conftest.py
@pytest.fixture
async def test_db():
    # Create temporary DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def test_client(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    with TestClient(app) as client:
        yield client
```

### Rule 4.2: Isolated Tests with Transactions
**Source**: [Developing and Testing an Asynchronous API - TestDriven.io](https://testdriven.io/blog/fastapi-crud/)
- **Extracted information**: "Use a DB session that will roll back after the test is complete to ensure clean tables for each test" (index 43-1)
- **Location**: Database testing section
- **How to use**: Each test should run in a transaction that rolls back.

```python
@pytest.fixture
async def db_session(engine):
    connection = await engine.connect()
    transaction = await connection.begin()
    
    session = AsyncSession(bind=connection)
    
    yield session
    
    await transaction.rollback()
    await connection.close()
```

### Rule 4.3: Minimum 80% Coverage
**Source**: [FastAPI Testing with PyTest Guide](https://www.augustinfotech.com/blogs/how-to-use-coverage-unit-testing-in-fastapi-using-pytest/)
- **Extracted information**: "Coverage testing ensures that the entire source code is exercised by tests" (index 42-1)
- **Location**: Coverage testing section
- **How to use**: Configure pytest with minimum coverage.

```ini
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = --cov=app --cov-report=html --cov-fail-under=80
testpaths = tests
python_files = test_*.py
```

---

## 5. CI/CD Rules

### Rule 5.1: Multi-Stage Pipeline with Cache
**Source**: [Enhancing GitHub Actions CI for FastAPI - PyImageSearch](https://pyimagesearch.com/2024/11/04/enhancing-github-actions-ci-for-fastapi-build-test-and-publish/)
- **Extracted information**: "Configure the CI pipeline to run automated tests, check code quality with linters, and manage dependencies" (index 21-1)
- **Location**: CI pipeline configuration section
- **How to use**: Implement parallel stages with dependency caching.

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Cache Dependencies
      uses: actions/cache@v3
      with:
        path: |
          ~/.cache/pip
          ~/.cache/pypoetry
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt', '**/poetry.lock') }}
    
    - name: Run Tests Parallel
      run: |
        pytest -n auto --cov=app --cov-fail-under=80
```

### Rule 5.2: Security in the Pipeline
**Source**: [How to build a CI/CD pipeline - GitHub Blog](https://github.blog/enterprise-software/ci-cd/build-ci-cd-pipeline-github-actions-four-steps/)
- **Extracted information**: "Since GitHub Actions is fully integrated with GitHub, you can set any webhook as an event trigger" (index 22-1)
- **Location**: Security practices section
- **How to use**: Scan vulnerabilities on every push.

```yaml
security-scan:
  runs-on: ubuntu-latest
  steps:
  - uses: actions/checkout@v4
  
  - name: Run Trivy Scanner
    uses: aquasecurity/trivy-action@master
    with:
      scan-type: 'fs'
      scan-ref: '.'
      severity: 'CRITICAL,HIGH'
      exit-code: '1'  # Fail if vulnerabilities found
  
  - name: Dependency Check
    run: |
      pip install safety
      safety check --json
```

### Rule 5.3: Automated Deployment with Validations
**Source**: [FastAPI with GitHub Actions and GHCR - PyImageSearch](https://pyimagesearch.com/2024/11/11/fastapi-with-github-actions-and-ghcr-continuous-delivery-made-simple/)
- **Extracted information**: "Automating the entire deployment process... scanning it for vulnerabilities" (index 25-1)
- **Location**: CD pipeline section
- **How to use**: Deploy only after all validations pass.

```yaml
deploy:
  needs: [test, security-scan, build]
  if: github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  
  steps:
  - name: Deploy to Production
    run: |
      # Only if all checks pass
      kubectl apply -f k8s/
      kubectl rollout status deployment/pipewise
```

---

## 6. Containerization Rules

### Rule 6.1: Optimized Multi-Stage Builds
**Source**: [FastAPI in Containers - Docker](https://fastapi.tiangolo.com/deployment/docker/)
- **Extracted information**: "Taking care of the order of instructions in the Dockerfile and the Docker cache you can minimize build times" (index 51-1)
- **Location**: Docker optimization section
- **How to use**: Separate build from runtime, order layers by change frequency.

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim as builder
WORKDIR /build

# Copy only requirements first (changes less)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app

# Copy installed dependencies
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy code (changes more frequently)
COPY ./app ./app

# ✅ Use exec form for graceful shutdown
CMD ["fastapi", "run", "app/main.py", "--port", "80"]
```

### Rule 6.2: Security Configuration
**Source**: [Dockerizing FastAPI with Postgres - TestDriven.io](https://testdriven.io/blog/fastapi-docker-traefik/)
- **Extracted information**: "Non-root user for the services... For production environments" (index 54-1)
- **Location**: Production security section
- **How to use**: Never run as root in production.

```dockerfile
# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Change ownership
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Mandatory health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:80/health || exit 1
```

### Rule 6.3: Resource Optimization
**Source**: [Containerizing FastAPI Applications - Better Stack](https://betterstack.com/community/guides/scaling-python/fastapi-with-docker/)
- **Extracted information**: "Docker packages your app with everything it needs, so it runs the same anywhere" (index 56-1)
- **Location**: Resource optimization section
- **How to use**: Limit resources and use slim images.

```yaml
# docker-compose.yml
services:
  api:
    image: pipewise-api:latest
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped
```

---

## 7. Asynchronous Processing Rules

### Rule 7.1: Separate Queues by Priority
**Source**: [Using Celery for Asynchronous Task Queues - Syskool](https://syskool.com/using-celery-for-asynchronous-task-queues-in-python/)
- **Extracted information**: "Use Dedicated Queues: Separate critical tasks and low-priority tasks into different queues" (index 61-1)
- **Location**: Best practices section
- **How to use**: Configure multiple queues with dedicated workers.

```python
# celery_config.py
task_routes = {
    'app.tasks.critical.*': {'queue': 'critical'},
    'app.tasks.emails.*': {'queue': 'emails'},
    'app.tasks.analytics.*': {'queue': 'low_priority'},
}

# Start specific workers
# celery -A app worker -Q critical --concurrency=4
# celery -A app worker -Q emails --concurrency=2
# celery -A app worker -Q low_priority --concurrency=1
```

### Rule 7.2: Implement Smart Retry
**Source**: [Asynchronous Tasks with FastAPI and Celery - TestDriven.io](https://testdriven.io/blog/fastapi-and-celery/)
- **Extracted information**: "The Celery worker will pick up your instructions and handle them at the scheduled time" (index 65-1)
- **Location**: Task configuration section
- **How to use**: Configure exponential retries with limits.

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    retry_backoff=True,      # Exponential: 1m, 2m, 4m
    retry_jitter=True        # Add randomness
)
def process_lead(self, lead_id: str):
    try:
        # Processing
        result = analyze_lead(lead_id)
        return result
    except TemporaryError as exc:
        # Retry only temporary errors
        raise self.retry(exc=exc)
    except PermanentError:
        # Don't retry permanent errors
        log_error(f"Permanent failure for lead {lead_id}")
        raise
```

### Rule 7.3: Task Monitoring
**Source**: [The problems with Python's Celery - Hatchet](https://docs.hatchet.run/blog/problems-with-celery)
- **Extracted information**: "A common pattern is to limit concurrency per user or tenant" (index 63-1)
- **Location**: Monitoring patterns section
- **How to use**: Implement custom metrics per tenant.

```python
from prometheus_client import Counter, Histogram

# Metrics per tenant
task_counter = Counter(
    'celery_tasks_total',
    'Total tasks processed',
    ['task_name', 'tenant_id', 'status']
)

task_duration = Histogram(
    'celery_task_duration_seconds',
    'Task execution time',
    ['task_name', 'tenant_id']
)

@celery_app.task
def monitored_task(tenant_id: str, data: dict):
    start_time = time.time()
    
    try:
        result = process_data(data)
        task_counter.labels(
            task_name='process_data',
            tenant_id=tenant_id,
            status='success'
        ).inc()
        return result
    except Exception as e:
        task_counter.labels(
            task_name='process_data',
            tenant_id=tenant_id,
            status='failure'
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        task_duration.labels(
            task_name='process_data',
            tenant_id=tenant_id
        ).observe(duration)
```

---

## 8. Monitoring and Observability Rules

### Rule 8.1: Metrics by Component
**Source**: [Cloud Monitoring with Prometheus and Grafana - BDCC Global](https://www.bdccglobal.com/blog/cloud-monitoring-with-prometheus-and-grafana/)
- **Extracted information**: "Prometheus scrapes metrics from cloud services... These metrics are stored in Prometheus' TSDB" (index 71-1)
- **Location**: Metrics collection section
- **How to use**: Expose specific metrics per service.

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Application metrics
request_count = Counter(
    'pipewise_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status', 'tenant_id']
)

request_duration = Histogram(
    'pipewise_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'tenant_id']
)

active_leads = Gauge(
    'pipewise_active_leads',
    'Current active leads in pipeline',
    ['stage', 'tenant_id']
)

# Middleware to capture metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        tenant_id=request.state.tenant_id
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path,
        tenant_id=request.state.tenant_id
    ).observe(duration)
    
    return response
```

### Rule 8.2: SLO-Based Alerts
**Source**: [What is observability? Best practices - Grafana Blog](https://grafana.com/blog/2022/07/01/what-is-observability-best-practices-key-metrics-methodologies-and-more/)
- **Extracted information**: "Instead of effectively alerting on breaching your SLO within a small window, you want to alert on breaching your SLO in increasingly larger windows" (index 76-1)
- **Location**: SLO alerting section
- **How to use**: Implement error budgets and gradual alerts.

```yaml
# prometheus/alerts.yml
groups:
- name: slo_alerts
  rules:
  - alert: ErrorBudgetBurn
    expr: |
      (
        rate(pipewise_requests_total{status=~"5.."}[5m])
        / rate(pipewise_requests_total[5m])
      ) > 0.001  # 99.9% SLO
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Error budget burn rate high"
      
  - alert: ErrorBudgetCritical
    expr: |
      (
        rate(pipewise_requests_total{status=~"5.."}[30m])
        / rate(pipewise_requests_total[30m])
      ) > 0.005  # 5x burn rate
    for: 5m
    labels:
      severity: critical
```

### Rule 8.3: Dashboards per Tenant
**Source**: [Understanding Data Observability with Grafana - Orchestra](https://www.getorchestra.io/guides/understanding-data-observability-with-grafana)
- **Extracted information**: "Grafana allows users to create customizable dashboards that can help monitor the health and performance" (index 73-1)
- **Location**: Dashboard configuration section
- **How to use**: Create parameterized dashboards by tenant.

```json
{
  "dashboard": {
    "title": "PipeWise - Tenant Overview",
    "templating": {
      "list": [{
        "name": "tenant_id",
        "type": "query",
        "query": "label_values(pipewise_requests_total, tenant_id)",
        "refresh": 1
      }]
    },
    "panels": [{
      "title": "Request Rate",
      "targets": [{
        "expr": "rate(pipewise_requests_total{tenant_id=\"$tenant_id\"}[5m])"
      }]
    }, {
      "title": "Lead Conversion Funnel",
      "targets": [{
        "expr": "pipewise_active_leads{tenant_id=\"$tenant_id\"}"
      }]
    }]
  }
}
```

---

## 9. React 19 Rules

### Rule 9.1: Use the New React Compiler
**Source**: [React v19 – React](https://react.dev/blog/2024/12/05/react-19)
- **Extracted information**: "In React 19, we're adding support for using async functions in transitions to handle pending states, errors, forms, and optimistic updates automatically" (index 81-1)
- **Location**: React Compiler section
- **How to use**: Remove manual optimization hooks and let the compiler optimize automatically.

```typescript
// ✅ CORRECT - React 19 with compiler
function LeadCard({ lead }: { lead: Lead }) {
  // No need for useMemo/useCallback
  const handleClick = () => {
    processLead(lead.id);
  };
  
  return (
    <div onClick={handleClick}>
      <h3>{lead.name}</h3>
      <p>{lead.score}</p>
    </div>
  );
}

// ❌ INCORRECT - Unnecessary manual optimization
const handleClick = useCallback(() => {
  processLead(lead.id);
}, [lead.id]);
```

### Rule 9.2: Implement Server Components by Default
**Source**: [React 19 New Features - GeeksforGeeks](https://www.geeksforgeeks.org/react-19-new-features-and-updates/)
- **Extracted information**: "Server Components are now the default, you add 'use client' to Client Components when using hooks for interactivity" (index 82-1)
- **Location**: Server Components section
- **How to use**: Every component is a Server Component by default, add 'use client' only when you need interactivity.

```typescript
// ✅ CORRECT - Server Component by default
// app/components/LeadList.tsx
async function LeadList() {
  const leads = await fetchLeads(); // Runs on server
  
  return (
    <div>
      {leads.map(lead => (
        <LeadCard key={lead.id} lead={lead} />
      ))}
    </div>
  );
}

// app/components/LeadActions.tsx
'use client' // Only when you need hooks/events

import { useState } from 'react';

function LeadActions({ leadId }: { leadId: string }) {
  const [isProcessing, setIsProcessing] = useState(false);
  
  return (
    <button onClick={() => setIsProcessing(true)}>
      Process Lead
    </button>
  );
}
```

### Rule 9.3: Use Actions for Form Handling
**Source**: [New React 19 Features - FreeCodeCamp](https://www.freecodecamp.org/news/new-react-19-features-you-should-know-with-code-examples/)
- **Extracted information**: "Actions simplify the process of handling form submissions and integrating with React's concurrent features" (index 83-1)
- **Location**: Actions section
- **How to use**: Replace traditional event handlers with Actions.

```typescript
// ✅ CORRECT - Using Actions
async function createLead(formData: FormData) {
  'use server';
  
  const lead = {
    name: formData.get('name'),
    email: formData.get('email'),
    company: formData.get('company')
  };
  
  await saveLead(lead);
  revalidatePath('/leads');
}

export function LeadForm() {
  return (
    <form action={createLead}>
      <input name="name" required />
      <input name="email" type="email" required />
      <input name="company" required />
      <button type="submit">Create Lead</button>
    </form>
  );
}

// ❌ INCORRECT - Traditional event handlers
function LeadForm() {
  const handleSubmit = async (e) => {
    e.preventDefault();
    // Manual form handling
  };
  
  return <form onSubmit={handleSubmit}>...</form>;
}
```

### Rule 9.4: Implement use() for Data Fetching
**Source**: [React Design Patterns 2025 - Telerik](https://www.telerik.com/blogs/react-design-patterns-best-practices)
- **Extracted information**: "The use() API can only be called in render, similar to hooks. Unlike hooks, use can be called conditionally" (index 84-1)
- **Location**: use() API section
- **How to use**: Use use() for async resources in components.

```typescript
// ✅ CORRECT - Using use() for promises
import { use } from 'react';

function LeadDetails({ leadPromise }: { leadPromise: Promise<Lead> }) {
  const lead = use(leadPromise); // Suspends until resolved
  
  return (
    <div>
      <h1>{lead.name}</h1>
      <p>Score: {lead.score}</p>
    </div>
  );
}

// With conditional Context
function ConditionalComponent({ showDetails }: { showDetails: boolean }) {
  if (showDetails) {
    const theme = use(ThemeContext); // Conditional use() allowed
    return <div style={{ color: theme.primary }}>Details</div>;
  }
  return <div>Summary</div>;
}
```

---

## 10. Tailwind CSS 4 Rules

### Rule 10.1: Migrate to New Import Syntax
**Source**: [Tailwind CSS v4.0 - Official Blog](https://tailwindcss.com/blog/tailwindcss-v4)
- **Extracted information**: "Just one-line of CSS — no more @tailwind directives, just add @import 'tailwindcss'" (index 91-1)
- **Location**: Installation section
- **How to use**: Use @import instead of @tailwind directives.

```css
/* ✅ CORRECT - Tailwind CSS 4 */
@import "tailwindcss";

/* Customization with CSS variables */
@theme {
  --color-primary: oklch(0.7 0.28 145);
  --font-sans: "Inter", sans-serif;
  --spacing-128: 32rem;
}

/* ❌ INCORRECT - v3 syntax */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### Rule 10.2: Use @layer for Custom Components
**Source**: [Tailwind CSS v4 Upgrade Guide](https://tailwindcss.com/docs/upgrade-guide)
- **Extracted information**: "Component utilities... can be overwritten by other Tailwind utilities without additional configuration" (index 92-1)
- **Location**: Custom utilities section
- **How to use**: Define components with @utility instead of @layer components.

```css
/* ✅ CORRECT - Tailwind CSS 4 */
@utility btn-primary {
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: theme(colors.blue.600);
  color: white;
}

@utility card {
  background: white;
  border-radius: theme(borderRadius.lg);
  box-shadow: theme(boxShadow.md);
  padding: theme(spacing.6);
}

/* ❌ INCORRECT - v3 syntax */
@layer components {
  .btn-primary {
    @apply rounded px-4 py-2 bg-blue-600 text-white;
  }
}
```

### Rule 10.3: Performance Optimization with Oxide Engine
**Source**: [Tailwind CSS 4.0: Everything you need to know](https://daily.dev/blog/tailwind-css-40-everything-you-need-to-know-in-one-place)
- **Extracted information**: "Tailwind CSS 4.0 is up to 10 times faster than previous versions, thanks to the Oxide engine" (index 94-1)
- **Location**: Performance section
- **How to use**: Configure automatic content detection.

```javascript
// tailwind.config.js is no longer needed for basic configuration
// Content detection is automatic

// For advanced configuration, use CSS
/* globals.css */
@theme {
  /* Extend colors */
  --color-brand-50: oklch(0.97 0.02 250);
  --color-brand-100: oklch(0.93 0.04 250);
  --color-brand-500: oklch(0.53 0.2 250);
  --color-brand-900: oklch(0.23 0.15 250);
  
  /* Custom breakpoints */
  --breakpoint-xs: 475px;
  --breakpoint-3xl: 1920px;
}
```

### Rule 10.4: Dark Mode with CSS Variables
**Source**: [Tailwind CSS Best Practices 2025](https://www.bootstrapdash.com/blog/tailwind-css-best-practices)
- **Extracted information**: "Dark mode in Tailwind CSS... You can easily switch between light and dark modes" (index 96-1)
- **Location**: Dark mode section
- **How to use**: Implement dark mode with modern CSS variables.

```css
/* ✅ CORRECT - CSS variables for themes */
@theme {
  /* Adaptive colors */
  --color-background: light-dark(
    oklch(1 0 0),      /* light mode */
    oklch(0.15 0 0)    /* dark mode */
  );
  
  --color-text: light-dark(
    oklch(0.2 0 0),    /* light mode */
    oklch(0.95 0 0)    /* dark mode */
  );
}

/* Component that adapts automatically */
.lead-card {
  background: var(--color-background);
  color: var(--color-text);
  @apply rounded-lg p-4 shadow-md;
}
```

---

## 11. Next.js 15 Rules

### Rule 11.1: Use App Router with React Server Components
**Source**: [Next.js 15 - Official Blog](https://nextjs.org/blog/next-15)
- **Extracted information**: "Next.js 15 introduces React 19 support, caching improvements, a stable release for Turbopack" (index 102-1)
- **Location**: App Router section
- **How to use**: Structure application with App Router and RSC by default.

```typescript
// ✅ CORRECT - App Router structure
// app/leads/page.tsx
export default async function LeadsPage() {
  const leads = await fetchLeads(); // Server Component
  
  return (
    <div>
      <h1>Leads Dashboard</h1>
      <LeadsList leads={leads} />
    </div>
  );
}

// app/leads/[id]/page.tsx
export default async function LeadDetailPage({
  params
}: {
  params: { id: string }
}) {
  const lead = await fetchLead(params.id);
  
  return <LeadDetail lead={lead} />;
}

// ❌ INCORRECT - Pages Router (legacy)
// pages/leads/index.tsx
export async function getServerSideProps() {
  // Old pattern
}
```

### Rule 11.2: Implement Form Component for Navigation
**Source**: [Next.js 15 Best Practices](https://www.antanaskovic.com/blog/next-js-15-best-practices-unlocking-the-full-potential-of-modern-web-development)
- **Extracted information**: "The new <Form> component extends the HTML <form> element with prefetching, client-side navigation" (index 104-1)
- **Location**: Form component section
- **How to use**: Use Form for forms that navigate.

```typescript
// ✅ CORRECT - Next.js 15 Form component
import { Form } from 'next/form';

export function SearchForm() {
  return (
    <Form action="/search">
      <input
        name="query"
        placeholder="Search leads..."
        className="rounded-md border px-4 py-2"
      />
      <button type="submit">Search</button>
    </Form>
  );
}

// With Server Action
async function searchLeads(formData: FormData) {
  'use server';
  const query = formData.get('query');
  redirect(`/search?q=${query}`);
}

export function AdvancedSearchForm() {
  return (
    <Form action={searchLeads}>
      <input name="query" required />
      <select name="status">
        <option value="new">New</option>
        <option value="qualified">Qualified</option>
      </select>
    </Form>
  );
}
```

### Rule 11.3: Optimization with Turbopack
**Source**: [Next.js 15.3 Release](https://nextjs.org/blog/next-15-3)
- **Extracted information**: "Next.js 15.3 includes Turbopack for builds... plugin response times have improved ~60%" (index 105-1)
- **Location**: Turbopack section
- **How to use**: Enable Turbopack for fast development.

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Turbopack enabled by default in dev
  experimental: {
    // Instrumentation for monitoring
    instrumentationHook: true,
    // View Transitions API
    viewTransitions: true,
  },
  
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.pipewise.com',
      },
    ],
  },
};

module.exports = nextConfig;
```

### Rule 11.4: Scalable Folder Structure
**Source**: [Best Practices for Organizing Next.js 15 - DEV Community](https://dev.to/bajrayejoon/best-practices-for-organizing-your-nextjs-15-2025-53ji)
- **Extracted information**: "Placing your code inside a src directory... it's like using a napkin at a barbecue restaurant" (index 110-1)
- **Location**: Folder structure section
- **How to use**: Organize by features, not by file types.

```
pipewise-frontend/
├── src/
│   ├── app/                    # App Router
│   │   ├── (auth)/            # Auth route group
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/       # Dashboard group
│   │   │   ├── layout.tsx     # Shared layout
│   │   │   ├── leads/
│   │   │   ├── analytics/
│   │   │   └── settings/
│   │   └── api/               # Route handlers
│   │       └── leads/
│   ├── components/
│   │   ├── ui/                # Base UI components
│   │   │   ├── Button/
│   │   │   ├── Card/
│   │   │   └── Modal/
│   │   └── features/          # Components by feature
│   │       ├── leads/
│   │       │   ├── LeadCard/
│   │       │   ├── LeadForm/
│   │       │   └── LeadTable/
│   │       └── analytics/
│   ├── lib/                   # Utilities
│   │   ├── api/              # API client
│   │   ├── auth/             # Auth helpers
│   │   └── utils/            # General helpers
│   ├── hooks/                # Custom hooks
│   └── types/                # TypeScript types
```

### Rule 11.5: Implement Middleware for Multi-tenancy
**Source**: [Next.js best practices in 2025](https://www.augustinfotech.com/blogs/nextjs-best-practices-in-2025/)
- **Extracted information**: "Use middleware to handle route-based logic efficiently" (index 103-1)
- **Location**: Middleware section
- **How to use**: Validate tenant in middleware.

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Get tenant from subdomain or header
  const hostname = request.headers.get('host') || '';
  const tenant = hostname.split('.')[0];
  
  // Validate tenant
  if (!isValidTenant(tenant)) {
    return NextResponse.redirect(new URL('/invalid-tenant', request.url));
  }
  
  // Inject tenant in headers
  const response = NextResponse.next();
  response.headers.set('x-tenant-id', tenant);
  
  // For protected routes
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    const token = request.cookies.get('auth-token');
    
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }
  
  return response;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
```

---

## Priority Summary

### Critical (Implement First)
1. **AgentSDK Migration**: Foundation for all AI logic
2. **Multi-tenancy**: Fundamental for B2B SaaS
3. **React 19 + Next.js 15**: Modern frontend architecture
4. **Automated testing**: Quality from the start
5. **Basic CI/CD**: Reliable deployment

### Important (Second Phase)
1. **Tailwind CSS 4**: Optimized design system
2. **Optimized containerization**: Scalability
3. **Asynchronous processing**: Backend performance
4. **Server Components**: Frontend performance
5. **Advanced security**: Data protection

### Optimizations (Third Phase)
1. **Advanced monitoring**: Business insights
2. **Auto-scaling**: Cost efficiency
3. **ML in monitoring**: Anomaly detection
4. **Performance tuning**: Final optimization
5. **View Transitions**: Enhanced UX

---

## Validation Checklist

Before considering an improvement complete, validate:

### Backend
- [ ] Does it follow the rules in this document?
- [ ] Does it have tests with >80% coverage?
- [ ] Is it documented in OpenAPI?
- [ ] Does it pass the CI/CD pipeline?
- [ ] Does it respect multi-tenant isolation?
- [ ] Does it have monitoring metrics?
- [ ] Does it handle errors correctly?
- [ ] Is it horizontally scalable?

### Frontend
- [ ] Does it use Server Components by default?
- [ ] Does it implement 'use client' only when necessary?
- [ ] Does it follow the feature-based folder structure?
- [ ] Does it use the React 19 compiler?
- [ ] Does it implement Tailwind CSS 4 with CSS variables?
- [ ] Does it have E2E tests with Playwright?
- [ ] Does it meet Core Web Vitals?
- [ ] Is it accessible (WCAG 2.1)?

### General
- [ ] Does it meet defined SLOs?
- [ ] Is it optimized for performance?
- [ ] Does it have updated documentation?
- [ ] Does it follow team conventions?

This document should be updated as new best practices are discovered or production issues are encountered.

---

## Reference Versions

This document is based on the following versions:
- **OpenAI AgentSDK**: Latest (2025)
- **Python**: 3.11+
- **FastAPI**: 0.110+
- **React**: 19.0
- **Next.js**: 15.3
- **Tailwind CSS**: 4.0
- **Node.js**: 20+
- **PostgreSQL**: 15+
- **Redis**: 7+

Ensure you use these versions or higher to guarantee compatibility with all rules and examples.