"""
Jinja2 template loader for agent prompts.

This module provides a centralized service for loading and rendering
agent prompt templates with support for conditional logic based on
scenario types and other parameters.
"""

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PromptTemplateLoader:
    """
    Manages loading and rendering of Jinja2 prompt templates.

    This class provides a singleton interface for rendering agent prompts
    from Jinja2 template files with proper error handling and logging.
    """

    _instance: 'PromptTemplateLoader | None' = None

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Jinja2 environment."""
        if not hasattr(self, '_initialized'):
            # Get the template directory path (same directory as this file)
            self.template_dir = Path(__file__).parent

            # Create Jinja2 environment
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                trim_blocks=True,          # Remove first newline after template tag
                lstrip_blocks=True,        # Strip leading spaces/tabs from line
                keep_trailing_newline=True # Keep final newline in template
            )

            self._initialized = True
            logger.info(f"PromptTemplateLoader initialized with template dir: {self.template_dir}")

    def render(
        self,
        template_path: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a Jinja2 template with the given context.

        Args:
            template_path: Path to template relative to prompt_templates/
                          Example: "historian/system_main.jinja2"
            context: Dictionary of variables to pass to the template

        Returns:
            Rendered prompt string

        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateError: If template rendering fails

        Example:
            >>> loader = PromptTemplateLoader()
            >>> prompt = loader.render(
            ...     "historian/system_main.jinja2",
            ...     {"scenario_type": "local_deviation"}
            ... )
        """
        try:
            template = self.env.get_template(template_path)
            rendered = template.render(**context)

            logger.debug(
                f"Rendered template '{template_path}' - Length: {len(rendered)} chars",
                extra={
                    "template_path": template_path,
                    "context_keys": list(context.keys()),
                    "output_length": len(rendered)
                }
            )

            return rendered

        except TemplateNotFound as e:
            logger.error(
                f"Template not found: '{template_path}'",
                extra={"template_path": template_path}
            )
            raise TemplateNotFound(f"Template '{template_path}' not found in {self.template_dir}")

        except TemplateError as e:
            logger.error(
                f"Template rendering error in '{template_path}': {e}",
                exc_info=True,
                extra={
                    "template_path": template_path,
                    "error": str(e)
                }
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error rendering template '{template_path}': {e}",
                exc_info=True
            )
            raise


# Global singleton instance
_loader_instance: PromptTemplateLoader | None = None


def get_template_loader() -> PromptTemplateLoader:
    """
    Get the global PromptTemplateLoader instance.

    Returns:
        Singleton instance of PromptTemplateLoader
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = PromptTemplateLoader()
    return _loader_instance


def render_prompt(template_path: str, **kwargs) -> str:
    """
    Convenience function for rendering prompts.

    Args:
        template_path: Path to template relative to prompt_templates/
        **kwargs: Template variables

    Returns:
        Rendered prompt string

    Example:
        >>> prompt = render_prompt(
        ...     "historian/system_main.jinja2",
        ...     scenario_type="local_deviation"
        ... )
    """
    loader = get_template_loader()
    return loader.render(template_path, kwargs)
