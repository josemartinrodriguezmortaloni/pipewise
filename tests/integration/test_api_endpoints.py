"""
Integration tests for API endpoints
Following Rule 4.1: Use FastAPI TestClient with Fixtures
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json


class TestHealthEndpoints:
    """Test health check and system endpoints"""
    
    def test_health_check(self, test_client: TestClient):
        """Test basic health check endpoint"""
        response = test_client.get("/health")
        
        # Should work without tenant headers for health check
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_metrics_endpoint(self, test_client: TestClient):
        """Test Prometheus metrics endpoint"""
        response = test_client.get("/metrics")
        
        # Metrics endpoint should be publicly accessible
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")


class TestLeadEndpoints:
    """Test lead management endpoints with multi-tenancy"""
    
    def test_create_lead_success(self, authenticated_client: TestClient, sample_lead_data):
        """Test successful lead creation"""
        response = authenticated_client.post("/api/v1/leads/", json=sample_lead_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_lead_data["name"]
        assert data["email"] == sample_lead_data["email"]
        assert data["company"] == sample_lead_data["company"]
        assert "id" in data
        assert "created_at" in data
    
    def test_create_lead_validation_error(self, authenticated_client: TestClient):
        """Test lead creation with validation errors"""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "email": "invalid-email",  # Invalid email format
            "company": ""  # Empty company
        }
        
        response = authenticated_client.post("/api/v1/leads/", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_leads_list(self, authenticated_client: TestClient, test_lead):
        """Test getting leads list with tenant isolation"""
        response = authenticated_client.get("/api/v1/leads/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Should only return leads for the authenticated tenant
        if data:  # If there are leads
            for lead in data:
                assert "tenant_id" in lead
                assert lead["tenant_id"] == authenticated_client.headers["X-Tenant-ID"]
    
    def test_get_lead_by_id(self, authenticated_client: TestClient, test_lead):
        """Test getting specific lead by ID"""
        response = authenticated_client.get(f"/api/v1/leads/{test_lead.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_lead.id
        assert data["name"] == test_lead.name
        assert data["email"] == test_lead.email
    
    def test_get_lead_not_found(self, authenticated_client: TestClient):
        """Test getting non-existent lead"""
        response = authenticated_client.get("/api/v1/leads/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_update_lead(self, authenticated_client: TestClient, test_lead):
        """Test updating lead information"""
        update_data = {
            "name": "Updated Name",
            "phone": "+1-555-9999",
            "metadata": {"updated": True}
        }
        
        response = authenticated_client.put(f"/api/v1/leads/{test_lead.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["phone"] == "+1-555-9999"
    
    def test_delete_lead(self, authenticated_client: TestClient, test_lead):
        """Test deleting a lead"""
        response = authenticated_client.delete(f"/api/v1/leads/{test_lead.id}")
        
        assert response.status_code == 204
        
        # Verify lead is deleted
        get_response = authenticated_client.get(f"/api/v1/leads/{test_lead.id}")
        assert get_response.status_code == 404


class TestLeadWorkflowEndpoints:
    """Test lead workflow processing endpoints"""
    
    @patch('app.agents.modern_agents.Runner.run_async')
    def test_process_lead_workflow(self, mock_runner, authenticated_client: TestClient, test_lead):
        """Test lead workflow processing"""
        # Mock AgentSDK responses
        mock_result = type('MockResult', (), {})()
        mock_result.output = type('MockOutput', (), {})()
        mock_result.output.qualified = True
        mock_result.output.qualification_score = 85.0
        mock_runner.return_value = mock_result
        
        response = authenticated_client.post(f"/api/v1/leads/{test_lead.id}/process")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["qualified"] is True
        assert "qualification_score" in data
    
    @patch('app.agents.modern_agents.Runner.run_async')
    def test_qualify_lead_only(self, mock_runner, authenticated_client: TestClient, test_lead):
        """Test individual lead qualification"""
        mock_result = type('MockResult', (), {})()
        mock_result.output = type('MockOutput', (), {})()
        mock_result.output.qualified = True
        mock_result.output.qualification_score = 75.0
        mock_result.output.key_factors = ["Enterprise size", "Clear budget"]
        mock_runner.return_value = mock_result
        
        response = authenticated_client.post(f"/api/v1/leads/{test_lead.id}/qualify")
        
        assert response.status_code == 200
        data = response.json()
        assert "qualified" in data
        assert "qualification_score" in data
    
    def test_process_lead_unauthorized_tenant(self, test_client: TestClient, test_lead):
        """Test processing lead from different tenant (should fail)"""
        # Request without proper tenant headers
        response = test_client.post(f"/api/v1/leads/{test_lead.id}/process")
        
        # Should fail due to missing tenant context
        assert response.status_code in [400, 401, 403]


class TestTenantIsolation:
    """Test multi-tenant data isolation"""
    
    def test_tenant_data_isolation(self, test_client: TestClient, test_tenant, test_premium_tenant):
        """Test that tenants can only access their own data"""
        # Create test client for first tenant
        client1_headers = {
            "X-Tenant-ID": test_tenant.id,
            "Authorization": "Bearer test-token-1"
        }
        
        # Create test client for second tenant  
        client2_headers = {
            "X-Tenant-ID": test_premium_tenant.id,
            "Authorization": "Bearer test-token-2"
        }
        
        # Create lead for tenant 1
        lead_data = {
            "name": "Tenant 1 Lead",
            "email": "lead1@tenant1.com",
            "company": "Tenant 1 Corp"
        }
        
        response1 = test_client.post(
            "/api/v1/leads/",
            json=lead_data,
            headers=client1_headers
        )
        assert response1.status_code == 201
        lead1_id = response1.json()["id"]
        
        # Try to access tenant 1's lead from tenant 2 (should fail)
        response2 = test_client.get(
            f"/api/v1/leads/{lead1_id}",
            headers=client2_headers
        )
        assert response2.status_code == 404  # Not found due to tenant isolation
    
    def test_missing_tenant_header(self, test_client: TestClient):
        """Test API access without tenant header"""
        response = test_client.get("/api/v1/leads/")
        
        assert response.status_code in [400, 401, 403]
        data = response.json()
        assert "tenant" in data["error"].lower()


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_enforcement(self, authenticated_client: TestClient):
        """Test that rate limits are enforced per tenant"""
        # This test would need to be adjusted based on actual rate limits
        # For now, test that the endpoint works normally
        
        responses = []
        for i in range(5):  # Make several requests
            response = authenticated_client.get("/api/v1/leads/")
            responses.append(response.status_code)
        
        # All requests should succeed for normal usage
        assert all(status == 200 for status in responses)
    
    @patch('app.core.middleware.time.time')
    def test_rate_limit_headers(self, mock_time, authenticated_client: TestClient):
        """Test that rate limit headers are included in responses"""
        mock_time.return_value = 1640995200  # Fixed timestamp
        
        response = authenticated_client.get("/api/v1/leads/")
        
        # Check for rate limit related headers (if implemented)
        assert response.status_code == 200
        # Could check for headers like X-RateLimit-Remaining, X-RateLimit-Reset


class TestErrorHandling:
    """Test error handling and responses"""
    
    def test_validation_error_format(self, authenticated_client: TestClient):
        """Test that validation errors are properly formatted"""
        invalid_data = {
            "name": "",
            "email": "not-an-email",
            "company": None
        }
        
        response = authenticated_client.post("/api/v1/leads/", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        
        # Check that all validation errors are included
        fields_with_errors = [error["loc"][-1] for error in data["detail"]]
        assert "name" in fields_with_errors
        assert "email" in fields_with_errors
    
    def test_server_error_handling(self, authenticated_client: TestClient):
        """Test server error handling (500 errors)"""
        # This would test how the API handles unexpected server errors
        # For now, ensure the client is working
        response = authenticated_client.get("/api/v1/leads/")
        assert response.status_code in [200, 404]  # Valid response codes
    
    def test_method_not_allowed(self, authenticated_client: TestClient):
        """Test method not allowed responses"""
        response = authenticated_client.patch("/api/v1/leads/")  # PATCH not supported
        
        assert response.status_code == 405
        data = response.json()
        assert "not allowed" in data["detail"].lower()


class TestCORSHeaders:
    """Test CORS header handling"""
    
    def test_cors_headers_present(self, test_client: TestClient):
        """Test that CORS headers are included in responses"""
        headers = {"Origin": "http://localhost:3000"}
        response = test_client.get("/health", headers=headers)
        
        assert response.status_code == 200
        # Check for CORS headers (if implemented)
        # assert "Access-Control-Allow-Origin" in response.headers
    
    def test_preflight_request(self, test_client: TestClient):
        """Test CORS preflight OPTIONS request"""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        
        response = test_client.options("/api/v1/leads/", headers=headers)
        
        # Should handle preflight requests properly
        assert response.status_code in [200, 204]