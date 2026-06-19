#!/usr/bin/env python3
"""Check what unread emails exist in the inbox."""

import imaplib
import ssl
from datetime import datetime, timedelta
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
    
    # Search for unread emails since 30 days ago
    date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
    print(f"Search date: {date_30_days_ago}")
    
    status, data = imap.search(None, f'(UNSEEN SINCE {date_30_days_ago})')
    print(f"Search status: {status}")
    
    msg_ids = data[0].split()
    print(f"Found {len(msg_ids)} unread email(s)")
    
    for msg_id in msg_ids:
        status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
        envelope_str = msg_data[0][1].decode('utf-8', errors='ignore') if isinstance(msg_data[0], tuple) else msg_data[0].decode('utf-8', errors='ignore')
        
        # Extract subject
        match = re.search(r'Subject: "([^"]*)"', envelope_str)
        subject = match.group(1) if match else "No subject"
        print(f"\nID {msg_id.decode()}: {subject}")
        
        # Check body
        status, body_data = imap.fetch(msg_id, '(BODY.PEEK[])')
        if status == "OK":
            raw_msg = body_data[0][1] if isinstance(body_data[0], tuple) else body_data[0]
            msg = __import__('email').message_from_bytes(raw_msg)
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_text += part.get_payload(decode=True).decode('utf-8', errors='ignore') + "\n"
            else:
                body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            if 'invoice' in body_text.lower() or 'lasku' in body_text.lower():
                print(f"  → Contains 'invoice' or 'lasku' in body")
