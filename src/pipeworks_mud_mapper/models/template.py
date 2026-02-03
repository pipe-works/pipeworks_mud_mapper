"""Ollama template models for LLM prompt generation.

This module defines Pydantic models for Ollama templates that encode theme,
voice guidance, and craft constraints for generating room descriptions.

Template Structure
------------------
Templates follow the Craft of Constraint philosophy and compile into
comprehensive system prompts for small LLMs like Gemma2:2B.

::

    OllamaTemplate
    ├── template_name, template_id, version
    ├── description
    ├── theme: TemplateTheme
    │   ├── name (thematic world)
    │   ├── tone (emotional register)
    │   ├── era (time period)
    │   └── aesthetic (sensory flavor)
    ├── voice_guidance: TemplateVoiceGuidance
    │   ├── style (how the GM speaks)
    │   ├── register (formality level)
    │   ├── keyword_include (words to weave in)
    │   └── keyword_exclude (words to avoid)
    ├── craft_constraints: TemplateCraftConstraints
    │   ├── multi_part_spaces
    │   ├── locked_things_approach
    │   ├── silence_tone
    │   └── exit_hints
    ├── examples: TemplateExamples
    │   ├── good_crossroads / bad_crossroads
    │   ├── good_locked_thing / bad_locked_thing
    │   └── good_multi_part / bad_multi_part
    ├── author_notes
    └── author_credit

Usage
-----
Load and validate a template::

    from pipeworks_mud_mapper.models import OllamaTemplate
    import json

    with open("template.json") as f:
        data = json.load(f)
    template = OllamaTemplate.model_validate(data)

See Also
--------
- ``services/template_service.py``: Template loading and compilation
- ``_working/ollama/``: Template architecture documentation
"""

from pydantic import BaseModel, Field


class TemplateTheme(BaseModel):
    """Theme configuration for an Ollama template.

    Defines the thematic world, emotional register, time period,
    and sensory flavor for room descriptions.

    Attributes
    ----------
    name : str
        The thematic world (e.g., "Ledgerfall, a goblin-run urban realm").
    tone : str
        Primary emotional register (e.g., "whimsical, deadpan, slightly chaotic").
    era : str
        Time period if relevant (e.g., "Victorian-inspired"). Can be empty.
    aesthetic : str
        Visual/sensory flavor (e.g., "copper pipes, ink smudges, rust").
    """

    name: str = Field(..., min_length=1, description="Thematic world name")
    tone: str = Field(..., min_length=1, description="Primary emotional register")
    era: str = Field(default="", description="Time period if relevant")
    aesthetic: str = Field(default="", description="Visual/sensory flavor")


class TemplateVoiceGuidance(BaseModel):
    """Voice and style guidance for an Ollama template.

    Defines how the Game Master "speaks" in room descriptions,
    including formality, style, and keyword guidance.

    Attributes
    ----------
    style : str
        How the GM speaks (e.g., "as if narrating for a gossip column").
    voice_register : str
        Formality level (e.g., "matter-of-fact with dry humor").
        Note: Named voice_register to avoid shadowing Pydantic's register method.
    keyword_include : list[str]
        Words/concepts to weave in when fitting.
    keyword_exclude : list[str]
        Words/concepts to avoid.
    """

    style: str = Field(..., min_length=1, description="How the GM speaks")
    voice_register: str = Field(..., min_length=1, alias="register", description="Formality level")
    keyword_include: list[str] = Field(
        default_factory=list, description="Words to weave in when fitting"
    )
    keyword_exclude: list[str] = Field(default_factory=list, description="Words to avoid")

    model_config = {"populate_by_name": True}


class TemplateCraftConstraints(BaseModel):
    """Craft of Constraint specific guidance for an Ollama template.

    Provides theme-specific guidance for common description challenges:
    multi-part spaces, locked things, silence, and exit descriptions.

    Attributes
    ----------
    multi_part_spaces : str
        How to describe wide/complex spaces (markets, long streets).
    locked_things_approach : str
        How to handle barriers without explaining solutions.
    silence_tone : str
        What silence feels like in this theme.
    exit_hints : str
        How to describe directions without narrating destinations.
    """

    multi_part_spaces: str = Field(default="", description="How to describe wide spaces")
    locked_things_approach: str = Field(default="", description="How to handle barriers")
    silence_tone: str = Field(default="", description="What silence feels like")
    exit_hints: str = Field(default="", description="How to describe directions")


class TemplateExamples(BaseModel):
    """Good and bad examples for an Ollama template.

    Provides concrete examples that guide small LLMs to produce
    correct descriptions by showing what TO do and what NOT to do.

    Attributes
    ----------
    good_crossroads : str
        Correct way to describe a choice point.
    bad_crossroads : str
        Common mistake when describing choice points.
    good_locked_thing : str
        Correct way to describe barriers without explaining solutions.
    bad_locked_thing : str
        Common mistake when describing barriers.
    good_multi_part : str
        Correct way to describe the middle of a complex space.
    bad_multi_part : str
        Common mistake with wide/complex spaces.
    """

    good_crossroads: str = Field(default="", description="Correct crossroads example")
    bad_crossroads: str = Field(default="", description="Incorrect crossroads example")
    good_locked_thing: str = Field(default="", description="Correct barrier example")
    bad_locked_thing: str = Field(default="", description="Incorrect barrier example")
    good_multi_part: str = Field(default="", description="Correct wide space example")
    bad_multi_part: str = Field(default="", description="Incorrect wide space example")


class OllamaTemplate(BaseModel):
    """A complete Ollama template for room description generation.

    Templates compile into comprehensive system prompts that guide small
    LLMs (like Gemma2:2B) to produce consistent, constraint-respecting
    room descriptions following the Craft of Constraint philosophy.

    Attributes
    ----------
    template_name : str
        Human-readable display name (e.g., "Ledgerfall Goblin").
    template_id : str
        Unique identifier in slug format (e.g., "ledgerfall_goblin").
    version : str
        Semantic version (default: "1.0.0").
    description : str
        Brief explanation of when/why to use this template.
    theme : TemplateTheme
        Thematic world configuration.
    voice_guidance : TemplateVoiceGuidance
        Voice and style guidance.
    craft_constraints : TemplateCraftConstraints
        Craft of Constraint specific guidance.
    examples : TemplateExamples
        Good and bad examples for the template.
    author_notes : str
        Meta guidance for template authors/forkers.
    author_credit : str
        Template creator attribution.

    Examples
    --------
    Create a minimal template::

        >>> template = OllamaTemplate(
        ...     template_name="My Theme",
        ...     template_id="my_theme",
        ...     theme=TemplateTheme(name="A fantasy world", tone="epic"),
        ...     voice_guidance=TemplateVoiceGuidance(
        ...         style="grand narrator",
        ...         register="formal"
        ...     ),
        ... )

    Load from JSON file::

        >>> import json
        >>> with open("template.json") as f:
        ...     data = json.load(f)
        >>> template = OllamaTemplate.model_validate(data)
    """

    template_name: str = Field(..., min_length=1, description="Human-readable display name")
    template_id: str = Field(..., min_length=1, description="Unique identifier (slug format)")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(default="", description="When/why to use this template")

    theme: TemplateTheme
    voice_guidance: TemplateVoiceGuidance
    craft_constraints: TemplateCraftConstraints = Field(default_factory=TemplateCraftConstraints)
    examples: TemplateExamples = Field(default_factory=TemplateExamples)

    author_notes: str = Field(default="", description="Meta guidance for template authors")
    author_credit: str = Field(default="", description="Template creator attribution")
