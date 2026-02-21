"""Dataset helpers for local LeetCode problems."""

from __future__ import annotations

import json
from pathlib import Path


def load_problems(data_dir: Path) -> list[dict]:
    """Load all problems from data/problems.json."""
    problems_file = data_dir / "problems.json"
    if not problems_file.exists():
        raise FileNotFoundError(f"Missing dataset file: {problems_file}")

    with problems_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_problem(problem_id: str, data_dir: Path) -> dict:
    """Load one problem by id/frontend_id."""
    normalized = str(problem_id)
    for problem in load_problems(data_dir):
        pid = str(problem.get("id") or problem.get("frontend_id"))
        if pid == normalized:
            return problem
    raise KeyError(f"Problem not found: {problem_id}")
