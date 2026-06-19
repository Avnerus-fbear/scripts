#!/usr/bin/env python3
"""Check shared odroid mailbox for Torguard invoice."""

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
    
    # Search for emails with "invoice" in subject (case-insensitive)
    status, data = imap.search(None, '(OR SUBJECT "invoice" SUBJECT "lasku")')
    print(f"Search status: {status}")
    
    msg_ids = data[0].split() if data and data[0] else []
    print(f"Found {len(msg_ids)} email(s) matching search")
    
    invoice_emails = []
    
    for msg_id in msg_ids:
        # Fetch ENVELOPE
        status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
        if status != "OK":
            print(f"  Failed to fetch {msg_id.decode()}")
            continue
            
        envelope_data = msg_data[0]
        # Handle both tuple and bytes formats
        if isinstance(envelope_data, tuple) and len(envelope_data) >= 2:
            envelope_str = envelope_data[1].decode('utf-8', errors='ignore')
        else:
            envelope_str = envelope_data.decode('utf-8', errors='ignore')
        
        print(f"\nEnvelope for {msg_id.decode()}: {envelope_str[:100]}...")
        
        env_match = re.search(r'\(ENVELOPE\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\)', envelope_str)
        if not env_match:
            print(f"  No match found")
            continue
            
        parts = env_match.groups()
        subject = parts[1] if parts[1] else ""
        from_addr = parts[6] if parts[6] else ""
        
        invoice_emails.append({
            'id': msg_id.decode(),
            'subject': subject,
            'from': from_addr
        })
        
        print(f"  ✓ MATCH: {subject}")

if invoice_emails:
    print(f"\n{'='*60}")
    print(f"TOTAL: Found {len(invoice_emails)} invoice/lasku email(s)")
    for email in invoice_emails:
        print(f"  - {email['subject']}")
else:
    print(f"\nNo invoice or 'lasku' related emails found in shared/odroid mailbox.")
