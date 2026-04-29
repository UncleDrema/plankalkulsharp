"""Generate ANTLR4 lexer/parser from grammar.

Usage:
    python scripts/generate_parser.py

Requires: Java runtime and ANTLR4 tool jar.
Downloads antlr4 jar automatically if not present.
"""

import subprocess
import sys
import urllib.request
from pathlib import Path

ANTLR_VERSION = "4.13.2"
ANTLR_JAR = f"antlr-{ANTLR_VERSION}-complete.jar"
ANTLR_URL = f"https://www.antlr.org/download/{ANTLR_JAR}"

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR = ROOT / "grammar" / "Plankalkul.g4"
OUTPUT = ROOT / "src" / "plankalkulsharp" / "frontend" / "generated"
TOOLS = ROOT / "tools"


def ensure_antlr_jar() -> Path:
    jar = TOOLS / ANTLR_JAR
    if jar.exists():
        return jar
    print(f"Downloading ANTLR {ANTLR_VERSION} tool...")
    TOOLS.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(ANTLR_URL, jar)
    print(f"Saved to {jar}")
    return jar


def main():
    jar = ensure_antlr_jar()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    cmd = [
        "java", "-jar", str(jar),
        "-Dlanguage=Python3",
        "-visitor",
        "-no-listener",
        "-o", str(OUTPUT),
        "-package", "plankalkulsharp.frontend.generated",
        str(GRAMMAR),
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"ANTLR4 generation failed with code {result.returncode}", file=sys.stderr)
        sys.exit(1)

    print(f"Generated parser in {OUTPUT}")


if __name__ == "__main__":
    main()
