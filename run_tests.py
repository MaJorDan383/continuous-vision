# Run the plugin's test suite. This does NOT install anything into the running interpreter
# (that mutates the user's environment): install the dev extra into a venv first, or into
# whatever environment already has pytest.
#
#   python -m venv .venv && .venv/Scripts/pip install -e ".[dev]" && .venv/Scripts/python run_tests.py
#   pip install -e ".[dev]" && pytest tests/
import subprocess
import sys


def run(*extra: str) -> int:
    return subprocess.call([sys.executable, "-m", "pytest", *(extra or ("tests/", "-q"))])


if __name__ == "__main__":
    try:
        import pytest  # noqa: F401
    except ImportError:
        print('pytest is not installed in this interpreter — run: pip install -e ".[dev]"')
        raise SystemExit(2)
    raise SystemExit(run(*sys.argv[1:]))