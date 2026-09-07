#!/usr/bin/env python
"""
Run every check this project has, in one command, on any platform.

    python scripts/verify.py           # lint, tests, end-to-end smoke test
    python scripts/verify.py --quick   # skip the smoke test (no server needed)

Use the interpreter from the virtualenv:

    .venv/bin/python scripts/verify.py          macOS and Linux
    .\\.venv\\Scripts\\python scripts\\verify.py   Windows (the leading .\\ is required)

Exits 0 only when everything passes, so CI and pre-commit hooks can use it too.
`make verify` is a shortcut for this on macOS and Linux.
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLOUR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
GREEN, RED, BOLD, RESET = ("\033[32m", "\033[31m", "\033[1m", "\033[0m") if COLOUR else ("", "", "", "")

# Each step is (heading, argv after the interpreter). Everything runs through
# sys.executable so it works the same whatever the platform calls the venv.
STEPS = [
    ("Lint", ["-m", "ruff", "check", "."]),
    ("Formatting", ["-m", "ruff", "format", "--check", "."]),
    ("Missing migrations", ["manage.py", "makemigrations", "--check", "--dry-run"]),
    ("Tests", ["manage.py", "test", "--settings=config.test_settings"]),
    ("End-to-end smoke test", [os.path.join("scripts", "smoke_test.py")]),
]


def run(heading, args):
    print(f"\n{BOLD}=== {heading} ==={RESET}")
    result = subprocess.run([sys.executable, *args], cwd=BASE_DIR)
    if result.returncode == 0:
        print(f"{GREEN}OK{RESET}  {heading}")
        return True
    print(f"{RED}FAILED{RESET}  {heading}")
    return False


def main():
    steps = STEPS
    if "--quick" in sys.argv:
        steps = [step for step in steps if "smoke_test.py" not in step[1][0]]

    # A missing dependency is the usual reason this cannot start; say so plainly
    # rather than failing several steps in a row with an import traceback.
    try:
        import django  # noqa: F401
    except ImportError:
        print(
            f"{RED}Django is not installed for {sys.executable}.{RESET}\n"
            "Install the dependencies first:\n"
            "  .venv/bin/pip install -r requirements-dev.txt        (macOS, Linux)\n"
            "  .\\.venv\\Scripts\\pip install -r requirements-dev.txt  (Windows)"
        )
        return 1

    failures = [heading for heading, args in steps if not run(heading, args)]

    print()
    if not failures:
        print(f"{GREEN}{BOLD}Everything passed.{RESET} The project is working.")
        return 0
    print(f"{RED}{BOLD}{len(failures)} step(s) failed:{RESET} {', '.join(failures)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
