"""CLI for initializing local LeetCode solutions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .problem_store import load_problem
from .runner import make_compilable_starter, get_python3_starter


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leetcode-helper", description="LeetCode local workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a local solution file from starter code")
    init_cmd.add_argument("problem_id", help="LeetCode problem id/frontend_id")
    init_cmd.add_argument("--output", help="Output file path")
    init_cmd.add_argument("--force", action="store_true", help="Overwrite if file exists")

    return parser


def command_init(problem_id: str, output: str | None, force: bool) -> int:
    root = repo_root()
    problem = load_problem(problem_id, root / "data")

    starter = get_python3_starter(problem)
    if not starter:
        print("No Python starter code found for this problem.")
        return 1

    output_path = Path(output) if output else root / "solutions" / f"problem_{problem_id}.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not force:
        print(f"File already exists: {output_path}")
        print("Use --force to overwrite.")
        return 1

    output_path.write_text(make_compilable_starter(starter), encoding="utf-8")
    print(f"Created starter solution: {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return command_init(args.problem_id, args.output, args.force)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
