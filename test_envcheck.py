"""
Comprehensive test suite for envcheck.py
Covers normal cases, edge cases, and malformed inputs.
"""

import os
import subprocess
import sys
import tempfile
import textwrap

SCRIPT = os.path.join(os.path.dirname(__file__), "envcheck.py")
PYTHON = sys.executable


def run(env_content: str, example_content: str) -> tuple[str, int]:
    """Write temp files, run envcheck, return (output, exit_code)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path     = os.path.join(tmpdir, ".env")
        example_path = os.path.join(tmpdir, ".env.example")

        with open(env_path,     "w") as f: f.write(env_content)
        with open(example_path, "w") as f: f.write(example_content)

        result = subprocess.run(
            [PYTHON, SCRIPT, "--env", env_path, "--example", example_path],
            capture_output=True, text=True
        )
        return result.stdout + result.stderr, result.returncode


def run_no_file(which: str) -> tuple[str, int]:
    """Run with a missing file (env or example)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        existing_path = os.path.join(tmpdir, ".env.existing")
        with open(existing_path, "w") as f: f.write("KEY=value\n")

        if which == "env":
            args = ["--env", "/nonexistent/.env", "--example", existing_path]
        else:
            args = ["--env", existing_path, "--example", "/nonexistent/.env.example"]

        result = subprocess.run(
            [PYTHON, SCRIPT] + args,
            capture_output=True, text=True
        )
        return result.stdout + result.stderr, result.returncode


# -- Test runner ----------------------------------------------------------------

passed = 0
failed = 0

def test(name: str, env: str, example: str, expect_exit: int,
         must_contain: list[str] = None, must_not_contain: list[str] = None):
    global passed, failed
    output, code = run(textwrap.dedent(env), textwrap.dedent(example))

    errors = []
    if code != expect_exit:
        errors.append(f"exit code {code} (expected {expect_exit})")
    for phrase in (must_contain or []):
        if phrase.lower() not in output.lower():
            errors.append(f"expected '{phrase}' in output")
    for phrase in (must_not_contain or []):
        if phrase.lower() in output.lower():
            errors.append(f"did NOT expect '{phrase}' in output")

    if errors:
        print(f"  FAIL  {name}")
        for e in errors: print(f"        -> {e}")
        print(f"        output: {repr(output[:300])}")
        failed += 1
    else:
        print(f"  PASS  {name}")
        passed += 1


def test_no_file(name: str, which: str, expect_exit: int, must_contain: list[str] = None):
    global passed, failed
    output, code = run_no_file(which)
    errors = []
    if code != expect_exit:
        errors.append(f"exit code {code} (expected {expect_exit})")
    for phrase in (must_contain or []):
        if phrase.lower() not in output.lower():
            errors.append(f"expected '{phrase}' in output")
    if errors:
        print(f"  FAIL  {name}")
        for e in errors: print(f"        -> {e}")
        failed += 1
    else:
        print(f"  PASS  {name}")
        passed += 1


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 1. NORMAL CASES ------------------------------------------------------")

test("All keys present and filled",
    env=     "KEY1=value1\nKEY2=value2\n",
    example= "KEY1=\nKEY2=\n",
    expect_exit=0,
    must_contain=["OK", "0 missing"])

test("One missing key",
    env=     "KEY1=value1\n",
    example= "KEY1=\nKEY2=\n",
    expect_exit=1,
    must_contain=["MISSING", "KEY2"])

test("One empty key",
    env=     "KEY1=value1\nKEY2=\n",
    example= "KEY1=\nKEY2=\n",
    expect_exit=1,
    must_contain=["EMPTY", "KEY2"])

test("Extra key in .env not in .env.example",
    env=     "KEY1=value1\nEXTRA=foo\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["EXTRA"])

test("Mixed: missing + empty + ok + extra",
    env=     "KEY1=value1\nKEY2=\nEXTRA=foo\n",
    example= "KEY1=\nKEY2=\nKEY3=\n",
    expect_exit=1,
    must_contain=["MISSING", "KEY3", "EMPTY", "KEY2", "OK", "KEY1"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 2. EMPTY FILES -------------------------------------------------------")

test("Both files empty",
    env=     "",
    example= "",
    expect_exit=0,
    must_contain=["0 missing"])

test("Empty .env, non-empty .env.example",
    env=     "",
    example= "KEY1=\nKEY2=\n",
    expect_exit=1,
    must_contain=["MISSING", "KEY1", "KEY2"])

test("Non-empty .env, empty .env.example",
    env=     "KEY1=value\n",
    example= "",
    expect_exit=0,
    must_contain=["EXTRA"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 3. COMMENTS AND BLANK LINES ------------------------------------------")

test("Comments ignored in .env",
    env=     "# this is a comment\nKEY1=value1\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Comments ignored in .env.example",
    env=     "KEY1=value1\n",
    example= "# comment\nKEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Blank lines ignored",
    env=     "\n\nKEY1=value1\n\n",
    example= "\nKEY1=\n\n",
    expect_exit=0,
    must_contain=["OK"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 4. SPACING AND FORMATTING --------------------------------------------")

test("Spaces around = sign",
    env=     "KEY1 = value1\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Whitespace-only value treated as empty",
    env=     "KEY1=   \n",
    example= "KEY1=\n",
    expect_exit=1,
    must_contain=["EMPTY"])

test("Value with spaces (no quotes)",
    env=     "KEY1=hello world\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Leading/trailing spaces in key name",
    env=     "  KEY1  =value1\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 5. VALUES WITH SPECIAL CHARACTERS ------------------------------------")

test("Value contains = sign (e.g. base64)",
    env=     "SECRET=abc==dGVzdA==\n",
    example= "SECRET=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Value contains special chars (!@#$%)",
    env=     "KEY1=p@$$w0rd!#%\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Value is a URL",
    env=     "DATABASE_URL=postgresql://user:pass@localhost:5432/db\n",
    example= "DATABASE_URL=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Value contains unicode",
    env=     "GREETING=héllo wörld\n",
    example= "GREETING=\n",
    expect_exit=0,
    must_contain=["OK"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 6. QUOTED VALUES -----------------------------------------------------")

test("Double-quoted value is treated as non-empty",
    env=     'KEY1="my value"\n',
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Single-quoted value is treated as non-empty",
    env=     "KEY1='my value'\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])

test("Empty double-quoted value is treated as empty",
    env=     'KEY1=""\n',
    example= "KEY1=\n",
    expect_exit=1,
    must_contain=["EMPTY"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 7. INLINE COMMENTS ---------------------------------------------------")

test("Inline comment: value before # is non-empty",
    env=     "KEY1=value # this is a comment\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 8. DUPLICATE KEYS ----------------------------------------------------")

test("Duplicate key in .env — last value wins, counted once",
    env=     "KEY1=first\nKEY1=second\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["1 ok"])

test("Duplicate key in .env.example — last entry wins",
    env=     "KEY1=value\n",
    example= "KEY1=\nKEY1=\n",
    expect_exit=0,
    must_contain=["OK"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 9. KEY WITHOUT = SIGN ------------------------------------------------")

test("Key with no = sign in .env is ignored (not treated as a key)",
    env=     "INVALID_LINE\nKEY1=value\n",
    example= "KEY1=\n",
    expect_exit=0,
    must_contain=["OK"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 10. MISSING FILES ----------------------------------------------------")

test_no_file("Missing .env file exits with error",
    which="env",
    expect_exit=1,
    must_contain=["error"])

test_no_file("Missing .env.example file exits with error",
    which="example",
    expect_exit=1,
    must_contain=["error"])


# ══════════════════════════════════════════════════════════════════════════════
print("\n-- 11. LARGE FILE -------------------------------------------------------")

large_env     = "\n".join(f"KEY_{i}=value_{i}" for i in range(500)) + "\n"
large_example = "\n".join(f"KEY_{i}=" for i in range(500)) + "\n"

test("500 keys — all present and filled",
    env=large_env, example=large_example,
    expect_exit=0,
    must_contain=["500 ok"])


# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'-'*60}")
print(f"  Results: {passed} passed, {failed} failed")
print(f"{'-'*60}\n")
sys.exit(0 if failed == 0 else 1)
