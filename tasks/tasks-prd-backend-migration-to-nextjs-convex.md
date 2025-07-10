# Task List: Backend Migration to Next.js, Vercel AI SDK, and Convex

## Relevant Files

- `frontend/convex/schema.ts` - Convex database schema definitions for agent memories, rate limits, and OAuth tokens
- `frontend/convex/_generated/api.ts` - Auto-generated Convex API types and functions
- `frontend/convex/agent-memories.ts` - Convex functions for agent memory management
- `frontend/convex/rate-limits.ts` - Convex functions for rate limiting
- `frontend/convex/oauth-tokens.ts` - Convex functions for OAuth token management
- `frontend/middleware.ts` - Clerk authentication middleware for route protection
- `frontend/app/layout.tsx` - Root layout with Clerk provider integration
- `frontend/hooks/use-auth.tsx` - Updated authentication hook using Clerk
- `frontend/lib/supabase-admin.ts` - Server-side Supabase utilities for backend operations
- `frontend/lib/ai/agents/base-agent.ts` - Base agent class with common functionality
- `frontend/lib/ai/agents/coordinator.ts` - Coordinator Agent implementation
- `frontend/lib/ai/agents/meeting-scheduler.ts` - Meeting Scheduler Agent implementation
- `frontend/lib/ai/agents/lead-administrator.ts` - Lead Administrator Agent implementation
- `frontend/lib/ai/tools/base-tool.ts` - Base tool class with error handling and retry logic
- `frontend/lib/ai/tools/sendgrid.ts` - SendGrid email tool implementation
- `frontend/lib/ai/tools/twitter.ts` - Twitter/X API tool implementation
- `frontend/lib/ai/tools/google-calendar.ts` - Google Calendar tool implementation
- `frontend/lib/ai/tools/calendly.ts` - Calendly scheduling tool implementation
- `frontend/lib/ai/tools/salesforce.ts` - Salesforce CRM tool implementation
- `frontend/lib/ai/tools/pipedrive.ts` - Pipedrive CRM tool implementation
- `frontend/lib/ai/tools/zoho-crm.ts` - Zoho CRM tool implementation
- `frontend/app/api/chat/route.ts` - Main chat API endpoint with Vercel AI SDK integration
- `frontend/app/api/agents/[agent]/route.ts` - Agent-specific API routes
- `frontend/app/api/tools/[tool]/route.ts` - Direct tool invocation API routes
- `frontend/app/api/oauth/[provider]/route.ts` - OAuth flow API routes
- `frontend/app/chat/page.tsx` - Updated chat interface for new streaming format
- `frontend/components/login-form.tsx` - Updated login form with Clerk integration
- `frontend/components/signup-form.tsx` - Updated signup form with Clerk integration
- `frontend/components/nav-user.tsx` - Updated user navigation with Clerk components
- `frontend/components/ui/agent-plan.tsx` - Updated agent plan component for new format
- `frontend/components/ui/workflow-sidebar.tsx` - Updated workflow sidebar for new structure
- `frontend/components/oauth-integration-card.tsx` - Updated OAuth integration card
- `frontend/lib/errors/index.ts` - Custom error classes and error handling utilities
- `frontend/lib/encryption.ts` - Token encryption/decryption utilities
- `frontend/package.json` - Updated dependencies for Convex, Clerk, and Vercel AI SDK

### Notes

- Unit tests should be created alongside each implementation file (e.g., `base-agent.test.ts`)
- Use `npm test` to run all tests, or `npm test -- --testPathPattern=specific-file` for specific tests
- Convex functions are automatically deployed when pushed to the connected branch
- Environment variables need to be configured in both local `.env.local` and Vercel dashboard
- OAuth tokens will be encrypted before storage in Convex for security

## Tasks

- [ ] 1.0 Set up Core Infrastructure and Authentication
  - [ ] 1.1 Initialize Convex in the frontend directory using `npx convex init`
  - [ ] 1.2 Install and configure Clerk Next.js SDK in `frontend/package.json`
  - [ ] 1.3 Create Convex schema file with agent_memories, rate_limits, oauth_tokens, and agent_handoffs tables
  - [ ] 1.4 Set up environment variables for Convex, Clerk, and existing services
  - [ ] 1.5 Create Clerk middleware for route protection in `frontend/middleware.ts`
  - [ ] 1.6 Update root layout to include ClerkProvider in `frontend/app/layout.tsx`
  - [ ] 1.7 Update authentication hook to use Clerk in `frontend/hooks/use-auth.tsx`
  - [ ] 1.8 Create server-side Supabase utilities in `frontend/lib/supabase-admin.ts`

- [ ] 2.0 Implement Database Architecture (Convex + Supabase)
  - [ ] 2.1 Define Convex schema for agent memories with user_id, agent_type, conversation_history, and context fields
  - [ ] 2.2 Define Convex schema for rate limits with user_id, endpoint, request_count, and reset_time fields
  - [ ] 2.3 Define Convex schema for OAuth tokens with user_id, provider, encrypted_tokens, and expiry fields
  - [ ] 2.4 Define Convex schema for agent handoffs with source_agent, target_agent, context, and status fields
  - [ ] 2.5 Create Convex functions for agent memory CRUD operations in `frontend/convex/agent-memories.ts`
  - [ ] 2.6 Create Convex functions for rate limiting in `frontend/convex/rate-limits.ts`
  - [ ] 2.7 Create Convex functions for OAuth token management in `frontend/convex/oauth-tokens.ts`
  - [ ] 2.8 Create token encryption/decryption utilities in `frontend/lib/encryption.ts`
  - [ ] 2.9 Test all Convex functions with proper error handling and validation

- [ ] 3.0 Migrate Agent Logic and Tools to TypeScript
  - [ ] 3.1 Create base agent class with common functionality in `frontend/lib/ai/agents/base-agent.ts`
  - [ ] 3.2 Create base tool class with error handling and retry logic in `frontend/lib/ai/tools/base-tool.ts`
  - [ ] 3.3 Implement Coordinator Agent logic in `frontend/lib/ai/agents/coordinator.ts`
  - [ ] 3.4 Implement Meeting Scheduler Agent logic in `frontend/lib/ai/agents/meeting-scheduler.ts`
  - [ ] 3.5 Implement Lead Administrator Agent logic in `frontend/lib/ai/agents/lead-administrator.ts`
  - [ ] 3.6 Create SendGrid email tool in `frontend/lib/ai/tools/sendgrid.ts`
  - [ ] 3.7 Create Twitter/X API tool in `frontend/lib/ai/tools/twitter.ts`
  - [ ] 3.8 Create Google Calendar tool in `frontend/lib/ai/tools/google-calendar.ts`
  - [ ] 3.9 Create Calendly scheduling tool in `frontend/lib/ai/tools/calendly.ts`
  - [ ] 3.10 Create Salesforce CRM tool in `frontend/lib/ai/tools/salesforce.ts`
  - [ ] 3.11 Create Pipedrive CRM tool in `frontend/lib/ai/tools/pipedrive.ts`
  - [ ] 3.12 Create Zoho CRM tool in `frontend/lib/ai/tools/zoho-crm.ts`
  - [ ] 3.13 Create comprehensive error handling system in `frontend/lib/errors/index.ts`
  - [ ] 3.14 Write unit tests for all agents and tools with >80% coverage

- [ ] 4.0 Refactor API Endpoints and Orchestration
  - [ ] 4.1 Refactor main chat endpoint to use Vercel AI SDK's streamText in `frontend/app/api/chat/route.ts`
  - [ ] 4.2 Implement agent selection logic based on user intent in the chat endpoint
  - [ ] 4.3 Register all migrated tools with the Vercel AI SDK in the chat endpoint
  - [ ] 4.4 Create agent-specific API routes in `frontend/app/api/agents/[agent]/route.ts`
  - [ ] 4.5 Create direct tool invocation API routes in `frontend/app/api/tools/[tool]/route.ts`
  - [ ] 4.6 Create OAuth flow API routes in `frontend/app/api/oauth/[provider]/route.ts`
  - [ ] 4.7 Implement proper error handling and response formatting for all API routes
  - [ ] 4.8 Add Clerk authentication protection to all API routes
  - [ ] 4.9 Test streaming compatibility with existing frontend chat interface
  - [ ] 4.10 Implement rate limiting using Convex functions in API routes

- [ ] 5.0 Update Frontend Integration and Testing
  - [ ] 5.1 Update chat interface to handle new Vercel AI SDK streaming format in `frontend/app/chat/page.tsx`
  - [ ] 5.2 Update login form to use Clerk components in `frontend/components/login-form.tsx`
  - [ ] 5.3 Update signup form to use Clerk components in `frontend/components/signup-form.tsx`
  - [ ] 5.4 Update user navigation with Clerk user management in `frontend/components/nav-user.tsx`
  - [ ] 5.5 Update agent plan component for new agent response format in `frontend/components/ui/agent-plan.tsx`
  - [ ] 5.6 Update workflow sidebar for new agent structure in `frontend/components/ui/workflow-sidebar.tsx`
  - [ ] 5.7 Update OAuth integration card to work with Convex storage in `frontend/components/oauth-integration-card.tsx`
  - [ ] 5.8 Create comprehensive end-to-end tests for all agent workflows
  - [ ] 5.9 Create integration tests for all external tool connections
  - [ ] 5.10 Perform load testing to ensure performance meets requirements (TTFB < 200ms, streaming < 100ms)
  - [ ] 5.11 Set up monitoring and error tracking with Vercel's observability tools
  - [ ] 5.12 Create migration scripts for existing OAuth tokens from Python backend to Convex
  - [ ] 5.13 Implement feature flags for gradual rollout and rollback capability
  - [ ] 5.14 Document the new architecture and update developer documentation 