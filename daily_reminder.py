#!/usr/bin/env python3
"""Daily reminder script: tasks, calendar, invoices, llama.cpp commits.

Usage:
    python3 scripts/daily_reminder.py

Output sections:
1. Tasks (all active, grouped by project)
2. Calendar events (next 7 days)
3. Invoice check (unread emails with 'lasku'/'invoice' in shared mailbox)
4. llama.cpp commits (last 24h)
"""

import re
import subprocess
import json
import sys
from datetime import datetime, timedelta, date
from collections import defaultdict

# Paths
SCRIPTS_DIR = "/home/nixos/.openclaw/workspace/scripts"
WORKSPACE = "/home/nixos/.openclaw/workspace"
TODO_FILE = f"{WORKSPACE}/todo/todo.txt"
DONE_FILE = f"{WORKSPACE}/todo/done.txt"
VENV_PYTHON = f"{WORKSPACE}/.venv/bin/python"

def run_tasks():
    """Get all tasks grouped by project."""
    print("🎯 DAILY TASKS")
    print()
    print("(All active tasks, grouped by project)")
    print()

    result = subprocess.run([
        VENV_PYTHON, "-m", "topydo", "-t", TODO_FILE, "-d", DONE_FILE,
        "ls", "-g", "project"
    ], capture_output=True, text=True, cwd=WORKSPACE)

    lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

    projects_tasks = defaultdict(list)
    current_project = None

    for line in lines:
        if line.strip().startswith('Project:'):
            project_name = line.strip().replace('Project:', '').strip()
            if project_name == 'None':
                current_project = 'No Project'
            else:
                current_project = project_name.lstrip('+')
            continue

        if not line.strip() or line.strip() == '=================':
            continue

        task_parts = line.split('|')
        if len(task_parts) >= 3:
            task = '|'.join(task_parts[2:]).strip()
            clean_task = task
            for tag in [current_project.lstrip('+'), 'No Project']:
                clean_task = clean_task.replace('+' + tag, '').strip()
            clean_task = re.sub(r'^\([A-Z]\)', '', clean_task).strip()
            clean_task = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', clean_task).strip()

            projects_tasks[current_project].append(clean_task)

    for project, tasks in sorted(projects_tasks.items()):
        if tasks:
            print(f"**{project}**")
            for task in tasks:
                print(f"• {task}")
            print()

    if not any(projects_tasks.values()):
        print("No active tasks found.")

    print()

def run_calendar():
    """Run calendar check."""
    print("📅 CALENDAR")
    print()

    try:
        # Change to scripts directory so credentials.py can be imported
        result = subprocess.run([
            "python3", f"{SCRIPTS_DIR}/check_calendar.py"
        ], capture_output=True, text=True, cwd=SCRIPTS_DIR, timeout=30)

        if result.stdout.strip():
            print(result.stdout.strip())
        else:
            print("No calendar events found.")

        if result.stderr.strip():
            print(f"\n⚠️ Calendar errors: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("⚠️ Calendar check timed out.")
    except Exception as e:
        print(f"⚠️ Calendar check failed: {e}")

    print()

def run_invoice_check():
    """Check for new invoices in shared mailbox."""
    print("📧 INVOICE CHECK")
    print()

    try:
        result = subprocess.run([
            "python3", f"{SCRIPTS_DIR}/check_invoices.py"
        ], capture_output=True, text=True, cwd=SCRIPTS_DIR, timeout=30)

        if result.stdout.strip():
            # Extract just the summary, not the debug output
            output = result.stdout.strip()
            # Show only the final results
            if "Found" in output or "No invoice" in output:
                # Find the last meaningful lines
                lines = output.split('\n')
                # Show from "Found" or "No invoice" onwards
                for i, line in enumerate(lines):
                    if 'Found' in line or 'No invoice' in line or '✓' in line:
                        print('\n'.join(lines[i:]))
                        break
                else:
                    print(output[-500:])  # Last 500 chars if no match
            else:
                print(output[-300:])
        else:
            print("Invoice check completed (no output).")

        if result.stderr.strip() and "Traceback" in result.stderr:
            print(f"\n⚠️ Invoice check error: {result.stderr.strip()[-200:]}")
    except subprocess.TimeoutExpired:
        print("⚠️ Invoice check timed out.")
    except Exception as e:
        print(f"⚠️ Invoice check failed: {e}")

    print()

def run_llama_commits():
    """Fetch llama.cpp commits from last 24h."""
    print("🦙 LLAMA.CPP COMMITS (24h)")
    print()

    try:
        result = subprocess.run([
            "python3", f"{SCRIPTS_DIR}/llama_commits.py"
        ], capture_output=True, text=True, cwd=SCRIPTS_DIR, timeout=30)

        if result.stdout.strip():
            print(result.stdout.strip())
        else:
            print("No commits found or fetch failed.")

        if result.stderr.strip():
            print(f"\n⚠️ Commit fetch error: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("⚠️ Commit fetch timed out.")
    except Exception as e:
        print(f"⚠️ Commit fetch failed: {e}")

    print()

def main():
    today = datetime.now()
    print(f"🐻 **Daily Report — {today.strftime('%A, %B %d, %Y')}**")
    print()
    print("*(Automated morning check — Europe/Helsinki timezone)*")
    print()
    print("---")
    print()

    run_tasks()
    print("---")
    print()
    run_calendar()
    print("---")
    print()
    run_invoice_check()
    print("---")
    print()
    run_llama_commits()

if __name__ == "__main__":
    main()
