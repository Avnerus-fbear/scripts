#!/usr/bin/env python3
"""Check calendar events for the upcoming week."""

import urllib.request
import urllib.error
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import base64
import re

# CalDAV settings (loaded from secrets)
from credentials import creds
CALDAV_URL = creds['Caldav_URL']
USERNAME = creds['Caldav_USER']
PASSWORD = creds['Caldav_PASS']

def parse_ics_datetime(ics_str, local_tz=None):
    """Parse iCalendar datetime format with timezone support.
    Handles both datetime (19961027T040000) and date-only (20260619) values.
    Accepts full property lines like 'DTSTART;VALUE=DATE:20260619' or raw values."""
    if local_tz is None:
        local_tz = ZoneInfo("Europe/Helsinki")  # EET/EEST
    
    ics_str = ics_str.strip()
    
    # Extract the actual value part (after DTSTART;params:)
    # The value is everything after the last colon that follows the property name
    if ics_str.startswith("DTSTART"):
        # Remove DTSTART and any parameters (e.g., DTSTART;VALUE=DATE;TZID=...)
        val_part = ics_str.split(":", 1)[1] if ":" in ics_str else ics_str
        # Handle cases where TZID contains colons (shouldn't but be safe)
        if "TZID=" in ics_str:
            # Value is after the TZID value's colon
            idx = ics_str.index("TZID=")
            # Find the colon after the TZID value
            after_tzid = ics_str[idx + 5:]  # skip "TZID="
            # TZID value ends at the next colon
            tzid_end = after_tzid.index(":")
            val_part = after_tzid[tzid_end + 1:]
    else:
        val_part = ics_str
    
    dt = None
    tzinfo = None
    is_date_only = "VALUE=DATE" in ics_str
    
    # Check for timezone identifier (TZID=...)
    tz_match = re.search(r'TZID=([^:;]+)', ics_str)
    if tz_match:
        tz_name = tz_match.group(1)
        tz_mapping = {
            "FLE Standard Time": "Europe/Helsinki",
            "FLE Daylight Time": "Europe/Helsinki",
            "Central Europe Standard Time": "Europe/Budapest",
            "Central Europe Daylight Time": "Europe/Budapest",
            "Eastern Standard Time": "America/New_York",
            "Eastern Daylight Time": "America/New_York",
            "Pacific Standard Time": "America/Los_Angeles",
            "Pacific Daylight Time": "America/Los_Angeles",
        }
        iana_tz = tz_mapping.get(tz_name, tz_name)
        try:
            tzinfo = ZoneInfo(iana_tz)
        except:
            pass
    elif "Z" in val_part:
        tzinfo = ZoneInfo("UTC")
        val_part = val_part.replace("Z", "")
    
    # Parse the datetime
    if len(val_part) >= 14 and "T" in val_part:
        try:
            dt = datetime.strptime(val_part[:19], "%Y%m%dT%H%M%S")
            if tzinfo:
                dt = dt.replace(tzinfo=tzinfo)
                dt = dt.astimezone(local_tz)
        except ValueError:
            pass
    elif len(val_part) >= 8 and (is_date_only or "T" not in val_part):
        # Date-only value (e.g., 20260619)
        try:
            dt = datetime.strptime(val_part[:8], "%Y%m%d")
            dt = dt.replace(tzinfo=local_tz)
        except ValueError:
            pass
    
    return dt

def parse_rrule(rrule_str, dtstart, end_date):
    """Parse RRULE and generate all occurrence dates."""
    if not rrule_str or "FREQ=" not in rrule_str:
        return []
    
    from datetime import date
    import re
    
    # Parse RRULE components
    freq = None
    byday = None
    interval = 1
    count = None
    until = None
    
    for part in rrule_str.split(";"):
        if part.startswith("FREQ="):
            freq = part.split("=")[1]
        elif part.startswith("BYDAY="):
            byday = part.split("=")[1]
        elif part.startswith("INTERVAL="):
            interval = int(part.split("=")[1])
        elif part.startswith("COUNT="):
            count = int(part.split("=")[1])
        elif part.startswith("UNTIL="):
            until_str = part.split("=")[1]
            until = parse_ics_datetime(until_str)
    
    if not freq:
        return []
    
    occurrences = []
    
    # Handle weekly frequency
    if freq == "WEEKLY" and byday:
        day_map = {
            "MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6
        }
        target_weekday = day_map.get(byday)
        if target_weekday is not None:
            # Get the weekday of dtstart (convert to date)
            dtstart_date = dtstart.date() if hasattr(dtstart, 'date') else dtstart
            
            # Find the first occurrence on or after dtstart_date that matches the target weekday
            days_until_target = (target_weekday - dtstart_date.weekday()) % 7
            current = dtstart_date + timedelta(days=days_until_target)
            
            while current <= end_date.date():
                # Check if current occurrence falls on the target weekday
                if current.weekday() == target_weekday:
                    occurrences.append(current)
                if count and len(occurrences) >= count:
                    break
                current += timedelta(weeks=interval)
    
    return occurrences

def format_weekday_name(dtstart_str):
    """Get the weekday name from DTSTART."""
    dt = parse_ics_datetime(dtstart_str)
    if dt:
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return weekdays[dt.weekday()]
    return ""

def unfold_ics_lines(ics_content):
    """Unfold iCalendar lines (RFC 5545 line folding).
    Lines starting with space/tab are continuations of the previous line."""
    raw_lines = ics_content.replace("\r\n", "\n").split("\n")
    unfolded = []
    for line in raw_lines:
        if line and (line[0] == ' ' or line[0] == '\t') and unfolded:
            # Continuation of previous line
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def parse_ics_events(ics_content, start_date, end_date):
    """Parse events from iCalendar content."""
    events = []
    lines = unfold_ics_lines(ics_content)
    
    in_event = False
    current_event = {}
    in_timezone = False
    
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            current_event = {}
        elif line == "END:VEVENT":
            if in_event:
                # Parse dtstart
                dtstart = None
                is_date_only = False
                if "dtstart" in current_event:
                    dtstart = parse_ics_datetime(current_event["dtstart"])
                    is_date_only = current_event.get("date_only", False)
                
                rrule = current_event.get("rrule", "")
                
                # If we have an RRULE, expand occurrences
                if dtstart and rrule:
                    occurrence_dates = parse_rrule(rrule, dtstart, end_date)
                    for occ_date in occurrence_dates:
                        if start_date.date() <= occ_date <= end_date.date():
                            occurrence_event = current_event.copy()
                            occurrence_event["occurrence_date"] = occ_date
                            events.append(occurrence_event)
                # Otherwise check if single event is in range
                elif dtstart:
                    # Convert start_date and end_date to timezone-aware for comparison
                    start_aware = start_date.replace(tzinfo=ZoneInfo("Europe/Helsinki"))
                    end_aware = end_date.replace(hour=23, minute=59, second=59, tzinfo=ZoneInfo("Europe/Helsinki"))
                    # Check if event overlaps the range: dtstart must be before end AND dtend must be after start
                    # (handles events that started before the range but are still ongoing)
                    dtend = None
                    if "dtend" in current_event:
                        dtend = parse_ics_datetime(current_event["dtend"])
                        # Ensure dtend is timezone-aware for comparison
                        if dtend and dtend.tzinfo is None:
                            dtend = dtend.replace(tzinfo=ZoneInfo("Europe/Helsinki"))
                    if dtstart <= end_aware and (dtend is None or dtend >= start_aware):
                        events.append(current_event)
                in_event = False
        elif line == "BEGIN:VTIMEZONE":
            in_timezone = True
        elif line == "END:VTIMEZONE":
            in_timezone = False
        elif in_event and not in_timezone:
            if line.startswith("SUMMARY:"):
                current_event["summary"] = line[8:]
            elif line.startswith("DTSTART"):
                # Store the full line (includes VALUE=DATE, TZID, etc.)
                current_event["dtstart"] = line
                # Extract the raw value after the last colon
                if ":" in line:
                    raw_val = line.split(":", 1)[1]
                    # Handle cases like "DTSTART;VALUE=DATE:20260619"
                    if ":" in raw_val:
                        raw_val = raw_val.split(":", 1)[1]
                    current_event["dtstart_raw"] = raw_val
                if "VALUE=DATE" in line:
                    current_event["date_only"] = True
            elif line.startswith("DTEND"):
                current_event["dtend"] = line.split(":", 1)[1] if ":" in line else ""
            elif line.startswith("LOCATION:"):
                current_event["location"] = line[9:]
            elif line.startswith("DESCRIPTION:"):
                current_event["description"] = line[12:]
            elif line.startswith("RRULE:"):
                current_event["rrule"] = line[6:]
            elif line.startswith("ATTENDEE"):
                # Parse ATTENDEE lines (e.g. ATTENDEE;CN=Name;RSVP=TRUE:mailto:email@domain.com)
                if "mailto:" in line:
                    email = line.split("mailto:")[1].split(";")[0].split('"')[0].strip()
                    # Extract display name from CN= parameter
                    cn_match = re.search(r'CN=([^;:]+)', line)
                    display_name = cn_match.group(1).strip() if cn_match else None
                    if "attendees" not in current_event:
                        current_event["attendees"] = []
                    current_event["attendees"].append({"email": email, "name": display_name})
    
    return events

def get_calendar_events(start_date, end_date):
    """Fetch calendar events for the given date range."""
    caldav_url = f"{CALDAV_URL}"
    
    # Build iCalendar time range query
    start_str = start_date.strftime("%Y%m%dT000000Z")
    end_str = end_date.strftime("%Y%m%dT235959Z")
    
    calendar_query = f"""<?xml version="1.0" encoding="utf-8" ?>
<C:calendar-query xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop xmlns:D="DAV:">
    <D:getetag/>
    <C:calendar-data/>
  </D:prop>
  <C:filter>
    <C:comp-filter name="VCALENDAR">
      <C:comp-filter name="VEVENT">
        <C:time-range start="{start_str}" end="{end_str}"/>
      </C:comp-filter>
    </C:comp-filter>
  </C:filter>
</C:calendar-query>"""
    
    try:
        # Create request with authentication
        credentials = f"{USERNAME}:{PASSWORD}"
        auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()
        
        req = urllib.request.Request(
            caldav_url,
            data=calendar_query.encode('utf-8'),
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
                "Accept": "text/xml",
                "Authorization": auth_header
            },
            method="REPORT"
        )
        
        response = urllib.request.urlopen(req, timeout=30)
        return response.read().decode('utf-8')
        
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return None

def format_events_for_display(events, start_date, end_date):
    """Format events for display."""
    if not events:
        return f"No calendar events from {start_date.strftime('%B %d')} to {end_date.strftime('%B %d')}.\n"
    
    # Sort events by occurrence_date (sooner to later), then by time
    def sort_key(event):
        occurrence_date = event.get("occurrence_date", None)
        dtstart = event.get("dtstart", "")
        dt = parse_ics_datetime(dtstart)
        
        # Use local timezone for time comparison
        if dt and hasattr(dt, 'time'):
            time_val = dt.time()
            date_for_sort = dt.date()
        else:
            time_val = None
            date_for_sort = None
        
        if occurrence_date:
            return (occurrence_date, time_val if time_val else (0, 0, 0))
        elif date_for_sort:
            return (date_for_sort, time_val if time_val else (0, 0, 0))
        else:
            return (date.max, (23, 59, 59))
    
    sorted_events = sorted(events, key=sort_key)
    
    lines = [f"📅 **Calendar Events ({start_date.strftime('%B %d')} - {end_date.strftime('%B %d')})**\n"]
    
    for event in sorted_events:
        summary = event.get("summary", "No title")
        dtstart = event.get("dtstart", "")
        dtend = event.get("dtend", "")
        location = event.get("location", "")
        description = event.get("description", "")
        rrule = event.get("rrule", "")
        occurrence_date = event.get("occurrence_date", None)
        attendees = event.get("attendees", [])
        
        # Format time if available
        time_str = ""
        weekday_str = ""
        today_str = ""
        is_all_day = False
        if dtstart:
            dt = parse_ics_datetime(dtstart)
            if dt:
                # Check if this is an all-day event (VALUE=DATE)
                if "VALUE=DATE" in dtstart:
                    is_all_day = True
                else:
                    time_str = dt.strftime("%H:%M")
                weekday_str = format_weekday_name(dtstart)
                # Use occurrence_date if available (for recurring events), otherwise use dtstart
                check_date = occurrence_date if occurrence_date else dt.date()
                # Check if this event is happening today
                if check_date == start_date.date():
                    today_str = " (Today)"
        
        # Clean up location (unescape ICS backslashes)
        clean_location = location.replace("\\,", ",").replace("\\", "") if location else ""
        
        line = f"- **{summary}**"
        if today_str:
            line += today_str
        elif weekday_str:
            line += f" ({weekday_str})"
        if time_str and not is_all_day:
            line += f" {time_str}"
        if clean_location:
            line += f" @ {clean_location}"
        if attendees:
            # Filter out self (avnerus/softrobot/fattybear) and format names
            self_ids = {"avnerus", "softrobot@avner.us", "fattybear@avner.us", "fattybear"}
            others = []
            for att in attendees:
                att_email = att["email"] if isinstance(att, dict) else att
                if att_email.lower() in self_ids:
                    continue
                if isinstance(att, dict) and att.get("name"):
                    others.append(att["name"])
                elif "@" in att_email:
                    local = att_email.split("@")[0]
                    # Clean up dot-separated names
                    others.append(local.replace(".", " ").title())
                else:
                    others.append(att_email)
            if others:
                line += f" (👤 {', '.join(others)})"
        lines.append(line)
    
    return "\n".join(lines) + "\n"

def main():
    today = datetime.now()
    
    # Get current day and next 6 days (total 7 days)
    start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=6)
    
    print(f"📅 Checking calendar events from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...\n")
    
    xml_response = get_calendar_events(start_date, end_date)
    
    if xml_response:
        # Extract calendar-data content
        events = []
        if "calendar-data" in xml_response:
            # Find all calendar-data blocks
            for match in re.finditer(r'<C:calendar-data[^>]*>(.*?)</C:calendar-data>', xml_response, re.DOTALL):
                ics_content = match.group(1)
                events.extend(parse_ics_events(ics_content, start_date, end_date))
        
        if events:
            output = format_events_for_display(events, start_date, end_date)
            print(output)
            # Also return for cron output
            return output
        else:
            result = "No calendar events found for the upcoming week.\n"
            print(result)
            return result
    else:
        result = "No calendar events found for the upcoming week.\n"
        print(result)
        return result

if __name__ == "__main__":
    result = main()
