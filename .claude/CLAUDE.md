# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

**PipeWise** is a B2B CRM platform that solves the speed-to-lead challenge through AI-powered automation. It features a **Python FastAPI backend** with **Next.js 15 frontend**, built for multi-tenant SaaS architecture.

### Tech Stack
- **Backend**: Python 3.11+, FastAPI, OpenAI AgentSDK, Supabase, Redis, Celery
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS 4, Radix UI
- **Database**: PostgreSQL with Supabase (Row Level Security enabled)
- **AI**: OpenAI AgentSDK for lead qualification, outbound contact, and meeting scheduling

## Development Commands

### Backend Development
```bash
# Install dependencies
uv sync

# Development server (auto-reload)
python server.py

# Run tests with coverage (minimum 80% required)
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m security               # Security tests only

# Code quality checks
black app/                        # Format code
isort app/                        # Sort imports
flake8 app/                       # Lint code
mypy app/                         # Type checking
```

### Frontend Development
```bash
# Navigate to frontend directory first
cd frontend

# Install dependencies
npm install

# Development server with Turbopack (port 3000)
npm run dev

# Production build and start
npm run build && npm start

# Lint frontend code
npm run lint
```

## Key Architectural Patterns

### Multi-Agent AI System
The application uses OpenAI AgentSDK with 4 specialized agents:
- **Lead Qualifier**: Scores and qualifies incoming leads
- **Outbound Contact**: Automated personalized outreach  
- **Meeting Scheduler**: Calendly integration for booking
- **WhatsApp Agent**: Multi-platform communication

All agents use `@function_tool` decorators and typed contexts for dependency injection.

### Multi-Tenant Architecture
- **Row Level Security (RLS)** in Supabase for data isolation
- **Tenant middleware** automatically filters all queries by tenant_id
- **Per-tenant rate limiting** and configuration
- **Shared resource pool** with tenant-specific limits

### Async-First Design
- All FastAPI routes and database operations are async
- Background task processing with Celery + Redis
- Separate queues by priority (critical, emails, low_priority)
- Comprehensive error handling with exponential retry

### Testing Strategy
- **Minimum 80% code coverage** enforced in CI
- **Real database testing** with transaction rollback
- **Parallel test execution** with pytest-xdist
- Test categories: unit, integration, e2e, security, performance

## Project Structure

### Backend (`/app/`)
```
app/
├── agents/          # AI agents with OpenAI AgentSDK
├── api/             # FastAPI routes (70+ endpoints)
├── auth/            # JWT + 2FA authentication with Redis
├── core/            # Configuration and dependencies
├── models/          # SQLAlchemy models with multi-tenancy
├── schemas/         # Pydantic validation schemas
├── services/        # Business logic services
└── supabase/        # Database client and migrations
```

### Frontend (`/frontend/`)
```
frontend/
├── app/             # Next.js 15 App Router
├── components/      # Radix UI + custom components
├── hooks/           # React hooks for API integration
├── lib/             # Supabase client and utilities
└── public/          # Static assets
```

## Important Development Rules

### OpenAI AgentSDK Migration
- Always use `@function_tool` decorators for external service interactions
- Implement typed contexts for dependency injection
- Use `output_type` parameter for structured Pydantic responses

### React 19 + Next.js 15
- Server Components by default, add `'use client'` only when needed
- Use Actions for form handling instead of traditional event handlers
- Use `use()` hook for async resources and conditional context
- Use Next.js 15 `<Form>` component for navigation forms

### Multi-Tenancy Requirements
- Every database query must filter by tenant_id
- Use tenant middleware to inject tenant context
- Implement per-tenant rate limiting
- Store tenant-specific configurations with caching

### Testing Requirements
- Write tests for all new features (unit + integration)
- Use real database with transaction rollback
- Minimum 80% coverage enforced by pytest
- Follow test categories: unit, integration, e2e, security

## Environment Setup

### Required Environment Variables
```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# OpenAI
OPENAI_API_KEY=your_openai_key

# Redis
REDIS_URL=redis://localhost:6379

# Email & Integrations
SMTP_HOST=your_smtp_host
CALENDLY_API_KEY=your_calendly_key
```

### Database Setup
1. Run Supabase migrations: `supabase db push`
2. Set up Row Level Security policies
3. Enable real-time subscriptions for live updates

## Production Considerations

### Backend Deployment
- Use `gunicorn` with `uvicorn` workers for production
- Configure health checks at `/health`
- Enable metrics collection at `/metrics`
- Set up proper logging with structured output

### Frontend Deployment
- Next.js 15 with static optimization enabled
- Image optimization with AVIF/WebP support
- Bundle splitting for optimal loading
- Configure proper CORS and security headers

## Common Patterns

### Database Queries
```python
# Always filter by tenant_id
async def get_leads(tenant_id: str, db: AsyncSession):
    result = await db.execute(
        select(Lead).where(Lead.tenant_id == tenant_id)
    )
    return result.scalars().all()
```

### Agent Implementation
```python
@function_tool
def qualify_lead(lead_data: str) -> str:
    """Qualifies a lead using AI analysis."""
    # Implementation with automatic validation
    
agent = Agent[TenantContext](
    name="Lead Qualifier",
    instructions="Analyze and score leads",
    output_type=LeadAnalysis
)
```

### React Server Components
```typescript
// Default: Server Component
async function LeadsPage() {
  const leads = await fetchLeads(); // Runs on server
  return <LeadsList leads={leads} />;
}

// Only when interactivity needed
'use client'
function LeadActions() {
  const [processing, setProcessing] = useState(false);
  // Interactive component
}
```

This architecture ensures scalability, security, and maintainability while providing sub-5-minute lead response times through AI automation.