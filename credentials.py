#!/usr/bin/env python3
"""Load credentials from /var/run/secrets/avnerus-credentials.

Usage:
    from credentials import creds
    imap_user = creds['IMAP_USER']
    imap_pass = creds['IMAP_PASS']
    caldav_url = creds['Caldav_URL']
"""

import os

_SECRET_FILE = "/var/run/secrets/avnerus-credentials"

def _load():
    if not os.path.exists(_SECRET_FILE):
        raise FileNotFoundError(f"Credentials file not found: {_SECRET_FILE}")
    parsed = {}
    with open(_SECRET_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                parsed[key.strip()] = value.strip()
    return parsed

creds = _load()
