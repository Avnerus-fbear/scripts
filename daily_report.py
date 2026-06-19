#!/usr/bin/env python3
"""Consolidated daily report: todos, calendar, invoices, llama.cpp commits."""

import subprocess
import sys
from datetime import date

def run_script(script_path):
    """Run a script and capture its output."""
    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True, text=True, timeout=120,
            cwd="/home/nixos/.openclaw/workspace"
        )
        output = result.stdout.strip() or result.stderr.strip()
        if not output:
            output = "(no output)"
        return output
    except subprocess.TimeoutExpired:
        return f"(timed out after 120s)"
    except Exception as e:
        return f"(error: {e})"

def main():
    scripts = [
        ("daily_reminder.py", None),
        ("check_invoices.py", "Checking invoices..."),
        ("llama_commits.py", "Fetching llama.cpp commits..."),
    ]

    for script, intro in scripts:
        if intro:
            print(intro)
        output = run_script(f"/home/nixos/.openclaw/workspace/scripts/{script}")
        print(output)
        print()
        print("=" * 60)
        print()

if __name__ == "__main__":
    main()
