"""Deterministic validator for LLM-generated room descriptions.

This module implements the hard-rule validator described in
``_working/description_validator.md``. It enforces structural constraints
without rewriting or negotiating prose, in line with the Craft of Constraint
principle that authority lives outside the model.

Design goals:
- Deterministic: same input yields same output.
- Explainable: every failure is labeled and traceable to a rule.
- Non-creative: the validator never edits or suggests replacements.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a room description.

    Attributes
    ----------
    valid : bool
        True when no hard rule failures were detected.
    hard_failures : list[str]
        Named hard rule failures (non-negotiable in the validator).
    soft_failures : list[str]
        Advisory failures for future expansion (currently unused).
    metrics : dict
        Numeric metrics captured during validation (word counts, bounds).
    rule_hits : dict[str, list[str]]
        Tokens matched per rule, for UI staging visibility.
    """

    valid: bool = True
    hard_failures: list[str] = field(default_factory=list)
    soft_failures: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    rule_hits: dict[str, list[str]] = field(default_factory=dict)


def _get_config_path() -> Path:
    """Resolve the validator config path relative to the project root."""
    package_dir = Path(__file__).parent.parent.parent.parent
    return package_dir / "data" / "ollama" / "description_validator.json"


def load_validator_config() -> dict[str, Any]:
    """Load validator rules from JSON config.

    Returns an empty dict on missing or invalid config to keep validation
    stable and non-failing in the UI path.
    """
    config_path = _get_config_path()
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
            return cast(dict[str, Any], data)
    except FileNotFoundError:
        logger.warning("Validator config not found: %s", config_path)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("Invalid validator JSON: %s (%s)", config_path, exc)
        return {}


def _count_words(text: str) -> int:
    """Count words using a simple tokenization heuristic.

    We treat apostrophes as part of a word to avoid splitting contractions.
    """
    return len(re.findall(r"[A-Za-z0-9']+", text))


def _word_boundary_match(text: str, token: str) -> bool:
    """Match a token with word boundaries when possible.

    Multi-word phrases are matched as substrings. Single-word tokens are
    matched with word boundaries to reduce false positives.
    """
    if " " in token:
        return token in text
    return re.search(rf"\b{re.escape(token)}\b", text) is not None


def _record_hits(result: ValidationResult, rule: str, hits: list[str]) -> None:
    """Record token hits for a rule if any were found."""
    if hits:
        result.rule_hits[rule] = hits


def validate_description(text: str, target_words: int) -> ValidationResult:
    """Validate a description against hard rules.

    Parameters
    ----------
    text : str
        Generated description text to validate.
    target_words : int
        Target word count from the UI. Used to compute bounds.

    Returns
    -------
    ValidationResult
        Structured results for UI display and persistence.
    """
    result = ValidationResult()
    config = load_validator_config()

    text_normalized = (text or "").strip()
    text_lower = text_normalized.lower()

    # Word count rule
    # Uses ratios so the validator stays in lockstep with the UI target.
    wc_config = config.get("word_count", {})
    if wc_config.get("enabled", True):
        word_count = _count_words(text_normalized)
        min_ratio = float(wc_config.get("min_ratio", 0.67))
        max_ratio = float(wc_config.get("max_ratio", 1.17))
        min_words = int(target_words * min_ratio)
        max_words = int(target_words * max_ratio)

        result.metrics["word_count"] = word_count
        result.metrics["target_words"] = target_words
        result.metrics["min_words"] = min_words
        result.metrics["max_words"] = max_words

        if word_count < min_words or word_count > max_words:
            result.hard_failures.append("word_count_out_of_bounds")

    # Banned phrases
    # Substring match is deliberate because these are fixed phrases.
    banned_phrases = [p.lower() for p in config.get("banned_phrases", [])]
    banned_hits = [phrase for phrase in banned_phrases if phrase in text_lower]
    _record_hits(result, "banned_phrases", banned_hits)
    result.hard_failures.extend([f"banned_phrase:{hit}" for hit in banned_hits])

    # Cardinal directions
    # Word boundary matching prevents false positives in longer words.
    cardinal_tokens = [t.lower() for t in config.get("cardinal_directions", [])]
    cardinal_hits = [t for t in cardinal_tokens if _word_boundary_match(text_lower, t)]
    _record_hits(result, "cardinal_directions", cardinal_hits)
    result.hard_failures.extend([f"cardinal_direction:{hit}" for hit in cardinal_hits])

    # Traversal verbs
    # These indicate movement or destination leakage.
    traversal_tokens = [t.lower() for t in config.get("traversal_verbs", [])]
    traversal_hits = [t for t in traversal_tokens if _word_boundary_match(text_lower, t)]
    _record_hits(result, "traversal_verbs", traversal_hits)
    result.hard_failures.extend([f"traversal_verb:{hit}" for hit in traversal_hits])

    if result.hard_failures:
        result.valid = False

    return result
