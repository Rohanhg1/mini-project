
import os
import sys
import django
from django.conf import settings

# Configure Django settings manually
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'app',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        SECRET_KEY='test_key',
    )
    django.setup()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'cse_1', 'project')))

from app.views import allocate_timetable_with_ga

def test_allocation():
    entries = [
        {
            "teacher": "T1", "year": 1, "subject": "Math", "hours": 4, 
            "is_integrated": False, "is_lab": False, "is_external_lab": False, 
            "remaining": 4, "day_time_prefs": {"Mon": "9:00-10:00"}
        },
        {
            "teacher": "T2", "year": 1, "subject": "Physics", "hours": 3, 
            "is_integrated": True, "is_lab": True, "is_external_lab": False, 
            "remaining": 3, "day_time_prefs": {}
        },
        {
            "teacher": "T3", "year": 2, "subject": "Chem Lab", "hours": 0, 
            "is_integrated": False, "is_lab": True, "is_external_lab": True, 
            "remaining": 0, "day_time_prefs": {}
        }
    ]
    
    print("Running allocation...")
    try:
        timetables, unallocated = allocate_timetable_with_ga(entries)
        print("Allocation successful!")
        print("Unallocated:", unallocated)
        # Basic check
        if timetables:
            print("Timetables generated for years:", list(timetables.keys()))
    except Exception as e:
        print(f"Error during allocation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_allocation()
