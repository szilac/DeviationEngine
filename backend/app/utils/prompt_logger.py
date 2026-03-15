"""
Prompt logging utility for debugging agent prompts.

When DEBUG_AGENT_PROMPTS=true, saves the exact prompts sent to LLMs
to individual files for analysis.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def save_agent_prompt(
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    model_info: Optional[Dict[str, Any]] = None,
    context_info: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save agent prompt to file for debugging.

    Creates/overwrites a file at: backend/data/agent_prompts/{agent_name}_latest.txt

    Args:
        agent_name: Name of the agent (e.g., 'historian', 'skeleton')
        system_prompt: The system prompt/instructions
        user_prompt: The user prompt with input data
        model_info: Optional dict with model provider and name
        context_info: Optional dict with RAG/context information
        metadata: Optional dict with timeline_id, generation_id, etc.
    """
    # Check if debug mode is enabled
    if not os.getenv("DEBUG_AGENT_PROMPTS", "false").lower() == "true":
        return

    try:
        # Create directory if it doesn't exist
        prompts_dir = Path(__file__).parent.parent.parent / "data" / "agent_prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # Create filename
        filename = prompts_dir / f"{agent_name}_latest.txt"

        # Build content
        content_parts = [
            "=" * 80,
            f"AGENT: {agent_name}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            ""
        ]

        # Add model info
        if model_info:
            content_parts.append("=== MODEL INFO ===")
            content_parts.append(f"Provider: {model_info.get('provider', 'unknown')}")
            content_parts.append(f"Model: {model_info.get('model', 'unknown')}")
            content_parts.append("")

        # Add metadata
        if metadata:
            content_parts.append("=== METADATA ===")
            for key, value in metadata.items():
                content_parts.append(f"{key}: {value}")
            content_parts.append("")

        # Add context info (RAG stats)
        if context_info:
            content_parts.append("=== CONTEXT INFO ===")
            content_parts.append(f"Source: {context_info.get('source', 'unknown')}")
            if 'chunks' in context_info:
                content_parts.append(f"Chunks: {context_info['chunks']}")
            if 'tokens' in context_info:
                content_parts.append(f"Tokens: ~{context_info['tokens']}")
            content_parts.append("")

        # Add system prompt
        content_parts.append("=== SYSTEM PROMPT ===")
        content_parts.append(system_prompt)
        content_parts.append("")

        # Add user prompt
        content_parts.append("=== USER PROMPT ===")
        content_parts.append(user_prompt)
        content_parts.append("")

        content_parts.append("=" * 80)
        content_parts.append("END OF PROMPT")
        content_parts.append("=" * 80)

        # Write to file (overwrite)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(content_parts))

        logger.info(f"Saved {agent_name} prompt to {filename}")

    except Exception as e:
        logger.error(f"Failed to save prompt for {agent_name}: {e}")


def is_prompt_logging_enabled() -> bool:
    """Check if prompt logging is enabled."""
    return os.getenv("DEBUG_AGENT_PROMPTS", "false").lower() == "true"
