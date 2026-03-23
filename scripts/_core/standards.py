# scripts/_core/standards.py
"""Shared utility for loading and filtering dbt project governance standards."""
from __future__ import annotations

import json
import re
from pathlib import Path

_STANDARDS_PATH = Path("reference/dbt_project_standards.json")


def _condense_description(description: str) -> str:
    """Strip code examples and verbose sub-sections, keeping the core rule statement.

    Removes everything at or after the first code fence, or the first
    markdown sub-heading (``######``, ``#####``, ``####``) that introduces
    examples or supplementary detail.
    """
    for marker in ("```", "\n######", "\n#####", "\n####"):
        idx = description.find(marker)
        if idx != -1:
            description = description[:idx]
    # Collapse multiple blank lines left behind after stripping
    description = re.sub(r"\n{3,}", "\n\n", description)
    return description.strip()


def load_standards_for_layer(
    layer: str,
    condense: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Return governance rules applicable to the given model layer.

    Args:
        layer: One of ``"staging"``, ``"base"``, ``"integration"``,
            ``"marts"``, or ``"unknown"``.
        condense: When True, strip verbose code examples from descriptions
            so the output is token-efficient for LLM consumption.

    Returns:
        Tuple of ``(manual_rules, automated_rules)`` where each item is a
        list of rule dicts with keys ``id``, ``title``, ``description``,
        ``layer``, and ``is_automated``.  Rules whose ``layer`` is ``"all"``
        appear in both lists alongside layer-specific rules.

    Raises:
        FileNotFoundError: If the standards JSON cannot be found.
    """
    if not _STANDARDS_PATH.exists():
        raise FileNotFoundError(
            f"Standards JSON not found at {_STANDARDS_PATH}. "
            "Run `python -m scripts.governance.parse_standards` first."
        )

    with open(_STANDARDS_PATH, encoding="utf-8") as fh:
        all_rules: list[dict] = json.load(fh)

    applicable = [
        r for r in all_rules if r.get("layer") in ("all", layer)
    ]

    if condense:
        applicable = [
            {**r, "description": _condense_description(r.get("description", ""))}
            for r in applicable
        ]

    manual = [r for r in applicable if not r.get("is_automated")]
    automated = [r for r in applicable if r.get("is_automated")]

    return manual, automated
