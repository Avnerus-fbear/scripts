#!/usr/bin/env python3
import imaplib
import re

# Connect to IMAP server
from credentials import creds
imap = imaplib.IMAP4_SSL(creds['IMAP_SERVER'], int(creds['IMAP_PORT']))
imap.login(creds['IMAP_USER'], creds['IMAP_PASS'])

# Select shared/odroid mailbox (read-only)
status, _ = imap.select('shared/odroid', readonly=True)
if status != 'OK':
    print(f'Failed to select mailbox: {status}')
    exit(1)

# Search for unread messages from last 30 days
from datetime import datetime, timedelta
date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime('%d-%b-%Y')
status, data = imap.search(None, '(UNSEEN SINCE ' + date_30_days_ago + ')')
if status != 'OK':
    print(f'Failed to search: {status}')
    exit(1)

# Get message IDs
msg_ids = data[0].split()
print(f'Found {len(msg_ids)} unread messages from last 30 days\n')

if not msg_ids:
    print('No unread messages found.')
    exit(0)

# Sample first message to debug format
msg_id = msg_ids[0]
status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
print(f"Message ID: {msg_id}")
print(f"Status: {status}")
print(f"Message data type: {type(msg_data)}")
print(f"Message data length: {len(msg_data)}")

if msg_data:
    print(f"msg_data[0] type: {type(msg_data[0])}")
    if isinstance(msg_data[0], tuple):
        print(f"msg_data[0][1] type: {type(msg_data[0][1])}")
        envelope_str = msg_data[0][1].decode('utf-8', errors='ignore')
        print(f"Envelope string (first 500 chars): {envelope_str[:500]}")
        
        # Parse the envelope
        envelope_str_clean = envelope_str.split('(')[1].split(')')[0] if '(' in envelope_str else envelope_str
        parts = envelope_str_clean.split()
        print(f"First 20 parts: {parts[:20]}")

imap.close()
imap.logout()
