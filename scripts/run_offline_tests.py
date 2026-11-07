#!/usr/bin/env python3
"""Run only hardware-independent unit tests on generic machines.

Hardware E2E tests require the dedicated AMD host, running Switch, Mattermost,
vLLM, and ROCm. They are not meaningful on hosted CI runners.
"""
from pathlib import Path
import sys
import unittest


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_path in sorted((Path(__file__).resolve().parents[1] / "tests").glob("test_*.py")):
        if test_path.name == "test_e2e_full_suite.py":
            continue
        suite.addTests(loader.discover(str(test_path.parent), pattern=test_path.name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
