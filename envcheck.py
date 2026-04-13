#!/usr/bin/env python3
"""
envcheck — validate your .env against .env.example
Usage: python envcheck.py [--env FILE] [--example FILE]
"""

import argparse
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# ANSI color constants  (kept at module level — pure data, no behavior)
# ---------------------------------------------------------------------------

RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
DIM    = "\033[2m"
RESET  = "\033[0m"


# ===========================================================================
# LAYER 1 — Pure-data container
#   S: holds result data only, zero logic.
#   I: consumers that only need data never touch parser or reporter code.
# ===========================================================================

@dataclass
class ComparisonResult:
    """
    Pure value object that carries the four categories produced by a
    comparison.  No methods, no I/O, no parsing — only data.

    S — single responsibility: represent the comparison outcome as data.
    """
    env_path:     str
    example_path: str
    missing: list[str] = field(default_factory=list)
    empty:   list[str] = field(default_factory=list)
    ok:      list[str] = field(default_factory=list)
    extra:   list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        """True when there are no missing or empty keys."""
        return len(self.missing) == 0 and len(self.empty) == 0


# ===========================================================================
# LAYER 2 — Abstractions (interfaces)
#   I — each interface is narrow and cohesive; no implementor is forced to
#       carry methods it does not need.
#   D — high-level modules depend on these abstractions, not on concretes.
# ===========================================================================

class EnvFileParserBase(ABC):
    """
    Contract for anything that can read an env file and return a dict.

    I — one abstract method only; implementations are never burdened with
        unrelated concerns such as comparison or output.
    """

    @abstractmethod
    def parse(self, path: str) -> dict[str, str]:
        """
        Parse *path* and return a mapping of {KEY: value}.

        Raises FileNotFoundError when the path does not exist.
        """


class EnvComparatorBase(ABC):
    """
    Contract for anything that can compare two env dicts and produce a
    ComparisonResult.

    I — focused solely on comparison; reporters and parsers never implement
        this interface.
    """

    @abstractmethod
    def compare(
        self,
        env: dict[str, str],
        example: dict[str, str],
        env_path: str,
        example_path: str,
    ) -> ComparisonResult:
        """Return a ComparisonResult describing the diff between the dicts."""


class ReporterBase(ABC):
    """
    Contract for anything that can present a ComparisonResult to the user.

    I — focused on presentation only; new output targets (file, JSON, …) just
        implement this interface without touching any other layer.
    O — adding a new reporter (e.g. JsonReporter) never requires modifying
        existing classes.
    """

    @abstractmethod
    def report(self, result: ComparisonResult) -> None:
        """Present *result* to the user."""


# ===========================================================================
# LAYER 3 — Concrete implementations
# ===========================================================================

class EnvFileParser(EnvFileParserBase):
    """
    Reads a .env-style file from disk and returns {key: value} pairs.

    S — responsible only for I/O + parsing; has no knowledge of comparison
        or output.
    L — fully substitutable for EnvFileParserBase; raises FileNotFoundError
        as documented by the contract so callers need not change behaviour.
    """

    def parse(self, path: str) -> dict[str, str]:
        """
        Parse *path* into a dict.

        Raises FileNotFoundError when the file does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        result: dict[str, str] = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip()
                    if (
                        len(value) >= 2
                        and value[0] == value[-1]
                        and value[0] in ('"', "'")
                    ):
                        value = value[1:-1]
                    result[key.strip()] = value
        return result


class EnvComparator(EnvComparatorBase):
    """
    Compares two env dicts and produces a ComparisonResult.

    S — responsible only for the comparison algorithm; does not read files
        and does not produce any output.
    L — substitutable for EnvComparatorBase; always returns a
        ComparisonResult without side effects.
    """

    def compare(
        self,
        env: dict[str, str],
        example: dict[str, str],
        env_path: str,
        example_path: str,
    ) -> ComparisonResult:
        return ComparisonResult(
            env_path=env_path,
            example_path=example_path,
            missing=[k for k in example if k not in env],
            empty=[k for k in example if k in env and not env[k]],
            ok=[k for k in example if k in env and env[k]],
            extra=[k for k in env if k not in example],
        )


class ConsoleReporter(ReporterBase):
    """
    Formats and prints a ComparisonResult to stdout using ANSI colours.

    S — responsible only for presentation; has zero knowledge of how files
        are parsed or how the comparison is performed.
    L — substitutable for ReporterBase; always writes to stdout and returns
        None as the contract specifies.
    O — the output format is encapsulated here; changing it never affects
        any other class.
    """

    def report(self, result: ComparisonResult) -> None:
        print(
            f"\n{DIM}Checking:{RESET} {result.env_path}"
            f"  {DIM}vs{RESET}  {result.example_path}\n"
        )

        for key in result.missing:
            print(f"  {RED}MISSING{RESET}   {key}")
        for key in result.empty:
            print(f"  {YELLOW}EMPTY  {RESET}   {key}")
        for key in result.ok:
            print(f"  {GREEN}OK     {RESET}   {key}")
        for key in result.extra:
            print(f"  {DIM}EXTRA  {RESET}   {key}  {DIM}(not in .env.example){RESET}")

        print(
            f"\n  {RED}{len(result.missing)} missing{RESET}  "
            f"{YELLOW}{len(result.empty)} empty{RESET}  "
            f"{GREEN}{len(result.ok)} ok{RESET}"
        )

        if result.extra:
            print(
                f"  {DIM}{len(result.extra)} extra key(s) "
                f"not declared in .env.example{RESET}"
            )

        print()


# ===========================================================================
# LAYER 4 — Orchestration / CLI
#   D — CLI depends only on the abstract interfaces; concrete types are
#       injected, making the wiring easy to swap without modifying CLI logic.
#   S — CLI is responsible only for argument parsing, wiring, and exit code;
#       it delegates every other concern to the collaborators it receives.
# ===========================================================================

class CLI:
    """
    Parses CLI arguments, wires collaborators together, and drives execution.

    S — responsible only for orchestration; delegates parsing, comparison,
        and reporting to the injected collaborators.
    D — depends on abstractions (EnvFileParserBase, EnvComparatorBase,
        ReporterBase), not on concrete classes.  Concrete instances are
        supplied by the caller (main()), keeping this class testable and
        extensible.
    """

    def __init__(
        self,
        parser:     EnvFileParserBase,
        comparator: EnvComparatorBase,
        reporter:   ReporterBase,
    ) -> None:
        self._parser     = parser
        self._comparator = comparator
        self._reporter   = reporter

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, argv: list[str] | None = None) -> int:
        """
        Execute the full pipeline.

        Returns 0 when all keys are present and non-empty, 1 otherwise.
        Exits with code 1 immediately when a file cannot be found.
        """
        args = self._parse_args(argv)

        env_dict     = self._load_file(args.env)
        example_dict = self._load_file(args.example)

        result = self._comparator.compare(
            env_dict, example_dict, args.env, args.example
        )
        self._reporter.report(result)

        return 0 if result.is_ok else 1

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_args(argv: list[str] | None) -> argparse.Namespace:
        arg_parser = argparse.ArgumentParser(
            description="Validate your .env file against .env.example",
            epilog="Exit code 0 = all good. Exit code 1 = missing or empty variables.",
        )
        arg_parser.add_argument(
            "--env",
            default=".env",
            metavar="FILE",
            help="path to .env (default: .env)",
        )
        arg_parser.add_argument(
            "--example",
            default=".env.example",
            metavar="FILE",
            help="path to .env.example (default: .env.example)",
        )
        return arg_parser.parse_args(argv)

    def _load_file(self, path: str) -> dict[str, str]:
        """
        Delegate to the injected parser; translate FileNotFoundError into
        a user-friendly error message and a sys.exit(1) so the external
        behaviour remains identical to the original implementation.
        """
        try:
            return self._parser.parse(path)
        except FileNotFoundError:
            print(f"{RED}Error:{RESET} file not found: {path}")
            sys.exit(1)


# ===========================================================================
# ENTRY POINT — wires concrete implementations and hands control to CLI
# ===========================================================================

def main() -> None:
    """
    Compose the object graph with concrete implementations and run.

    D — all concrete dependencies are created here (the composition root)
        and injected into CLI; no high-level module constructs its own
        dependencies.
    """
    cli = CLI(
        parser=     EnvFileParser(),
        comparator= EnvComparator(),
        reporter=   ConsoleReporter(),
    )
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
