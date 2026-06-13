"""LLM exception module.

This module defines exceptions raised while registering, configuring,
or invoking LLM providers.
"""


class LLMDisabledError(RuntimeError):
    """Exception raised when trying to use a disabled LLM."""

    def __init__(self, name: str):
        """Initialize the exception.

        Args:
            name (str): Name of the disabled LLM.
        """
        super().__init__(f"LLM is disabled: {name}")
        self.name = name
