"""Callbacks for validating Ollama responses.

This module provides the validation panel logic that checks generated
text against hard/soft rules and maintains a small history buffer.
"""

from datetime import UTC, datetime

from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.services import validate_description
from pipeworks_mud_mapper.services.ollama_config import DEFAULT_TARGET_WORDS


@callback(
    Output("ollama-validator-status", "children"),
    Output("ollama-validator-summary", "children"),
    Output("ollama-validator-hits", "children"),
    Output("ollama-validator-history", "children"),
    Output("ollama-validation-history", "data"),
    Output("ollama-validation-info", "data"),
    Input("ollama-response", "value"),
    State("ollama-target-words", "value"),
    State("ollama-validation-history", "data"),
    prevent_initial_call=True,
)
def validate_ollama_response(
    response_text: str | None,
    target_words: int | None,
    history: list[dict] | None,
):
    """Validate the latest LLM response and update the staging panel.

    This callback is advisory. It never blocks authors from applying a
    description. Instead, it surfaces hard-rule hits and aggregates a
    small in-memory history to make drift visible during iteration.
    """
    if not response_text:
        status = html.Small(
            [
                html.I(className="bi bi-dot text-muted me-1"),
                "Waiting for a response",
            ],
            className="text-muted",
        )
        summary = html.Small("No response to validate yet.", className="text-muted")
        hits = html.Small("No rule hits yet.", className="text-muted")
        history_display = _render_validation_history(history)
        return status, summary, hits, history_display, no_update, no_update

    target_words = target_words if target_words is not None else DEFAULT_TARGET_WORDS
    # The validator is deterministic and uses the UI target for word bounds.
    result = validate_description(response_text, target_words=target_words)

    if result.valid:
        status = html.Small(
            [
                html.I(className="bi bi-check-circle-fill text-success me-1"),
                "Pass (hard rules)",
            ],
            className="text-success",
        )
    else:
        status = html.Small(
            [
                html.I(className="bi bi-exclamation-triangle-fill text-warning me-1"),
                "Review needed",
            ],
            className="text-warning",
        )

    word_count = result.metrics.get("word_count")
    min_words = result.metrics.get("min_words")
    max_words = result.metrics.get("max_words")
    if word_count is not None and min_words is not None and max_words is not None:
        summary_text = (
            f"Words: {word_count} " f"(target {target_words}, range {min_words}-{max_words})"
        )
    else:
        summary_text = f"Target words: {target_words}"

    hard_count = len(result.hard_failures)
    if hard_count:
        summary_text = f"{summary_text} • Hard failures: {hard_count}"
    summary = html.Small(summary_text, className="text-muted")

    hits = _render_rule_hits(result)

    # Maintain a tiny ring buffer to keep the UI readable.
    history_list = list(history or [])
    history_list.append(
        {
            "timestamp": datetime.now(UTC).strftime("%H:%M:%S"),
            "valid": result.valid,
            "word_count": word_count,
            "hard_failures": hard_count,
        }
    )
    history_list = history_list[-3:]
    history_display = _render_validation_history(history_list)

    # Persist the latest validator output for map authoring metadata.
    validation_info = {
        "valid": result.valid,
        "hard_failures": result.hard_failures,
        "soft_failures": result.soft_failures,
        "metrics": result.metrics,
        "rule_hits": result.rule_hits,
        "validated_at": datetime.now(UTC).isoformat(),
    }

    return status, summary, hits, history_display, history_list, validation_info


# =============================================================================
# Helper Rendering Functions
# =============================================================================


def _render_rule_hits(result) -> html.Div:
    """Format rule hits for the staging panel."""
    if not result.rule_hits:
        return html.Small("No rule hits.", className="text-muted")

    lines = []
    for rule_name, hits in result.rule_hits.items():
        lines.append(html.Div(f"{rule_name.replace('_', ' ')}: {', '.join(sorted(set(hits)))}"))

    return html.Div(lines, className="text-muted")


def _render_validation_history(history: list[dict] | None) -> html.Div:
    """Render a compact, last-three history list."""
    if not history:
        return html.Small("No checks yet.", className="text-muted")

    rows = []
    for entry in history[-3:][::-1]:
        status = "pass" if entry.get("valid") else "review"
        word_count = entry.get("word_count")
        words_text = f"{word_count}w" if word_count is not None else "n/a"
        hard_failures = entry.get("hard_failures", 0)
        rows.append(
            html.Div(
                f"{entry.get('timestamp', '--:--:--')} • {status} • "
                f"{words_text} • {hard_failures} hits"
            )
        )

    return html.Div(rows, className="text-muted")
