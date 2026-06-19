#!/usr/bin/env python3
import imaplib
import email
from datetime import datetime, timedelta
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

# Analyze messages
important_emails = []
action_needed = []
normal_emails = []

for msg_id in msg_ids:
    # Fetch full message
    status, msg_data = imap.fetch(msg_id, '(RFC822.HEADER)')
    if status != 'OK':
        continue
    
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)
    
    # Extract headers
    date_str = msg.get('Date', '')
    from_addr = msg.get('From', '')
    subject = msg.get('Subject', '')
    
    # Decode subject if necessary
    if subject.startswith('=?'):
        try:
            subject = email.header.decode_header(subject)[0][0].decode('utf-8') if isinstance(subject, bytes) else subject
        except:
            pass
    
    msg_id_str = msg_id.decode()
    
    # Check for invoice keywords
    has_invoice = bool(re.search(r'(lasku|invoice)', subject, re.IGNORECASE))
    
    email_info = {
        'id': msg_id_str,
        'date': date_str,
        'from': from_addr,
        'subject': subject,
        'has_invoice': has_invoice
    }
    
    if has_invoice:
        important_emails.append(email_info)
        action_needed.append(email_info)
    else:
        normal_emails.append(email_info)

# Print results
print("=" * 60)
print("URGENT - Action Required (Invoices/Laskut)")
print("=" * 60)

if action_needed:
    for email_info in action_needed:
        print(f"\n📧 Email ID: {email_info['id']}")
        print(f"📅 Date: {email_info['date']}")
        print(f"👤 From: {email_info['from']}")
        print(f"📝 Subject: {email_info['subject']}")
        print("-" * 40)
else:
    print("No urgent emails requiring action.")

print("\n" + "=" * 60)
print(f"Other Unread Emails ({len(normal_emails)} total)")
print("=" * 60)

if normal_emails:
    for email_info in normal_emails:
        print(f"\n📧 Email ID: {email_info['id']}")
        print(f"📅 Date: {email_info['date']}")
        print(f"👤 From: {email_info['from']}")
        print(f"📝 Subject: {email_info['subject']}")
        print("-" * 40)
else:
    print("No other unread emails.")

print("\n" + "=" * 60)
print(f"Summary: {len(important_emails)} invoice/lasku emails, {len(normal_emails)} other unread emails")
print("=" * 60)

imap.close()
imap.logout()
