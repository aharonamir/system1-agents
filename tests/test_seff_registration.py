# coding: utf-8
"""``seff`` is offered wherever ``jev`` is: every tuple, list, set, ``match`` and ``Literal`` that lists ``jev``
lists ``seff`` too. A registration point added later without it fails here.
"""

from __future__ import annotations

import ast
import typing
from pathlib import Path

from s1a import mcp_server
from s1a.browser.browse import BROWSER_MODEL_NAMES
from s1a.cli import DECIDE_MODEL_NAMES
from s1a.decision_models import DECISION_MODEL_NAMES
from s1a.rails import RAIL_MODEL_NAMES
from s1a.tool.loop import MODEL_NAMES

SOURCE = Path(__file__).resolve().parents[1] / "s1a"


def constants(node: ast.AST) -> set[str]:
    return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def places_missing_seff() -> list[str]:
    missing = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
                values = {e.value for e in node.elts if isinstance(e, ast.Constant)}
            elif isinstance(node, ast.Match):
                values = set().union(*(constants(case.pattern) for case in node.cases))
            elif (
                isinstance(node, ast.Subscript)
                and getattr(node.value, "id", getattr(node.value, "attr", "")) == "Literal"
            ):
                values = constants(node.slice)
            else:
                continue
            if "jev" in values and "seff" not in values:
                missing.append(f"{path.relative_to(SOURCE.parent).as_posix()}:{node.lineno}")
    return missing


def test_every_place_that_offers_jev_offers_seff() -> None:
    assert places_missing_seff() == []


def test_the_named_lists() -> None:
    for names in (DECISION_MODEL_NAMES, DECIDE_MODEL_NAMES, RAIL_MODEL_NAMES, MODEL_NAMES, BROWSER_MODEL_NAMES):
        assert "seff" in names
    decide_model = typing.get_type_hints(
        mcp_server.decide.__wrapped__ if hasattr(mcp_server.decide, "__wrapped__") else mcp_server.decide
    )["model"]
    assert "seff" in typing.get_args(decide_model)


def test_the_check_would_catch_a_missing_place(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "s1a").mkdir()
    (tmp_path / "s1a" / "new_front.py").write_text('NAMES = ("jev", "clm")\n', encoding="utf-8")
    monkeypatch.setattr(__name__ + ".SOURCE", tmp_path / "s1a")
    assert places_missing_seff() == ["s1a/new_front.py:1"]
