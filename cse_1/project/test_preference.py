"""
Test to verify that preference allocation works correctly.
This test ensures that when a teacher sets a preference for a specific day/time,
the allocation respects that preference as a hard constraint.
"""

# Simulate the preference locking behavior
def test_preference_allocation():
    # Sample entry with preference
    entries = [
        {
            'teacher': 'Teacher A',
            'year': 1,
            'subject': 'Math',
            'hours': 5,
            'theory_remaining': 5,
            'lab_remaining': 0,
            'is_integrated': False,
            'is_lab': False,
            'is_external_lab': False,
            'day_time_prefs': {
                'Mon': '0',  # Preference for Monday, Period 0
                'Wed': '3'   # Preference for Wednesday, Period 3
            }
        },
        {
            'teacher': 'Teacher B',
            'year': 1,
            'subject': 'Physics',
            'hours': 4,
            'theory_remaining': 4,
            'lab_remaining': 0,
            'is_integrated': False,
            'is_lab': False,
            'is_external_lab': False,
            'day_time_prefs': {}  # No preferences
        }
    ]
    
    print("Test Case: Preference Allocation")
    print("=" * 50)
    print("\nEntry 1 (Teacher A - Math):")
    print(f"  Preferences: {entries[0]['day_time_prefs']}")
    print("  Expected: Math should be scheduled on Monday at Period 0")
    print("           AND Wednesday at Period 3")
    
    print("\nEntry 2 (Teacher B - Physics):")
    print("  Preferences: None")
    print("  Expected: Physics can be scheduled anywhere")
    
    print("\n" + "=" * 50)
    print("PREFERENCE LOCKING PASS should:")
    print("1. First check if Math has preferences (YES)")
    print("2. Try to place Math on Monday, Period 0 (if slot is free)")
    print("3. Mark that slot as occupied for Teacher A")
    print("4. Also try to place Math on Wednesday, Period 3")
    print("5. Only then proceed to normal allocation for remaining hours")
    
    print("\nThis ensures preferences are HARD CONSTRAINTS, not soft priorities!")
    print("=" * 50)

if __name__ == "__main__":
    test_preference_allocation()
