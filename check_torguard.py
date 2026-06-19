#!/usr/bin/env python3
"""Check recent emails from Torguard."""

import imaplib
import ssl
import re
from datetime import datetime, timedelta

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
    
    # Check main INBOX
    status, _ = imap.select("INBOX", readonly=True)
    print(f"INBOX status: {status}")
    
    # Search for emails from Torguard
    status, data = imap.search(None, 'FROM "torguard"')
    print(f"Search status: {status}")
    
    msg_ids = data[0].split() if data and data[0] else []
    print(f"Found {len(msg_ids)} email(s) from Torguard")
    
    for msg_id in msg_ids:
        # Fetch ENVELOPE
        status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
        if status != "OK":
            continue
            
        envelope_str = msg_data[0][1].decode('utf-8', errors='ignore') if isinstance(msg_data[0], tuple) else msg_data[0].decode('utf-8', errors='ignore')
        
        env_match = re.search(r'\(ENVELOPE\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\)', envelope_str)
        if not env_match:
            continue
            
        parts = env_match.groups()
        subject = parts[1] if parts[1] else ""
        from_addr = parts[6] if parts[6] else ""
        
        print(f"\n{'='*60}")
        print(f"ID: {msg_id.decode()}")
        print(f"From: {from_addr}")
        print(f"Subject: {subject}")

if not msg_ids:
    print("\nNo Torguard emails found in INBOX.")
    print("\nChecking other folders...")
    
    # List all mailboxes
    status, mailboxes = imap.list()
    if status == "OK":
        for mb in mailboxes:
            mb_name = mb.decode() if isinstance(mb, bytes) else mb
            if 'torguard' in mb_name.lower() or 'billing' in mb_name.lower():
                print(f"\nChecking: {mb_name}")
