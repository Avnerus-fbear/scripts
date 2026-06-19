#!/usr/bin/env python3
"""Search IMAP for emails containing 'lasku' in subject or body from last 30 days."""

import imaplib
import email
import ssl
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header

# IMAP Configuration (loaded from secrets)
from credentials import creds
IMAP_SERVER = creds['IMAP_SERVER']
IMAP_PORT = int(creds['IMAP_PORT'])
IMAP_USER = creds['IMAP_USER']
IMAP_PASSWORD = creds['IMAP_PASS']

def decode_imap_string(s):
    """Decode IMAP encoded string."""
    if not s:
        return ""
    try:
        decoded = decode_header(s)
        result = ""
        for text, encoding in decoded:
            if isinstance(text, bytes):
                result += text.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += text
        return result
    except:
        return s.decode('utf-8', errors='ignore') if isinstance(s, bytes) else str(s)

def search_lasku_emails():
    """Search for emails with 'lasku' in subject or body."""
    # Connect to IMAP server
    context = ssl.create_default_context()
    
    with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context) as imap:
        # Login
        status, _ = imap.login(IMAP_USER, IMAP_PASSWORD)
        if status != 'OK':
            print(f"Login failed: {status}")
            return
        
        # Select the shared mailbox (read-only)
        status, _ = imap.select("shared/odroid@avner.us", readonly=True)
        if status != 'OK':
            print(f"Failed to select mailbox: {status}")
            return
        
        # Calculate date 30 days ago
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%d-%b-%Y")
        
        # Search for unread emails from last 30 days
        search_criterion = f'(UNSEEN SINCE {thirty_days_ago})'
        status, data = imap.search(None, search_criterion)
        
        if status != 'OK':
            print(f"Search failed: {status}")
            return
        
        # Get message IDs
        msg_ids = data[0].split()
        print(f"Found {len(msg_ids)} unread messages from last 30 days")
        
        # Filter for 'lasku' in subject or body
        matching_emails = []
        
        for msg_id in msg_ids:
            # Fetch envelope (headers only)
            status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
            if status != 'OK':
                continue
            
            # The envelope data comes as a list with tuples
            envelope_bytes = None
            for item in msg_data:
                if isinstance(item, tuple) and len(item) >= 2:
                    envelope_bytes = item[1]
                    break
            
            if not envelope_bytes:
                continue
            
            # Parse envelope - it's a bytes string like: b'543 (ENVELOPE ("date" "subject" ...))'
            envelope_str = envelope_bytes.decode('utf-8', errors='ignore')
            # Extract the envelope data part
            match = re.search(r'\(ENVELOPE\s*\((.*)\)\)', envelope_str, re.DOTALL)
            if not match:
                continue
            
            envelope_data = match.group(1)
            # Parse the envelope fields (date, subject, from, etc.)
            # This is a simplified parser for the envelope structure
            parts = []
            current = ""
            in_quotes = False
            escape_next = False
            for char in envelope_data:
                if escape_next:
                    current += char
                    escape_next = False
                    continue
                if char == '\\' and in_quotes:
                    current += char
                    escape_next = True
                    continue
                if char == '"':
                    in_quotes = not in_quotes
                    current += char
                elif char == '(' and not in_quotes:
                    current = ""
                elif char == ')' and not in_quotes:
                    if current.strip():
                        parts.append(current.strip())
                    current = ""
                elif char == ' ' and not in_quotes:
                    if current.strip():
                        parts.append(current.strip())
                    current = ""
                else:
                    current += char
            
            # Parse the envelope fields
            # Structure: date, subject, from, sender, reply-to, to, cc, bcc, in-reply-to, message-id
            if len(parts) >= 7:
                date_str = parts[0].strip('"') if len(parts) > 0 else ""
                subject = decode_imap_string(parts[1].strip('"')) if len(parts) > 1 else ""
                from_addr = decode_imap_string(parts[2].strip('"')) if len(parts) > 2 else ""
            else:
                continue
            
            # Check if 'lasku' is in subject (case-insensitive)
            subject_lower = subject.lower()
            has_lasku_in_body = False
            
            if 'lasku' in subject_lower:
                matching_emails.append({
                    'id': msg_id.decode('utf-8'),
                    'date': date_str,
                    'from': from_addr,
                    'subject': subject,
                    'has_lasku_in_body': False
                })
                continue
            
            # Fetch full message to check body
            status, msg_data = imap.fetch(msg_id, '(BODY.PEEK[])')
            if status != 'OK':
                continue
            
            raw_msg = None
            for item in msg_data:
                if isinstance(item, tuple) and len(item) >= 2:
                    raw_msg = item[1]
                    break
            
            if not raw_msg:
                continue
            
            # Parse the message
            msg = email.message_from_bytes(raw_msg)
            
            # Check body for 'lasku'
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            if 'lasku' in body.lower():
                                has_lasku_in_body = True
                                break
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    if 'lasku' in body.lower():
                        has_lasku_in_body = True
                except:
                    pass
            
            if has_lasku_in_body:
                matching_emails.append({
                    'id': msg_id.decode('utf-8'),
                    'date': date_str,
                    'from': from_addr,
                    'subject': subject,
                    'has_lasku_in_body': True
                })
        
        # Print results
        print(f"\n--- Emails with 'lasku' found: {len(matching_emails)} ---\n")
        
        for email_info in matching_emails:
            print(f"ID: {email_info['id']}")
            print(f"Date: {email_info['date']}")
            print(f"From: {email_info['from']}")
            print(f"Subject: {email_info['subject']}")
            print(f"Location: {'Body' if email_info['has_lasku_in_body'] else 'Subject'}")
            print("-" * 60)
        
        if not matching_emails:
            print("No emails with 'lasku' found in unread messages from last 30 days.")

if __name__ == "__main__":
    search_lasku_emails()
