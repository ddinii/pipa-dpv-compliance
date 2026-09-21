from __future__ import annotations

import subprocess
import sys


def main() -> int:
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        [sys.executable, "run_mapping_demo.py"],
    ]
    for command in commands:
        completed = subprocess.run(command, check=False)
        if completed.returncode:
            return completed.returncode
    print("FINAL: FACT-TO-ONTOLOGY MAPPING TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

