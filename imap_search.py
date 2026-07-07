#!/usr/bin/env python3
"""Reusable IMAP search helper for searching mailboxes.

Usage:
    python3 scripts/imap_search.py --mailbox "shared/odroid" --since "01-Oct-2025" --before "31-Oct-2025" --keyword "PhD"
    python3 scripts/imap_search.py --mailbox "shared/odroid/Archives/2025" --since "01-Oct-2025" --before "15-Oct-2025" --keyword "gift"
    python3 scripts/imap_search.py --mailbox "INBOX" --keyword "invoice" --max 10

Options:
    --mailbox    Mailbox name (default: shared/odroid)
    --since      Start date (IMAP format, e.g., "01-Oct-2025")
    --before     End date (IMAP format)
    --keyword    Search keyword (searches subject + body)
    --subject    Search in subject only
    --max        Max results (default: 50)
    --full       Show full message body (not just subject)
    --json       Output as JSON

Examples:
    # Find all emails with "invoice" in Oct 2025
    python3 scripts/imap_search.py --mailbox "shared/odroid/Archives/2025" --since "01-Oct-2025" --before "31-Oct-2025" --keyword "invoice"

    # Find emails from specific sender
    python3 scripts/imap_search.py --mailbox "INBOX" --subject "from:boss"

    # List recent unread emails
    python3 scripts/imap_search.py --mailbox "INBOX" --unseen --max 5
"""

import imaplib
import email
import ssl
import re
import sys
import json
import argparse
import quopri
import base64
from datetime import datetime

# IMAP settings (loaded from credentials)
sys.path.insert(0, '/home/nixos/.openclaw/workspace/scripts')
from credentials import creds

IMAP_HOST = creds['IMAP_SERVER']
IMAP_PORT = int(creds['IMAP_PORT'])
IMAP_USER = creds['IMAP_USER']
IMAP_PASS = creds['IMAP_PASS']


def decode_header_text(text):
    """Decode encoded header text if needed (RFC 2047)."""
    if not text or '=?' not in text:
        return text

    pattern = r'=\?([^?]*)\?([BQ])\?([^?]*)\?='

    def decode_match(match):
        charset = match.group(1)
        encoding = match.group(2).upper()
        content = match.group(3)
        try:
            if encoding == 'B':
                return base64.b64decode(content).decode(charset, errors='ignore')
            else:
                return quopri.decodestring(content.encode()).decode(charset, errors='ignore')
        except:
            return content

    return re.sub(pattern, decode_match, text)


def parse_envelope(envelope_bytes):
    """Parse IMAP envelope bytes to extract subject and from address.

    This is the reliable parser that handles nested parentheses in IMAP envelopes.
    """
    envelope_str = envelope_bytes.decode('utf-8', errors='ignore')

    # Remove message ID prefix if present
    if ' ' in envelope_str:
        idx = envelope_str.index(' ')
        envelope_str = envelope_str[idx+1:]

    # Find all quoted strings
    quoted_strings = re.findall(r'"((?:[^"\\]|\\.)*)"', envelope_str)

    if len(quoted_strings) < 2:
        return None, None, None

    # Subject is the second quoted string (index 1)
    subject = quoted_strings[1]

    # Find from address structure
    subject_end = envelope_str.find(f'"{subject}"') + len(f'"{subject}"')
    remaining = envelope_str[subject_end:]

    # Match a parenthesized group (may contain nested parens)
    match = re.search(r'\((?:[^()]|\([^()]*\))*\)', remaining)

    if not match:
        return subject, "", None

    from_str = match.group(0)
    name_match = re.search(r'\("([^"]*)"', from_str)
    from_name = name_match.group(1) if name_match else ""

    # Try to extract date (first quoted string)
    date_str = quoted_strings[0] if len(quoted_strings) > 0 else None

    return decode_header_text(subject), decode_header_text(from_name), date_str


def get_message_body(imap, msg_id):
    """Extract plain text body from a message."""
    try:
        status, body_data = imap.fetch(msg_id, '(BODY.PEEK[])')
        if status != "OK":
            return ""

        raw_msg = None
        for item in body_data:
            if isinstance(item, tuple) and len(item) >= 2:
                raw_msg = item[1]
                break

        if not raw_msg:
            return ""

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

        return body_text
    except Exception as e:
        return f"[Error fetching body: {e}]"


def search_mailbox(mailbox, since=None, before=None, keyword=None, subject_only=False, unseen=False, max_results=50, show_full=False):
    """Search a mailbox and return matching messages."""
    context = ssl.create_default_context()

    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context) as imap:
        imap.login(IMAP_USER, IMAP_PASS)

        # Select mailbox
        status, _ = imap.select(mailbox, readonly=True)
        if status != "OK":
            print(f"Error: Could not select mailbox '{mailbox}'", file=sys.stderr)
            return []

        # Build search criteria
        criteria = []
        if unseen:
            criteria.append("UNSEEN")
        if since:
            criteria.append(f"SINCE {since}")
        if before:
            criteria.append(f"BEFORE {before}")
        if keyword:
            if subject_only:
                criteria.append(f'SUBJECT "{keyword}"')
            else:
                criteria.append(f'TEXT "{keyword}"')

        search_str = f'({" ".join(criteria)})' if criteria else 'ALL'

        # Execute search
        status, data = imap.search(None, search_str)
        if status != "OK":
            print(f"Search failed: {status}", file=sys.stderr)
            return []

        msg_ids = data[0].split()[:max_results]
        results = []

        for msg_id in msg_ids:
            msg_id_str = msg_id.decode('utf-8')

            # Fetch envelope
            status, msg_data = imap.fetch(msg_id, '(ENVELOPE)')
            if status != "OK":
                continue

            envelope_raw = msg_data[0]
            if isinstance(envelope_raw, tuple) and len(envelope_raw) >= 2:
                envelope_raw = envelope_raw[1]

            subject, from_name, date_str = parse_envelope(envelope_raw)

            if subject is None:
                continue

            result = {
                'id': msg_id_str,
                'subject': subject,
                'from': from_name,
                'date': date_str
            }

            if show_full:
                result['body'] = get_message_body(imap, msg_id)

            results.append(result)

        return results


def format_results(results, as_json=False):
    """Format search results for display."""
    if as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print("No matching messages found.")
        return

    print(f"Found {len(results)} matching message(s):\n")
    print("=" * 60)

    for i, msg in enumerate(results, 1):
        print(f"{i}. [{msg['id']}] {msg.get('date', 'No date')}")
        print(f"   From: {msg['from']}")
        print(f"   Subject: {msg['subject']}")

        if 'body' in msg and msg['body']:
            # Show first 500 chars of body
            body_preview = msg['body'][:500].replace('\n', ' ')
            if len(msg['body']) > 500:
                body_preview += "..."
            print(f"   Body: {body_preview}")

        print()


def main():
    parser = argparse.ArgumentParser(description="Search IMAP mailbox")
    parser.add_argument('--mailbox', default='shared/odroid', help='Mailbox name')
    parser.add_argument('--since', help='Start date (IMAP format, e.g., "01-Oct-2025")')
    parser.add_argument('--before', help='End date (IMAP format)')
    parser.add_argument('--keyword', help='Search keyword')
    parser.add_argument('--subject', action='store_true', help='Search subject only')
    parser.add_argument('--unseen', action='store_true', help='Only unread messages')
    parser.add_argument('--max', type=int, default=50, help='Max results')
    parser.add_argument('--full', action='store_true', help='Show full message body')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    results = search_mailbox(
        mailbox=args.mailbox,
        since=args.since,
        before=args.before,
        keyword=args.keyword,
        subject_only=args.subject,
        unseen=args.unseen,
        max_results=args.max,
        show_full=args.full
    )

    format_results(results, as_json=args.json)


if __name__ == "__main__":
    main()
