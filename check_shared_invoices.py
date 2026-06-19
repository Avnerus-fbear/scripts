#!/usr/bin/env python3
"""Check shared odroid mailbox for unread invoice/lasku emails."""

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
    
    # Search for UNREAD emails with "invoice" or "lasku" in subject
    status, data = imap.search(None, '(UNSEEN OR SUBJECT "invoice" SUBJECT "lasku")')
    
    msg_ids = data[0].split() if data and data[0] else []
    print(f"Found {len(msg_ids)} unread email(s) matching search\n")
    
    invoice_emails = []
    
    for msg_id in msg_ids:
        # Fetch ENVELOPE
        status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
        if status != "OK":
            continue
            
        envelope_data = msg_data[0]
        if isinstance(envelope_data, tuple) and len(envelope_data) >= 2:
            envelope_str = envelope_data[1].decode('utf-8', errors='ignore')
        else:
            envelope_str = envelope_data.decode('utf-8', errors='ignore')
        
        # Split by quotes to extract values
        parts = envelope_str.split('"')
        
        if len(parts) < 4:
            continue
            
        date = parts[1]
        subject = parts[3]
        
        # From name is at index 11 (after "TorGuard User (Anonymous)")
        from_name = parts[11] if len(parts) > 11 else parts[5]
        
        # Check if subject contains invoice or lasku
        if 'invoice' in subject.lower() or 'lasku' in subject.lower():
            invoice_emails.append({
                'id': msg_id.decode(),
                'subject': subject,
                'from': from_name
            })
            print(f"ID: {msg_id.decode()}")
            print(f"Date: {date}")
            print(f"Subject: {subject}")
            print(f"From: {from_name}")
            print("✓ MATCH\n")

if invoice_emails:
    print(f"{'='*60}")
    print(f"TOTAL: Found {len(invoice_emails)} unread invoice/lasku email(s)")
    for email in invoice_emails:
        print(f"  - {email['subject']} from {email['from']}")
else:
    print("No unread invoice or 'lasku' related emails found.")
