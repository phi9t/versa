"""Versa: conversation state compiler."""

from importlib.metadata import PackageNotFoundError, version

from versa.models.state import TaskState
from versa.orchestrator import AgentRuntime

try:
    __version__ = version("versa")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["AgentRuntime", "TaskState", "__version__"]
