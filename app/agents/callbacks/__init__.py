"""
Callbacks module for PipeWise agents.

Provides handoff callbacks and communication tracking between agents.
"""

from .handoff import create_handoff_callback, HandoffData

__all__ = [
    "create_handoff_callback",
    "HandoffData",
]
