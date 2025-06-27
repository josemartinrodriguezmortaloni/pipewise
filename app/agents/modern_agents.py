"""
Modern Agent implementation wrapper for the ModernAgents class
This module provides the interface expected by the tests
"""

from typing import Dict, Any, Optional
from .agents import (
    ModernAgents as BaseModernAgents,
    ModernLeadProcessor,
    TenantContext,
    SupabaseCRMClient,
)

# Import Runner from agents SDK
try:
    from agents import Runner
except ImportError:
    # Fallback if agents module not available
    class MockRunner:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, *args, **kwargs):
            return type("MockResult", (), {"final_output": {}})()

    Runner = MockRunner

# Re-export the classes that tests expect
ModernAgents = BaseModernAgents
TenantContext = TenantContext

__all__ = [
    "ModernAgents",
    "TenantContext",
    "ModernLeadProcessor",
    "Runner",
    "SupabaseCRMClient",
]
