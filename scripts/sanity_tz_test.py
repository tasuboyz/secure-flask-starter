import sys
import os
from datetime import datetime

# Ensure project root is on sys.path so `import app` works when running this script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

from app.google_calendar import _tzinfo_from_name

# Simulate Europe/Rome
tz = _tzinfo_from_name('Europe/Rome')
print('tz:', tz)

naive = datetime(2025, 9, 22, 8, 0, 0)
aware = naive.replace(tzinfo=tz)
print('naive:', naive.isoformat())
print('aware:', aware.isoformat())

# Convert to UTC
print('converted (iso):', aware.astimezone(tz=None).isoformat())
