#!/usr/bin/env python3
"""
envcheck — validate your .env against .env.example
Usage: python envcheck.py [--env FILE] [--example FILE]
"""

import argparse
import os
import sys


# ANSI colors
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def parse_env_file(path: str) -> dict[str, str]:
    """Read a .env file and return {key: value} pairs."""
    if not os.path.exists(path):
        print(f"{RED}Error:{RESET} file not found: {path}")
        sys.exit(1)

    result = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                result[key.strip()] = value
    return result


def check(env_path: str, example_path: str) -> bool:
    """Compare .env against .env.example. Returns True if all OK."""
    env     = parse_env_file(env_path)
    example = parse_env_file(example_path)

    missing = [k for k in example if k not in env]
    empty   = [k for k in example if k in env and not env[k]]
    ok      = [k for k in example if k in env and env[k]]
    extra   = [k for k in env if k not in example]

    print(f"\n{DIM}Checking:{RESET} {env_path}  {DIM}vs{RESET}  {example_path}\n")

    for key in missing:
        print(f"  {RED}MISSING{RESET}   {key}")
    for key in empty:
        print(f"  {YELLOW}EMPTY  {RESET}   {key}")
    for key in ok:
        print(f"  {GREEN}OK     {RESET}   {key}")
    for key in extra:
        print(f"  {DIM}EXTRA  {RESET}   {key}  {DIM}(not in .env.example){RESET}")

    total = len(example)
    print(f"\n  {RED}{len(missing)} missing{RESET}  "
          f"{YELLOW}{len(empty)} empty{RESET}  "
          f"{GREEN}{len(ok)} ok{RESET}")

    if extra:
        print(f"  {DIM}{len(extra)} extra key(s) not declared in .env.example{RESET}")

    print()
    return len(missing) == 0 and len(empty) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate your .env file against .env.example",
        epilog="Exit code 0 = all good. Exit code 1 = missing or empty variables."
    )
    parser.add_argument("--env",     default=".env",         metavar="FILE", help="path to .env (default: .env)")
    parser.add_argument("--example", default=".env.example", metavar="FILE", help="path to .env.example (default: .env.example)")
    args = parser.parse_args()

    ok = check(args.env, args.example)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
