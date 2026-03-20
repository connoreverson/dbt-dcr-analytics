"""Tests for _core renderers — focused on the new LLM renderer."""
from scripts._core.renderers.llm import render_llm_context


def test_render_llm_context_basic():
    """LLM renderer produces structured markdown with labeled sections."""
    sections = {
        "Model": "fct_reservations",
        "Layer": "Mart (fact)",
        "Grain": "One row per reservation",
        "Parents": ["int_contacts", "int_parks"],
    }
    output = render_llm_context(sections)
    assert "## Model" in output
    assert "fct_reservations" in output
    assert "## Grain" in output
    assert "int_contacts" in output
    # Should not contain rich formatting or decorative characters
    assert "\u2550" not in output
    assert "[bold]" not in output


def test_render_llm_context_with_prompt():
    """LLM renderer includes a suggested prompt section when provided."""
    sections = {
        "Model": "int_parks",
    }
    prompt = "I have a parks integration model. How should I add a new source?"
    output = render_llm_context(sections, suggested_prompt=prompt)
    assert "## Suggested Prompt" in output
    assert "How should I add a new source?" in output
