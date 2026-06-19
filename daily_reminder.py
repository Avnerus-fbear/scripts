#!/usr/bin/env python3
"""Check todos and calendar for daily reminder."""

import re
import subprocess
from datetime import date
from collections import defaultdict

print(f"📅 Daily Report — {date.today().strftime('%A, %B %d, %Y')}")
print()
print("(This is an automated daily check of your tasks and calendar)")
print()

# Run todo check using topydo with explicit paths for todo file
venv_python = "/home/nixos/.openclaw/workspace/.venv/bin/python"
todo_file = "/home/nixos/.openclaw/workspace/todo/todo.txt"
done_file = "/home/nixos/.openclaw/workspace/todo/done.txt"

# Get all tasks grouped by project
print()
print("🎯 DAILY TASKS")
print()
print("(All active tasks, grouped by project)")
print()

# Get all tasks grouped by project
result = subprocess.run([
    venv_python, "-m", "topydo", "-t", todo_file, "-d", done_file, 
    "ls", "-g", "project"
], capture_output=True, text=True, cwd="/home/nixos/.openclaw/workspace")

# Parse the grouped output to organize tasks by project
lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

projects_tasks = defaultdict(list)
current_project = None

for line in lines:
    # Check if we're entering a project section
    if line.strip().startswith('Project:'):
        project_name = line.strip().replace('Project:', '').strip()
        if project_name == 'None':
            current_project = 'No Project'
        else:
            current_project = project_name.lstrip('+')
        continue
    
    # Skip empty lines and separator lines
    if not line.strip() or line.strip() == '=================':
        continue
    
    # Clean up the task line - remove the leading |xxx| ID
    task_parts = line.split('|')
    if len(task_parts) >= 3:
        task = '|'.join(task_parts[2:]).strip()
        # Remove the +project tag from display
        clean_task = task
        # Remove the project tag (e.g., +mywhatif, +birthday)
        for tag in [current_project.lstrip('+'), 'No Project']:
            clean_task = clean_task.replace('+' + tag, '').strip()
        # Remove priority prefix for display (A, B, C, etc.)
        clean_task = re.sub(r'^\([A-Z]\)', '', clean_task).strip()
        # Remove creation date (YYYY-MM-DD) at the start
        clean_task = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', clean_task).strip()
        
        projects_tasks[current_project].append(clean_task)

# Print tasks grouped by project
for project, tasks in sorted(projects_tasks.items()):
    if tasks:
        print(f"**{project}**")
        for task in tasks:
            print(f"• {task}")
        print()

# Check if there are no tasks
if not any(projects_tasks.values()):
    print("No active tasks found.")

print()

# Run calendar check
subprocess.run([
    "python3", 
    "/home/nixos/.openclaw/workspace/scripts/check_calendar.py"
])
