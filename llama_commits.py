#!/usr/bin/env python3
"""Fetch and summarize commits to llama.cpp from the last 24 hours."""

import json
import subprocess
from datetime import datetime, timedelta

# Calculate 24 hours ago
since_date = datetime.utcnow() - timedelta(hours=24)
since_str = since_date.strftime('%Y-%m-%dT%H:%M:%SZ')

# Fetch commits
result = subprocess.run([
    'curl', '-s',
    f'https://api.github.com/repos/ggml-org/llama.cpp/commits?per_page=20&since={since_str}'
], capture_output=True, text=True)

if result.returncode != 0:
    print(f'Error fetching commits: {result.stderr}')
    exit(1)

data = json.loads(result.stdout)

print('## llama.cpp Commits (Last 24h)')
print()

# Extract data
commits = []
for c in data:
    sha = c['sha'][:8]
    date = datetime.fromisoformat(c['commit']['author']['date'].replace('Z', '+00:00'))
    date_str = date.strftime('%Y-%m-%d %H:%M')
    message = c['commit']['message'].split('\n')[0]
    author = c['commit']['author']['name']
    commits.append((date_str, sha, message, author))

# Sort by date descending
commits.sort(key=lambda x: x[0], reverse=True)

# Print table
print('| Time | Commit | Description | Author |')
print('|------|--------|-------------|--------|')
for date_str, sha, msg, author in commits:
    print(f'| {date_str} | `{sha}` | {msg} | {author} |')

print()

# Key highlights
print('### Key Highlights')
print()

highlights = []
for c in data:
    msg = c['commit']['message'].lower()
    if any(kw in msg for kw in ['fix', 'bug', 'error', 'optim', 'perf', 'update', 'new']):
        msg_clean = c['commit']['message'].split('\n')[0]
        highlights.append(f'- **{c["sha"][:8]}**: {msg_clean}')

if highlights:
    print('\n'.join(highlights[:5]))  # Top 5 highlights
else:
    print('No major highlights detected.')
