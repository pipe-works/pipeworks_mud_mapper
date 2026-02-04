"""UI helpers for Ollama status messaging.

This module centralizes small UI fragments so callbacks can avoid
duplicating HTML span construction. Keeping these helpers in one place
ensures consistent styling across all Ollama interactions.
"""

from dash import html

# =============================================================================
# Status Helpers
# =============================================================================
# Each helper returns a small HTML fragment with an icon and text. The
# goal is to keep the callbacks focused on business logic rather than
# repeated UI markup.


def status_ok(message: str) -> html.Span:
    """Return a green success status with a check icon.

    Parameters
    ----------
    message : str
        The message to display to the user.

    Returns
    -------
    html.Span
        Styled status node indicating success.
    """
    return html.Span([html.I(className="bi bi-check-circle text-success me-1"), message])


def status_ok_filled(message: str) -> html.Span:
    """Return a filled green success status with a check icon.

    This is used when we want a slightly stronger success visual.
    """
    return html.Span([html.I(className="bi bi-check-circle-fill text-success me-1"), message])


def status_info(message: str, *, muted: bool = False) -> html.Span:
    """Return a blue info status with an info icon.

    Parameters
    ----------
    message : str
        The message to display to the user.
    muted : bool
        When True, uses muted text styling for subtle hints.
    """
    class_name = "text-muted" if muted else "text-info"
    return html.Span(
        [html.I(className=f"bi bi-info-circle {class_name} me-1"), message],
        className=class_name,
    )


def status_warning(message: str) -> html.Span:
    """Return a yellow warning status with an exclamation icon."""
    return html.Span(
        [html.I(className="bi bi-exclamation-triangle text-warning me-1"), message],
        className="text-warning",
    )


def status_error(message: str) -> html.Span:
    """Return a red error status with an X icon."""
    return html.Span([html.I(className="bi bi-x-circle text-danger me-1"), message])


def status_error_filled(message: str) -> html.Span:
    """Return a red error status with a filled X icon."""
    return html.Span(
        [html.I(className="bi bi-x-circle-fill text-danger me-1"), message],
        className="text-danger",
    )


def status_pending(message: str) -> html.Span:
    """Return a pending status with a spinning hourglass icon."""
    return html.Span(
        [html.I(className="bi bi-hourglass-split text-info me-1 spinning"), message],
        className="text-info",
    )
