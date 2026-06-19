#!/usr/bin/env python3
"""Check ALL emails with invoice/lasku in subject (no date limit)."""

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
    
    # Check main INBOX
    status, _ = imap.select("INBOX", readonly=True)
    print(f"INBOX status: {status}")
    
    # Search for emails with "invoice" or "lasku" in subject
    status, data = imap.search(None, '(OR SUBJECT "invoice" SUBJECT "lasku")')
    print(f"Search status: {status}")
    
    msg_ids = data[0].split() if data and data[0] else []
    print(f"Found {len(msg_ids)} email(s) with 'invoice' or 'lasku' in subject")
    
    invoice_emails = []
    
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
        
        invoice_emails.append({
            'id': msg_id.decode(),
            'subject': subject,
            'from': from_addr
        })
        
        print(f"\n{'='*60}")
        print(f"ID: {msg_id.decode()}")
        print(f"From: {from_addr}")
        print(f"Subject: {subject}")

if invoice_emails:
    print(f"\n{'='*60}")
    print(f"TOTAL: Found {len(invoice_emails)} invoice/lasku email(s)")
else:
    print(f"\nNo invoice or 'lasku' related emails found.")
