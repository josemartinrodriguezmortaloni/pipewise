
# PRD: Backend Migration to Next.js, Vercel AI SDK, and Convex

## 1. Introduction & Overview

This document outlines the requirements for migrating the existing Python-based backend to a unified, serverless architecture within the Next.js application. The current system relies on a separate FastAPI service with a complex MCP (Mission Control Post) system for managing external service integrations, which complicates the development workflow and hosting environment.

The goal is to replace the Python backend entirely by leveraging Next.js API Routes, using the Vercel AI SDK for intelligent agent orchestration, Convex for real-time data and agent memory, and Clerk for robust user authentication. This migration will create a more scalable, maintainable, and modern monolithic application that aligns with the existing frontend structure documented in `frontend-structure.mdc`.

### Current Architecture Overview
- **Backend:** Python FastAPI with MCP system for resilient external service connections
- **Frontend:** Next.js 15 with App Router, TypeScript, Tailwind CSS, and Shadcn/UI
- **Database:** Supabase for user and lead data
- **Authentication:** Supabase Auth (to be replaced with Clerk)
- **External Services:** Pipedream for tool execution

## 2. Goals

- **Unify Tech Stack:** Consolidate the backend and frontend into a single Next.js codebase, eliminating the need for a separate Python service.
- **Modernize Architecture:** Adopt a serverless-first approach using Vercel for hosting, Convex for the database, and the Vercel AI SDK for core AI functionality.
- **Enhance Scalability & Performance:** Leverage serverless functions and a real-time database to build a highly scalable and performant system.
- **Improve Developer Experience:** Simplify the development process, CI/CD pipeline, and debugging with a single, cohesive codebase.
- **Maintain Feature Parity:** Ensure all existing agent capabilities and integrations continue to function seamlessly.

## 3. User Stories

- **As a developer,** I want to manage a single Next.js project for both frontend and backend to streamline development, reduce context-switching, and simplify deployments.
- **As a user,** I want to authenticate securely using a trusted service like Clerk and interact seamlessly with AI agents to accomplish my tasks, experiencing a fast and responsive interface.
- **As a system administrator,** I want to ensure the application is scalable and resilient, with distinct data stores for user data (Supabase) and volatile agent data (Convex) to optimize performance and security.
- **As a business owner,** I want to reduce infrastructure complexity and costs by eliminating the need for a separate Python backend service.

## 4. Functional Requirements

### FR1: Project Scaffolding & Setup
- Initialize Convex within the existing Next.js project in the `frontend/` directory using the Convex CLI.
- Integrate the Clerk Next.js SDK into the application.
- Configure environment variables for all services (Convex, Clerk, Supabase, and third-party tool APIs).
- Update `frontend/package.json` with new dependencies.
- Create Convex configuration files in `frontend/convex/`.

### FR2: Authentication Migration (Supabase → Clerk)
- Replace the existing Supabase Auth implementation with Clerk.
- Update `frontend/hooks/use-auth.tsx` to use Clerk's hooks and providers.
- Implement Clerk's pre-built components in:
  - `frontend/components/login-form.tsx`
  - `frontend/components/signup-form.tsx`
  - `frontend/components/nav-user.tsx`
- Create a new `frontend/middleware.ts` file for route protection using Clerk.
- Update `frontend/app/layout.tsx` to wrap the app with `<ClerkProvider>`.
- Migrate user sessions from Supabase to Clerk, ensuring user IDs are mapped correctly.

### FR3: Database Strategy (Hybrid Approach)
- **Convex (Agent Data):**
  - Create schema files in `frontend/convex/schema.ts` for:
    - **agent_memories:** Store conversation history, context, and state per agent per user
    - **rate_limits:** Track API usage and enforce limits per user
    - **oauth_tokens:** Securely store OAuth tokens for third-party services
    - **agent_handoffs:** Manage agent-to-agent communication state
  - Implement Convex functions (queries, mutations, actions) in `frontend/convex/`.
  
- **Supabase (User & Lead Data):**
  - Maintain existing Supabase connection for user and lead data.
  - Update `frontend/lib/supabase.ts` to work alongside Clerk authentication.
  - Create server-side utilities in `frontend/lib/supabase-admin.ts` for backend operations.

### FR4: Agent & Tool Logic Migration
- **Agent Migration Structure:**
  - Create `frontend/lib/ai/agents/` directory for agent implementations:
    - `coordinator.ts` - Coordinator Agent logic
    - `meeting-scheduler.ts` - Meeting Scheduler Agent logic
    - `lead-administrator.ts` - Lead Administrator Agent logic
    - `base-agent.ts` - Base agent class with common functionality
  
- **Tool Migration:** Create TypeScript implementations in `frontend/lib/ai/tools/`:
  - **Communication Tools:**
    - `sendgrid.ts` - Email sending via SendGrid
    - `twitter.ts` - Twitter/X API integration
  - **Calendar Tools:**
    - `google-calendar.ts` - Google Calendar operations
    - `calendly.ts` - Calendly scheduling
  - **CRM Tools:**
    - `salesforce.ts` - Salesforce CRM operations
    - `pipedrive.ts` - Pipedrive CRM operations
    - `zoho-crm.ts` - Zoho CRM operations
  
- **MCP System Replacement:**
  - Implement resilience patterns (circuit breakers, retries) using TypeScript decorators
  - Create `frontend/lib/ai/tools/base-tool.ts` with error handling and retry logic
  - Port health monitoring to Vercel's observability tools

### FR5: API Endpoint Refactoring
- **Main Chat Endpoint (`frontend/app/api/chat/route.ts`):**
  - Refactor to use Vercel AI SDK's `streamText` function
  - Implement agent selection logic based on user intent
  - Add tool registration for all migrated tools
  - Maintain streaming response compatibility with existing frontend
  
- **Supporting API Routes:**
  - Create `frontend/app/api/agents/[agent]/route.ts` for agent-specific operations
  - Create `frontend/app/api/tools/[tool]/route.ts` for direct tool invocation
  - Create `frontend/app/api/oauth/[provider]/route.ts` for OAuth flows

### FR6: Frontend Integration Updates
- **Chat Interface (`frontend/app/chat/page.tsx`):**
  - Update to handle new streaming format from Vercel AI SDK
  - Integrate with new agent response structures
  - Add Clerk user context to chat messages
  
- **UI Components Updates:**
  - Update `frontend/components/ui/agent-plan.tsx` for new agent plan format
  - Update `frontend/components/ui/workflow-sidebar.tsx` for new workflow structure
  - Ensure `frontend/components/oauth-integration-card.tsx` works with new OAuth storage

### FR7: OAuth Token Management
- Migrate OAuth token storage from Python backend to Convex
- Create secure token encryption/decryption utilities
- Implement token refresh logic in TypeScript
- Update integration settings UI to work with new token storage

### FR8: Error Handling & Monitoring
- Implement comprehensive error handling matching Python MCP system capabilities
- Create custom error classes in `frontend/lib/errors/`
- Set up error tracking with Vercel's monitoring tools
- Implement user-friendly error messages in multiple languages

## 5. Non-Goals (Out of Scope)

- **Full Data Migration:** User and lead data will remain in Supabase. Only agent-specific data moves to Convex.
- **Major UI Redesign:** The existing UI structure and components remain unchanged except for necessary authentication updates.
- **New Agent Features:** No new agent capabilities will be developed during migration.
- **Mobile App Development:** Focus remains on web application only.
- **Internationalization:** Multi-language support beyond existing error messages is out of scope.

## 6. Design Considerations

### Architecture Decisions
- **Monolithic Next.js App:** All backend logic moves into the Next.js application for simplified deployment
- **Hybrid Database:** Leveraging strengths of both Supabase (relational data) and Convex (real-time, document-based)
- **Tool Implementation:** Direct TypeScript implementation removes Pipedream dependency
- **Authentication:** Clerk provides better Next.js integration and pre-built components

### File Structure Alignment
The migration will follow the existing frontend structure:
- Agent logic in `frontend/lib/ai/agents/`
- Tool implementations in `frontend/lib/ai/tools/`
- API routes in `frontend/app/api/`
- Convex functions in `frontend/convex/`
- Shared utilities in `frontend/lib/`

## 7. Technical Considerations

- **Primary Stack:** Next.js 15 (App Router), Vercel AI SDK, Convex, Clerk, Supabase, TypeScript
- **Architecture Pattern:** Serverless functions with real-time subscriptions
- **Tool Implementation:** TypeScript functions compatible with Vercel AI SDK tool calling
- **State Management:** Convex for real-time state, React hooks for UI state
- **Error Handling:** Comprehensive error boundaries and graceful degradation
- **Performance:** Edge functions where applicable, proper caching strategies
- **Security:** OAuth tokens encrypted at rest, API routes protected by Clerk

### Migration Strategy
1. **Parallel Development:** New system developed alongside existing backend
2. **Feature Flags:** Gradual rollout using feature flags
3. **Rollback Plan:** Ability to switch back to Python backend if needed
4. **Data Sync:** Temporary sync between old and new systems during transition

## 8. Success Metrics

- **Functionality:** All existing agent features work identically in the new system
- **Performance:** 
  - API response times ≤ current system
  - Time to first byte (TTFB) < 200ms
  - Streaming latency < 100ms
- **Reliability:** 99.9% uptime for critical agent operations
- **Developer Experience:** 
  - Single `npm run dev` command to run entire application
  - Hot reload for all code changes
  - TypeScript coverage > 95%
- **Cost Reduction:** Infrastructure costs reduced by eliminating separate backend hosting
- **Testing:** 
  - Unit test coverage > 80%
  - E2E tests for all agent workflows
  - Integration tests for all external tools

## 9. Open Questions

1. **Token Migration Timeline:** When should we migrate existing OAuth tokens from the Python backend to Convex?
2. **Pipedream Deprecation:** Should we maintain Pipedream as a fallback during the transition period?
3. **User Communication:** How do we communicate the authentication change from Supabase to Clerk to existing users?
4. **Rate Limiting Strategy:** Should rate limits be enforced at the Vercel Edge or within Convex?
5. **Monitoring Tools:** Should we use Vercel's built-in monitoring or integrate a third-party solution?

## 10. Risks & Mitigation

### Technical Risks
- **Risk:** Complex agent logic may not translate well to TypeScript
  - **Mitigation:** Create comprehensive test suites before migration
  
- **Risk:** OAuth token migration could fail for some users
  - **Mitigation:** Implement fallback to re-authenticate affected users

### Business Risks
- **Risk:** Downtime during migration could affect users
  - **Mitigation:** Use blue-green deployment strategy

- **Risk:** Performance degradation in new architecture
  - **Mitigation:** Extensive load testing before full rollout

## 11. Timeline Estimation

Based on the scope and complexity:
- **Phase 1 (Foundation):** 1-2 weeks
- **Phase 2 (First Agent):** 2-3 weeks  
- **Phase 3 (Remaining Agents):** 3-4 weeks
- **Phase 4 (Testing & Rollout):** 1-2 weeks
- **Total Estimated Time:** 7-11 weeks

## 12. Dependencies

- Access to all third-party API credentials
- Clerk account setup and configuration
- Convex project creation and setup
- Updated environment variables
- Test accounts for all integrated services 