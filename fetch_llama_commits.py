#!/usr/bin/env python3
import json
import sys
import urllib.request
from datetime import datetime, timedelta

# Calculate the date from 24 hours ago
since_date = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

# Fetch commits
url = f"https://api.github.com/repos/ggml-org/llama.cpp/commits?per_page=20&since={since_date}"
request = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw/DailyReport'})
try:
    with urllib.request.urlopen(request) as response:
        commits = json.loads(response.read().decode())
except Exception as e:
    print(f"Error fetching commits: {e}")
    sys.exit(1)

if not commits:
    print('No commits found in the last 24 hours.')
    sys.exit(0)

print('## llama.cpp Commits (Last 24 Hours)')
print()
print('| Time | Commit | Description | Author |')
print('|------|--------|-------------|--------|')

for c in commits:
    sha = c['sha'][:8]
    date = c['commit']['committer']['date']
    # Extract first line of message
    msg = c['commit']['message'].split('\n')[0]
    author = c['commit']['committer'].get('name', 'Unknown')
    
    # Format time (convert ISO format)
    time_str = date.replace('T', ' ').split('+')[0]
    
    print(f'| {time_str} | `{sha}` | {msg} | {author} |')

print()
print('### Key Highlights')
print()

# Analyze for notable changes
highlights = []
for c in commits[:10]:  # Check first 10 commits
    msg = c['commit']['message'].lower()
    has_gpu = any(word in msg for word in ['gpu', 'cuda', 'metal', 'vulkan', 'quant'])
    has_docs = any(word in msg for word in ['docs', 'readme', 'guide'])
    has_fix = any(word in msg for word in ['fix', 'bug'])
    
    if has_gpu:
        highlights.append(f"**GPU/Quantization work**: {c['sha'][:8]} - {c['commit']['message'].split(chr(10))[0]}")
    elif has_docs:
        highlights.append(f"**Documentation**: {c['sha'][:8]} - {c['commit']['message'].split(chr(10))[0]}")
    elif has_fix:
        highlights.append(f"**Bug fixes**: {c['sha'][:8]} - {c['commit']['message'].split(chr(10))[0]}")

if highlights:
    for h in highlights:
        print(f"- {h}")
else:
    print('No major highlights detected in the latest commits.')
