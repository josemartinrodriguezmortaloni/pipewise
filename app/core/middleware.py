"""
Middleware for multi-tenant request handling
Following Rule 3.1: Data Isolation by Tenant ID
"""

from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import logging
import time
import uuid
from prometheus_client import Counter, Histogram

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Metrics for monitoring
REQUEST_COUNT = Counter(
    'pipewise_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status', 'tenant_id']
)

REQUEST_DURATION = Histogram(
    'pipewise_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'tenant_id']
)


class TenantMiddleware:
    """
    Middleware for tenant context injection and validation
    Following Rule 3.1: Data Isolation by Tenant ID
    """
    
    def __init__(self, app):
        self.app = app
        self.settings = get_settings()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Skip tenant validation for health check and public endpoints
        if self._is_public_endpoint(request.url.path):
            response = await call_next(request)
            return response
        
        try:
            # Extract tenant information
            tenant_id = self._extract_tenant_id(request)
            
            if not tenant_id:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Missing tenant identification"}
                )
            
            # Validate tenant
            is_valid = await self._validate_tenant(tenant_id, request)
            if not is_valid:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Invalid or inactive tenant"}
                )
            
            # Inject tenant context into request state
            request.state.tenant_id = tenant_id
            request.state.tenant_subdomain = self._extract_subdomain(request)
            
            # Add request ID for tracing
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            # Process request
            response = await call_next(request)
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Tenant-ID"] = tenant_id
            
            # Record metrics
            self._record_metrics(request, response, start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"}
            )
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require tenant validation"""
        public_paths = [
            "/health",
            "/metrics", 
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/static/",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/forgot-password",
            "/api/v1/public/"
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    def _extract_tenant_id(self, request: Request) -> str:
        """
        Extract tenant ID from request
        Supports multiple methods: header, subdomain, query parameter
        """
        # Method 1: X-Tenant-ID header (preferred for API calls)
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Method 2: Subdomain extraction (for web UI)
        subdomain = self._extract_subdomain(request)
        if subdomain and subdomain != "www" and subdomain != "api":
            return subdomain
        
        # Method 3: Query parameter (fallback)
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        return None
    
    def _extract_subdomain(self, request: Request) -> str:
        """Extract subdomain from request host"""
        host = request.headers.get("host", "")
        
        # Handle localhost and IP addresses in development
        if host.startswith("localhost") or host.replace(".", "").isdigit():
            return None
        
        # Extract subdomain
        parts = host.split(".")
        if len(parts) >= 3:  # subdomain.domain.com
            return parts[0]
        
        return None
    
    async def _validate_tenant(self, tenant_id: str, request: Request) -> bool:
        """
        Validate tenant exists and is active
        In production, this would query the database
        """
        # TODO: Implement actual tenant validation from database
        # For now, accept any non-empty tenant_id
        if not tenant_id or len(tenant_id) < 1:
            return False
        
        # Add basic validation rules
        if not tenant_id.replace("-", "").replace("_", "").isalnum():
            return False
        
        return True
    
    def _record_metrics(self, request: Request, response: Response, start_time: float):
        """Record Prometheus metrics for the request"""
        try:
            duration = time.time() - start_time
            tenant_id = getattr(request.state, 'tenant_id', 'unknown')
            
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                tenant_id=tenant_id
            ).inc()
            
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path,
                tenant_id=tenant_id
            ).observe(duration)
            
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")


class RateLimitMiddleware:
    """
    Rate limiting middleware per tenant
    Following Rule 3.2: Shared Resource Pool with Limits
    """
    
    def __init__(self, app):
        self.app = app
        self.settings = get_settings()
        # In production, use Redis for distributed rate limiting
        self.rate_limit_store = {}  # Simple in-memory store for development
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        tenant_id = getattr(request.state, 'tenant_id', None)
        if not tenant_id:
            return await call_next(request)
        
        # Check rate limit
        is_allowed = await self._check_rate_limit(tenant_id, request)
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded"}
            )
        
        return await call_next(request)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public"""
        public_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        return any(path.startswith(public_path) for public_path in public_paths)
    
    async def _check_rate_limit(self, tenant_id: str, request: Request) -> bool:
        """
        Check if request is within rate limits
        In production, implement with Redis sliding window
        """
        # Simple implementation for development
        current_time = int(time.time())
        window_start = current_time - 60  # 1-minute window
        
        key = f"{tenant_id}:{current_time // 60}"  # Per-minute bucket
        
        if key not in self.rate_limit_store:
            self.rate_limit_store[key] = 0
        
        self.rate_limit_store[key] += 1
        
        # Clean old entries
        old_keys = [k for k in self.rate_limit_store.keys() 
                   if int(k.split(":")[1]) < window_start // 60]
        for old_key in old_keys:
            del self.rate_limit_store[old_key]
        
        # Check limit (default 100 requests per minute)
        limit = self.settings.RATE_LIMIT_PER_MINUTE
        return self.rate_limit_store[key] <= limit


class CORSMiddleware:
    """
    CORS middleware with tenant-aware origins
    """
    
    def __init__(self, app):
        self.app = app
        self.settings = get_settings()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, request)
            return response
        
        response = await call_next(request)
        self._add_cors_headers(response, request)
        return response
    
    def _add_cors_headers(self, response: Response, request: Request):
        """Add CORS headers to response"""
        origin = request.headers.get("origin")
        
        # Get allowed origins
        allowed_origins = self.settings.get_cors_origins()
        
        if "*" in allowed_origins or (origin and origin in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Tenant-ID, X-Request-ID"
        )
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Tenant-ID"
        response.headers["Access-Control-Allow-Credentials"] = "true"


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses
    """
    
    def __init__(self, app):
        self.app = app
        self.settings = get_settings()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        if not self.settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP header for web security
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            # Relaxed CSP for documentation
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'"
            )
        
        return response


class LoggingMiddleware:
    """
    Request/response logging middleware
    """
    
    def __init__(self, app):
        self.app = app
        self.settings = get_settings()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        tenant_id = getattr(request.state, 'tenant_id', 'unknown')
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "tenant_id": tenant_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "ip": request.client.host if request.client else None
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "tenant_id": tenant_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }
        )
        
        return response