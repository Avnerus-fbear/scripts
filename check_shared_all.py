#!/usr/bin/env python3
"""Check shared odroid mailbox - show all emails."""

import imaplib
import ssl
import re

# IMAP settings (loaded from secrets)
from credentials import creds
IMAP_HOST = creds['IMAP_SERVER']
IMAP_PORT = int(creds['IMAP_PORT'])
IMAP_USER = creds['IMAP_USER']
IMAP_PASS = creds['IMAP_PASS']

# Connect to IMAP server with SSL
context = ssl.create_default_context()
with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context) as imap:
    # Login
    imap.login(IMAP_USER, IMAP_PASS)
    
    # Check shared odroid mailbox
    status, _ = imap.select("shared/odroid", readonly=True)
    print(f"shared/odroid status: {status}")
    
    # Get all message IDs
    status, data = imap.search(None, 'ALL')
    msg_ids = data[0].split() if data and data[0] else []
    print(f"Found {len(msg_ids)} email(s) total")
    
    # Show last 10 emails
    last_n = 10
    for msg_id in msg_ids[-last_n:]:
        # Fetch ENVELOPE
        status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
        if status != "OK":
            continue
            
        envelope_str = msg_data[0][1].decode('utf-8', errors='ignore') if isinstance(msg_data[0], tuple) else msg_data[0].decode('utf-8', errors='ignore')
        
        env_match = re.search(r'\(ENVELOPE\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\)', envelope_str)
        if not env_match:
            continue
            
        parts = env_match.groups()
        subject = parts[1] if parts[1] else "(empty)"
        from_addr = parts[6] if parts[6] else "(empty)"
        
        print(f"\nID: {msg_id.decode()} | Subject: {subject}")
