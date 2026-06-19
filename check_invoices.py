#!/usr/bin/env python3
"""Check IMAP inbox for invoice-related emails from last 30 days."""

import imaplib
import email
import ssl
from datetime import datetime, timedelta
import re

# IMAP settings (loaded from secrets)
from credentials import creds
IMAP_HOST = creds['IMAP_SERVER']
IMAP_PORT = int(creds['IMAP_PORT'])
IMAP_USER = creds['IMAP_USER']
IMAP_PASS = creds['IMAP_PASS']

def parse_envelope(envelope_bytes):
    """Parse IMAP envelope bytes to extract subject and from address."""
    envelope_str = envelope_bytes.decode('utf-8', errors='ignore')
    
    # Remove message ID prefix if present (e.g., "500 ")
    if ' ' in envelope_str:
        idx = envelope_str.index(' ')
        envelope_str = envelope_str[idx+1:]
    
    # Find all quoted strings in the envelope
    quoted_strings = re.findall(r'"((?:[^"\\]|\\.)*)"', envelope_str)
    
    if len(quoted_strings) < 2:
        return None, None
    
    # subject is the second quoted string (index 1)
    subject = quoted_strings[1]
    
    # Find from address structure
    # The from structure is the first parenthesized group after the subject
    subject_end = envelope_str.find(f'"{subject}"') + len(f'"{subject}"')
    remaining = envelope_str[subject_end:]
    
    # Match a parenthesized group that may contain nested parens
    # Pattern: (anything that has balanced parens)
    match = re.search(r'\((?:[^()]|\([^()]*\))*\)', remaining)
    
    if not match:
        return subject, ""
    
    from_str = match.group(0)
    
    # Extract display name from from structure
    # Format: ("Name" NIL user host)
    name_match = re.search(r'\("([^"]*)"', from_str)
    from_name = name_match.group(1) if name_match else ""
    
    return subject, from_name

def decode_header_text(text):
    """Decode encoded header text if needed (RFC 2047)."""
    if not text or '=?' not in text:
        return text
    
    import quopri
    import base64
    
    # Pattern for encoded words: =?charset?encoding?content?=
    pattern = r'=\?([^?]*)\?([BQ])\?([^?]*)\?='
    
    def decode_match(match):
        charset = match.group(1)
        encoding = match.group(2).upper()
        content = match.group(3)
        try:
            if encoding == 'B':
                return base64.b64decode(content).decode(charset, errors='ignore')
            else:  # Q
                return quopri.decodestring(content.encode()).decode(charset, errors='ignore')
        except:
            return content
    
    return re.sub(pattern, decode_match, text)

def check_mailbox(imap, mailbox_name, readonly=True):
    """Check a mailbox for invoice-related emails."""
    try:
        # Try to select the mailbox
        if readonly:
            status, _ = imap.select(mailbox_name, readonly=True)
        else:
            status, _ = imap.select(mailbox_name)
            
        if status != "OK":
            print(f"  Could not select mailbox: {mailbox_name}")
            return []
        
        # Search for unread emails since 30 days ago
        date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        
        # Search criteria: unread since 30 days ago
        status, data = imap.search(
            None, 
            f'(UNSEEN SINCE {date_30_days_ago})'
        )
        
        if status != "OK":
            print(f"  No unread emails found: {status}")
            return []
        
        msg_ids = data[0].split()
        invoice_emails = []
        
        print(f"  Found {len(msg_ids)} unread messages to check...")
        
        for msg_id in msg_ids:
            msg_id_str = msg_id.decode('utf-8')
            
            # Fetch ENVELOPE for headers
            status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
            if status != "OK":
                continue
            
            # Parse envelope
            envelope_raw = msg_data[0]
            if isinstance(envelope_raw, tuple) and len(envelope_raw) >= 2:
                envelope_raw = envelope_raw[1]
            
            subject, from_name = parse_envelope(envelope_raw)
            
            if subject is None:
                continue
            
            # Decode subject
            subject = decode_header_text(subject)
            from_name = decode_header_text(from_name)
            
            # Check if subject contains lasku or invoice (case-insensitive)
            subject_lower = subject.lower()
            
            if 'lasku' in subject_lower or 'invoice' in subject_lower:
                print(f"  ✅ Found invoice/lasku: {subject}")
                
                # Check body for these terms as well
                status, body_data = imap.fetch(msg_id, '(BODY.PEEK[])')
                if status == "OK":
                    raw_msg = None
                    for item in body_data:
                        if isinstance(item, tuple) and len(item) >= 2:
                            raw_msg = item[1]
                            break
                    
                    if raw_msg:
                        msg = email.message_from_bytes(raw_msg)
                        body_text = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            body_text += payload.decode('utf-8', errors='ignore') + "\n"
                                    except:
                                        pass
                        else:
                            try:
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    body_text = payload.decode('utf-8', errors='ignore')
                            except:
                                pass
                        
                        body_lower = body_text.lower()
                        if 'lasku' in body_lower or 'invoice' in body_lower:
                            invoice_emails.append({
                                'id': msg_id_str,
                                'subject': subject,
                                'from': from_name,
                                'mailbox': mailbox_name
                            })
        
        return invoice_emails
        
    except Exception as e:
        print(f"Error checking {mailbox_name}: {e}")
        import traceback
        traceback.print_exc()
        return []

# Connect to IMAP server with SSL
context = ssl.create_default_context()
with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context) as imap:
    # Login
    imap.login(IMAP_USER, IMAP_PASS)
    
    all_invoice_emails = []
    
    # Check ONLY shared odroid mailbox (read-only)
    print("Checking shared/odroid mailbox only...")
    all_invoice_emails.extend(check_mailbox(imap, "shared/odroid", readonly=True))
    
    if all_invoice_emails:
        print(f"\n✓ Found {len(all_invoice_emails)} invoice/lasku email(s):\n")
        print("=" * 60)
        for i, email in enumerate(all_invoice_emails, 1):
            print(f"{i}. [{email['id']}] - {email['mailbox']}")
            print(f"   From: {email['from']}")
            print(f"   Subject: {email['subject']}")
            print()
    else:
        print("No invoice or 'lasku' related emails found in unread messages.")
