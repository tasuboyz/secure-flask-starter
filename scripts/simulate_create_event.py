import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from datetime import datetime
tz = _tzinfo_from_name('Europe/Rome')
try:
    from app.google_calendar import _tzinfo_from_name
    print('simulate ready')

    # Quick local test of tz helper
    tz = _tzinfo_from_name('Europe/Rome')
    print('tz:', tz)
    naive = datetime.fromisoformat('2025-09-22T08:00:00')
    aware = naive.replace(tzinfo=tz)
    print('aware:', aware.isoformat())
    print('utc:', aware.astimezone().isoformat())
except Exception as e:
    import traceback
    print('Error running simulate script:')
    traceback.print_exc()
