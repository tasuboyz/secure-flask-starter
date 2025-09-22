import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from datetime import datetime
from app.google_calendar import _tzinfo_from_name, get_primary_calendar_timezone

print('Testing tz helper and conversions')

# Case A: naive local wall-time + client_tz=Europe/Rome
naive_str = '2025-09-22T08:00:00'
client_tz = 'Europe/Rome'
naive = datetime.fromisoformat(naive_str)
print('\nCase A - naive wall-time (no offset), client_tz provided')
print('naive:', naive)

tz = _tzinfo_from_name(client_tz)
aware = naive.replace(tzinfo=tz)
print('aware (attached tz):', aware.isoformat())
print('UTC instant:', aware.astimezone().isoformat())

# Case B: client sent toISOString (UTC)
iso_utc = '2025-09-22T08:00:00Z'
print('\nCase B - ISO with Z (UTC)')
utc_dt = datetime.fromisoformat(iso_utc.replace('Z', '+00:00'))
print('utc_dt:', utc_dt.isoformat())
# Convert to Europe/Rome
rome = _tzinfo_from_name('Europe/Rome')
rome_dt = utc_dt.astimezone(rome)
print('rome_dt:', rome_dt.isoformat())

# Case C: AI passes naive string -> server uses calendar tz if available (simulate)
ai_naive = '2025-09-22T08:00:00'
print('\nCase C - AI naive, server calendar tz fallback')
cal_tz = 'Europe/Rome'
ai_naive_dt = datetime.fromisoformat(ai_naive)
ai_aware = ai_naive_dt.replace(tzinfo=_tzinfo_from_name(cal_tz))
print('ai_aware:', ai_aware.isoformat())
print('ai_aware UTC:', ai_aware.astimezone().isoformat())
