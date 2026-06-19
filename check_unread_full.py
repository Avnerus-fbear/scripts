#!/usr/bin/env python3
"""Check what unread emails exist in the inbox with full details."""

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
        print(f"\n{'='*60}")
        print(f"EMAIL ID: {msg_id.decode()}")
        
        # Fetch ENVELOPE (headers only)
        status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
        envelope_str = msg_data[0][1].decode('utf-8', errors='ignore') if isinstance(msg_data[0], tuple) else msg_data[0].decode('utf-8', errors='ignore')
        
        # Parse envelope properly
        env_match = re.search(r'\(ENVELOPE\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\)', envelope_str)
        if env_match:
            parts = env_match.groups()
            print(f"Date: {parts[0]}")
            print(f"Subject: {parts[1] if parts[1] else '(empty)'}")
            print(f"From: {parts[6] if parts[6] else '(empty)'}")
            print(f"To: {parts[7] if parts[7] else '(empty)'}")
        
        # Fetch full body
        status, body_data = imap.fetch(msg_id, '(BODY.PEEK[])')
        if status == "OK":
            raw_msg = body_data[0][1] if isinstance(body_data[0], tuple) else body_data[0]
            msg = __import__('email').message_from_bytes(raw_msg)
            
            print(f"\nMultipart: {msg.is_multipart()}")
            
            # Check all parts for text content
            if msg.is_multipart():
                for i, part in enumerate(msg.walk()):
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    print(f"\nPart {i}: {content_type}")
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            print(f"Body preview: {body[:500]}")
                            print(f"'invoice' in body: {'invoice' in body.lower()}")
                            print(f"'lasku' in body: {'lasku' in body.lower()}")
                        except:
                            print("Could not decode part")
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    print(f"\nBody preview: {body[:500]}")
                    print(f"'invoice' in body: {'invoice' in body.lower()}")
                    print(f"'lasku' in body: {'lasku' in body.lower()}")
                except:
                    print("Could not decode body")
