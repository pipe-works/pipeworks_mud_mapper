"""Ollama template service for loading and compiling prompt templates.

This module provides functions for working with Ollama templates - JSON files
that encode theme, voice, and constraint guidance for LLM room descriptions.

Template Operations
-------------------
- ``get_templates_directory()``: Get the templates directory path
- ``list_templates()``: List available templates for dropdown population
- ``load_template()``: Load and validate a single template
- ``compile_system_prompt()``: Convert template to system prompt string
- ``get_default_system_prompt()``: Get legacy hardcoded prompt for "Custom" mode

Template Location
-----------------
Templates are stored in ``data/ollama/templates/`` as JSON files with the
``.template.json`` extension. The directory is created automatically if missing.

Usage
-----
List available templates::

    >>> from pipeworks_mud_mapper.services import template_service
    >>> templates = template_service.list_templates()
    >>> print(templates)
    [{'label': 'Ledgerfall Goblin', 'value': 'ledgerfall_goblin'}, ...]

Load and compile a template::

    >>> template = template_service.load_template("ledgerfall_goblin")
    >>> system_prompt = template_service.compile_system_prompt(template)
    >>> print(system_prompt[:100])
    You are a Game Master describing a single room...

See Also
--------
- ``models/template.py``: Pydantic models for templates
- ``_working/ollama/``: Template architecture documentation
- ``callbacks/ollama_callbacks.py``: Callbacks that use templates
"""

import json
import logging
from pathlib import Path

from pipeworks_mud_mapper.models import OllamaTemplate

logger = logging.getLogger(__name__)

# =============================================================================
# Core Rules - Universal Craft of Constraint guidance
# =============================================================================

CORE_RULES = """
CARDINAL RULE: Describe only what is PRESENT and FELT in this room RIGHT NOW.

CRAFT OF CONSTRAINT - UNIVERSAL RULES
======================================

1. DO NOT NARRATE FUTURES
   - Do not describe distant places, paths leading elsewhere, or what lies beyond
   - Do not write: "To the north, a forest stretches away"
   - Instead write: "The air carries the scent of pine"

2. DO NOT DECIDE FOR THE PLAYER
   - Do not guarantee safety, danger, or outcomes
   - Do not imply required actions or tools
   - Do not explain puzzles, locks, or barriers
   - Do not add "you should" or "you need" or "you will need"

3. DO NOT EXPLAIN LOCKED THINGS
   - Describe locked doors/chests/paths by their current state only
   - Never write: "You need a key" or "This is locked because..."
   - Instead: "The handle turns a fraction before stopping. The mechanism inside refuses."

4. THRESHOLDS WHISPER, NOT SPEAK
   - Do not describe where exits lead
   - Describe what it feels like to stand before choice
   - Instead of "A market awaits to the east," write "East carries noise and haggling"

5. SILENCE IS LEGAL
   - Not every detail needs narration
   - Not every object needs description
   - Absence is a legitimate sensation

6. DESCRIBE THE THRESHOLD, NOT THE DESTINATION
   - You are describing where decisions begin, not where they end
   - The room exists in the present moment, not in possibility

BANNED PHRASES (never use these):
   "opens onto", "leads to", "beyond", "offering a glimpse",
   "into the unknown", "promise of", "ahead"
""".strip()

# =============================================================================
# Default System Prompt (for "Custom" mode)
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are a creative writer for a MUD (text-based adventure game). \
Write atmospheric, evocative room descriptions. Keep descriptions \
concise (2-3 sentences). Focus on sensory details and mood."""


# =============================================================================
# Directory Functions
# =============================================================================


def get_templates_directory() -> Path:
    """Get the templates directory path.

    Returns the path to ``data/ollama/templates/`` relative to the
    project root. Creates the directory if it doesn't exist.

    Returns
    -------
    Path
        Absolute path to the templates directory.

    Examples
    --------
    >>> templates_dir = get_templates_directory()
    >>> print(templates_dir)
    /path/to/project/data/ollama/templates
    """
    # Navigate from this file to project root, then to data/ollama/templates
    package_dir = Path(__file__).parent.parent.parent.parent
    templates_dir = package_dir / "data" / "ollama" / "templates"

    # Create directory if it doesn't exist
    templates_dir.mkdir(parents=True, exist_ok=True)

    return templates_dir


# =============================================================================
# Template Listing
# =============================================================================


def list_templates() -> list[dict]:
    """List available templates for dropdown population.

    Scans the templates directory for ``.template.json`` files and
    returns a list suitable for Dash dropdown options.

    Returns
    -------
    list[dict]
        List of dicts with 'label' (display name) and 'value' (template_id).
        Sorted alphabetically by label.

    Examples
    --------
    >>> templates = list_templates()
    >>> print(templates)
    [{'label': 'Ledgerfall Goblin', 'value': 'ledgerfall_goblin'}]
    """
    templates_dir = get_templates_directory()
    options = []

    for json_file in templates_dir.glob("*.template.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            # Extract just what we need for the dropdown
            template_name = data.get("template_name", json_file.stem)
            template_id = data.get("template_id", json_file.stem.replace(".template", ""))

            options.append({"label": template_name, "value": template_id})

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in template file {json_file}: {e}")
        except Exception as e:
            logger.warning(f"Error reading template file {json_file}: {e}")

    # Sort by label for consistent ordering
    options.sort(key=lambda x: x["label"])

    return options


# =============================================================================
# Template Loading
# =============================================================================


def load_template(template_id: str) -> OllamaTemplate | None:
    """Load and validate a template by its ID.

    Searches for a template file with matching template_id in the
    templates directory and validates it against the Pydantic model.

    Parameters
    ----------
    template_id : str
        The template identifier (e.g., "ledgerfall_goblin").

    Returns
    -------
    OllamaTemplate | None
        The validated template, or None if not found or invalid.

    Examples
    --------
    >>> template = load_template("ledgerfall_goblin")
    >>> if template:
    ...     print(template.template_name)
    Ledgerfall Goblin
    """
    templates_dir = get_templates_directory()

    for json_file in templates_dir.glob("*.template.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            # Check if this is the template we're looking for
            if data.get("template_id") == template_id:
                template: OllamaTemplate = OllamaTemplate.model_validate(data)
                return template

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in template file {json_file}: {e}")
        except Exception as e:
            logger.warning(f"Error loading template from {json_file}: {e}")

    logger.warning(f"Template not found: {template_id}")
    return None


# =============================================================================
# System Prompt Compilation
# =============================================================================


def compile_system_prompt(template: OllamaTemplate, target_words: int = 300) -> str:
    """Compile a template into a system prompt string.

    Combines the universal Core Rules with theme-specific guidance,
    voice settings, craft constraints, and examples to produce a
    comprehensive system prompt for the LLM.

    Parameters
    ----------
    template : OllamaTemplate
        The template to compile.
    target_words : int, optional
        Target word count for the generated description. The compiled
        prompt will include a range (approximately 67%-117% of target)
        to give the LLM flexibility. Default is 300.

    Returns
    -------
    str
        The compiled system prompt string.

    Examples
    --------
    >>> template = load_template("ledgerfall_goblin")
    >>> prompt = compile_system_prompt(template)
    >>> print(prompt[:50])
    You are a Game Master describing a single room...

    >>> # With custom word count
    >>> prompt = compile_system_prompt(template, target_words=150)
    >>> "100-175 words" in prompt
    True
    """
    # Build the prompt in sections - each section is a line or block of text
    # that will be joined with newlines at the end. Empty strings create
    # blank lines for visual separation in the compiled prompt.
    sections = []

    # =================================================================
    # SECTION 1: Header - Establishes the GM persona and world context
    # =================================================================
    sections.append(
        f"You are a Game Master describing a single room in an interactive fiction game "
        f"set in {template.theme.name}."
    )
    sections.append("")

    # =================================================================
    # SECTION 2: Core Rules - Universal Craft of Constraint guidance
    # These rules apply to ALL templates regardless of theme/voice
    # =================================================================
    sections.append(CORE_RULES)
    sections.append("")
    sections.append("---")
    sections.append("")

    # =================================================================
    # SECTION 3: Theme and Voice - Template-specific personality
    # =================================================================
    theme = template.theme
    voice = template.voice_guidance

    sections.append(f"{template.template_name.upper()} VOICE & TONE")
    sections.append("=" * len(f"{template.template_name.upper()} VOICE & TONE"))
    sections.append("")
    sections.append(f"Theme: {theme.name}")
    sections.append(f"Tone: {theme.tone}")
    if theme.era:
        sections.append(f"Era: {theme.era}")
    if theme.aesthetic:
        sections.append(f"Aesthetic: {theme.aesthetic}")
    sections.append("")
    sections.append(f"Voice: {voice.style}")
    sections.append(f"Register: {voice.voice_register}")
    sections.append("")

    # Keywords
    if voice.keyword_include:
        sections.append("Keywords to weave in when fitting (don't force them):")
        sections.append(f"- {', '.join(voice.keyword_include)}")
        sections.append("")

    if voice.keyword_exclude:
        sections.append("Keywords to avoid:")
        sections.append(f"- {', '.join(voice.keyword_exclude)}")
        sections.append("")

    sections.append("---")
    sections.append("")

    # =================================================================
    # SECTION 4: Craft Constraints - Theme-specific guidance for common
    # description challenges (multi-part spaces, locked things, etc.)
    # Only included if the template defines any constraints.
    # =================================================================
    craft = template.craft_constraints
    has_constraints = any(
        [
            craft.multi_part_spaces,
            craft.locked_things_approach,
            craft.silence_tone,
            craft.exit_hints,
        ]
    )

    if has_constraints:
        sections.append(f"SPECIAL GUIDANCE FOR {template.template_name.upper()}")
        sections.append("=" * len(f"SPECIAL GUIDANCE FOR {template.template_name.upper()}"))
        sections.append("")

        if craft.locked_things_approach:
            sections.append(f"LOCKED THINGS: {craft.locked_things_approach}")
            sections.append("")

        if craft.multi_part_spaces:
            sections.append(f"MULTI-PART SPACES: {craft.multi_part_spaces}")
            sections.append("")

        if craft.silence_tone:
            sections.append(f"SILENCE: {craft.silence_tone}")
            sections.append("")

        if craft.exit_hints:
            sections.append(f"EXITS: {craft.exit_hints}")
            sections.append("")

        sections.append("---")
        sections.append("")

    # =================================================================
    # SECTION 5: Examples - Good and bad examples in the template's voice
    # These help guide small LLMs (like gemma2:2b) by showing concrete
    # instances of what TO do and what NOT to do.
    # =================================================================
    examples = template.examples
    has_examples = any(
        [
            examples.good_crossroads,
            examples.bad_crossroads,
            examples.good_locked_thing,
            examples.bad_locked_thing,
            examples.good_multi_part,
            examples.bad_multi_part,
        ]
    )

    if has_examples:
        sections.append(f"EXAMPLES IN {template.template_name.upper()} VOICE")
        sections.append("=" * len(f"EXAMPLES IN {template.template_name.upper()} VOICE"))
        sections.append("")

        if examples.good_crossroads:
            sections.append("GOOD CROSSROADS:")
            sections.append(examples.good_crossroads)
            sections.append("")

        if examples.bad_crossroads:
            sections.append("BAD CROSSROADS (DO NOT DO THIS):")
            sections.append(examples.bad_crossroads)
            sections.append("")

        if examples.good_locked_thing:
            sections.append("GOOD LOCKED THING:")
            sections.append(examples.good_locked_thing)
            sections.append("")

        if examples.bad_locked_thing:
            sections.append("BAD LOCKED THING (DO NOT DO THIS):")
            sections.append(examples.bad_locked_thing)
            sections.append("")

        if examples.good_multi_part:
            sections.append("GOOD MULTI-PART SPACE:")
            sections.append(examples.good_multi_part)
            sections.append("")

        if examples.bad_multi_part:
            sections.append("BAD MULTI-PART SPACE (DO NOT DO THIS):")
            sections.append(examples.bad_multi_part)
            sections.append("")

        sections.append("---")
        sections.append("")

    # =================================================================
    # SECTION 6: Task Instructions - Final instructions for the LLM
    # Specifies word count, tense, perspective, and reinforces the
    # key constraints one more time for emphasis.
    # =================================================================
    sections.append("YOUR TASK")
    sections.append("=========")
    sections.append("")
    sections.append(
        "You will receive a User Prompt describing the scene and what the author wants."
    )
    sections.append("")
    sections.append(f"Write a room description for {template.theme.name.split(',')[0]}:")
    # Calculate word count range: approximately 67%-117% of target for flexibility
    words_low = int(target_words * 0.67)
    words_high = int(target_words * 1.17)
    sections.append(f"- {words_low}-{words_high} words (aim for ~{target_words})")
    sections.append("- Present tense, second person (you/your)")
    sections.append("- Sensory: focus on what you see, hear, smell, feel, taste")
    sections.append("- Atmospheric: capture the mood of the room")
    sections.append("- NO future narration, NO player decisions, NO lock explanations")
    sections.append("- Trust the framework above; it's there for a reason")
    sections.append("")
    sections.append("Do not narrate beyond the room's walls.")
    sections.append("Do not explain what the player should do.")
    sections.append("Do not describe what locked things require.")
    sections.append("Do not describe where exits lead—only what presses from each direction.")
    sections.append("")
    sections.append("Begin your description now.")

    return "\n".join(sections)


def get_default_system_prompt() -> str:
    """Get the default system prompt for "Custom" mode.

    Returns the legacy hardcoded system prompt used when no template
    is selected, allowing users to write their own prompts.

    Returns
    -------
    str
        The default system prompt string.
    """
    return DEFAULT_SYSTEM_PROMPT
