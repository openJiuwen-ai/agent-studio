from datetime import datetime, timezone
from typing import Optional


class Reporter:
    """
    A class for tracking and reporting steps in a process.
    
    Attributes:
        steps (list): List of recorded steps
    """
    
    def __init__(self):
        """
        Initialize the Reporter.
        """        
        self.steps = []
    
    def add_step(self, step_name: str, is_success: bool, error: str = "") -> None:
        """
        Add a step to the report.

        Args:
            step_name: Name/description of the step
            is_success: Whether the step succeeded
            error: Error message (used only if is_success is False)
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        step_info = {
            'timestamp': timestamp,
            'step_name': step_name,
            'success': is_success,
            'error': error if not is_success else ""
        }
        
        self.steps.append(step_info)

    def log_trace(self):
        result = []
        for entry in self.steps:
            step_name = entry.get("step_name", "")
            success = entry.get("success", False)
            error = entry.get("error", "")

            status = "success" if success else "failed"
            formatted = f"{step_name} [{status}]: {error}"

            result.append(formatted)

        return result