"""Tool exception module.

This module defines exceptions raised while registering or invoking tools.
"""


class ToolAlreadyRegisteredError(ValueError):
    """Exception raised when registering a tool whose name already exists."""

    def __init__(self, name: str):
        """Initialize the exception.

        Args:
            name (str): Name of the tool that is already registered.
        """
        super().__init__(f"Tool already registered: {name}")
        self.name = name
