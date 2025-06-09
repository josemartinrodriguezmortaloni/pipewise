"""
Unit tests for multi-tenant dependencies
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import (
    TenantSecurityContext,
    TenantService,
    get_tenant_from_header,
    get_current_security_context,
    require_permission,
    require_feature
)
from app.models.tenant import Tenant
from app.models.user import User, Role


class TestTenantSecurityContext:
    """Test TenantSecurityContext functionality"""
    
    def test_initialization(self, test_user, test_tenant):
        """Test security context initialization"""
        permissions = ["admin", "lead:read", "lead:write"]
        context = TenantSecurityContext(test_user, test_tenant, permissions)
        
        assert context.user == test_user
        assert context.tenant == test_tenant
        assert context.permissions == permissions
    
    def test_has_permission_admin(self, test_user, test_tenant):
        """Test admin permission check"""
        permissions = ["admin"]
        context = TenantSecurityContext(test_user, test_tenant, permissions)
        
        assert context.has_permission("admin") is True
        assert context.has_permission("any_permission") is True  # Admin has all permissions
    
    def test_has_permission_specific(self, test_user, test_tenant):
        """Test specific permission check"""
        permissions = ["lead:read", "user:read"]
        context = TenantSecurityContext(test_user, test_tenant, permissions)
        
        assert context.has_permission("lead:read") is True
        assert context.has_permission("user:read") is True
        assert context.has_permission("lead:write") is False
    
    def test_has_feature_enabled(self, test_user, test_tenant):
        """Test feature availability check"""
        test_tenant.features_enabled = ["analytics", "custom_integrations"]
        context = TenantSecurityContext(test_user, test_tenant, [])
        
        assert context.has_feature("analytics") is True
        assert context.has_feature("custom_integrations") is True
        assert context.has_feature("premium_support") is False
    
    def test_get_api_limit(self, test_user, test_tenant):
        """Test API limit retrieval"""
        test_tenant.api_limits = {"requests_per_minute": 100, "users_count": 5}
        context = TenantSecurityContext(test_user, test_tenant, [])
        
        assert context.get_api_limit("requests_per_minute") == 100
        assert context.get_api_limit("users_count") == 5
        assert context.get_api_limit("nonexistent") is None


class TestTenantService:
    """Test TenantService functionality"""
    
    @pytest.mark.asyncio
    async def test_get_tenant_data(self, test_tenant):
        """Test tenant data retrieval with filtering"""
        mock_db = Mock(spec=Session)
        service = TenantService(mock_db, test_tenant)
        
        # Mock model class and query
        mock_model = Mock()
        mock_model.tenant_id = test_tenant.id
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_model]
        mock_db.query.return_value = mock_query
        
        # Test without filters
        result = await service.get_tenant_data(mock_model)
        
        mock_db.query.assert_called_once_with(mock_model)
        mock_query.filter.assert_called()
        assert result == [mock_model]
    
    @pytest.mark.asyncio
    async def test_create_tenant_data(self, test_tenant):
        """Test tenant data creation"""
        mock_db = Mock(spec=Session)
        service = TenantService(mock_db, test_tenant)
        
        data_dict = {"name": "Test Item", "description": "Test description"}
        mock_model = Mock()
        
        result = await service.create_tenant_data(mock_model, data_dict)
        
        # Verify tenant_id was added
        assert data_dict["tenant_id"] == test_tenant.id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestDependencyFunctions:
    """Test dependency injection functions"""
    
    @pytest.mark.asyncio
    async def test_get_tenant_from_header_success(self, test_tenant):
        """Test successful tenant retrieval from header"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = test_tenant
        mock_db.query.return_value = mock_query
        
        result = await get_tenant_from_header(test_tenant.id, mock_db)
        
        assert result == test_tenant
        mock_db.query.assert_called_once_with(Tenant)
    
    @pytest.mark.asyncio
    async def test_get_tenant_from_header_not_found(self):
        """Test tenant not found scenario"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_from_header("nonexistent-tenant", mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Tenant not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_tenant_from_header_inactive(self, test_tenant):
        """Test inactive tenant scenario"""
        test_tenant.is_active = False
        
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = test_tenant
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_from_header(test_tenant.id, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Tenant is inactive" in exc_info.value.detail


class TestPermissionDecorators:
    """Test permission and feature requirement decorators"""
    
    def test_require_permission_success(self, test_user, test_tenant):
        """Test successful permission check"""
        context = TenantSecurityContext(test_user, test_tenant, ["admin"])
        
        dependency = require_permission("admin")
        result = dependency(context)
        
        assert result == context
    
    def test_require_permission_failure(self, test_user, test_tenant):
        """Test failed permission check"""
        context = TenantSecurityContext(test_user, test_tenant, ["user:read"])
        
        dependency = require_permission("admin")
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(context)
        
        assert exc_info.value.status_code == 403
        assert "Permission 'admin' required" in exc_info.value.detail
    
    def test_require_feature_success(self, test_user, test_tenant):
        """Test successful feature check"""
        test_tenant.features_enabled = ["analytics"]
        context = TenantSecurityContext(test_user, test_tenant, [])
        
        dependency = require_feature("analytics")
        result = dependency(context)
        
        assert result == context
    
    def test_require_feature_failure(self, test_user, test_tenant):
        """Test failed feature check"""
        test_tenant.features_enabled = ["basic_crm"]
        context = TenantSecurityContext(test_user, test_tenant, [])
        
        dependency = require_feature("premium_analytics")
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(context)
        
        assert exc_info.value.status_code == 403
        assert "Feature 'premium_analytics' not available" in exc_info.value.detail


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    @patch('app.core.dependencies.get_redis_client')
    async def test_check_rate_limit_success(self, mock_redis):
        """Test successful rate limit check"""
        from app.core.dependencies import check_rate_limit
        
        # Mock Redis client
        mock_redis_instance = Mock()
        mock_redis_instance.incr.return_value = 5  # Under limit
        mock_redis.return_value = mock_redis_instance
        
        # Mock security context
        mock_context = Mock()
        mock_context.tenant.id = "test-tenant"
        mock_context.get_api_limit.return_value = None
        
        result = await check_rate_limit("api_calls", 100, mock_context)
        
        assert result == 5
        mock_redis_instance.incr.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.core.dependencies.get_redis_client')
    async def test_check_rate_limit_exceeded(self, mock_redis):
        """Test rate limit exceeded scenario"""
        from app.core.dependencies import check_rate_limit
        
        # Mock Redis client
        mock_redis_instance = Mock()
        mock_redis_instance.incr.return_value = 150  # Over limit
        mock_redis.return_value = mock_redis_instance
        
        # Mock security context
        mock_context = Mock()
        mock_context.tenant.id = "test-tenant"
        mock_context.get_api_limit.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit("api_calls", 100, mock_context)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail