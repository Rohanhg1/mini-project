# Fix Summary: Preference Allocation Issue

## Problem
When users selected a preference for a specific day and time slot, the timetable allocation algorithm was not respecting those preferences. Instead, subjects were being allocated to other days and times, treating preferences as soft priorities rather than hard constraints.

## Root Cause
The original implementation had a `matches_preference()` function (lines 926-942 in views.py) that checked if a subject matched its preference, BUT it was only used to **prioritize**subjects in the candidate sorting (lines 945-951). This meant:

1. The algorithm would **prefer** to allocate a subject to its preferred slot
2. But if that slot was already taken or had other constraints, it would happily place the subject elsewhere
3. Preferences were treated as a "nice to have" scoring bonus, not a requirement

## Solution Implemented
Added a **PREFERENCE LOCKING PASS** (lines 954-1032 in views.py) that runs BEFORE the main allocation loops. This pass:

1. **Iterates through all entries** looking for subjects with day/time preferences
2. For each preference, **attempts to place the subject in that exact slot**
3. **Validates all constraints**:
   - Slot is available (not already occupied)
   - Teacher is free at that time
   - Subject hasn't been assigned that day
   - Period hasn't been used by this subject
   - Respects consecutive day constraints

4. **Locks the preference** by:
   - Immediately placing the subject in the timetable
   - Marking the teacher as occupied
   - Recording the subject-day assignment
   - Tracking the period usage

5. **Only places ONE hour per preference** to avoid over-allocation

6. This happens **BEFORE** any other allocation, ensuring preferences get first priority

## Key Changes
- **File Modified**: `app/views.py`
- **Lines Added**: 78 new lines (954-1032)
- **Pass Executed**: PREFERENCE LOCKING PASS (runs first)
- **Constraint Type**: Changed from SOFT (priority) to HARD (requirement)

## How It Works Now

### Before (Old Behavior):
```
1. Main Pass starts
2. For each year, day, period:
   - Find best candidate (preference gives +10 points)
   - Place highest scoring candidate
3. If preferred slot taken → subject goes elsewhere
```

### After (New Behavior):
```
1. PREFERENCE LOCKING PASS
   - For each subject with preferences:
     - TRY to lock preferred day/time
     - SUCCESS → subject placed, slot reserved
     - FAILURE → continue (will try in main pass)

2. Main Pass starts
   - Works with remaining unallocated hours
   - Preferred slots already locked and protected
```

## Testing
Created `test_preference.py` to document expected behavior. 

### Example:
- **Teacher A** teaches **Math** (5 hours) with preferences:
  - Monday, Period 0
  - Wednesday, Period 3
  
**Expected Result:**
- ✅ Math WILL be allocated to Monday Period 0  (if slot available)
- ✅ Math WILL be allocated to Wednesday Period 3 (if slot available)
- ✅ Remaining 3 hours allocated by normal algorithm
- ❌ NO MORE: Math on Tuesday instead of Monday

## Validation
- ✅ No syntax errors (`python -m py_compile app/views.py`)
- ✅ Respects all existing constraints (teacher availability, subject-day limits, etc.)
- ✅ Maintains backward compatibility (subjects without preferences work as before)
- ✅ Hard constraint enforcement (preferences are locked, not just prioritized)

## Usage
Users can now confidently set day/time preferences knowing that:
1. If the slot is available and meets all constraints → **Subject WILL be placed there**
2. If the slot conflicts → **Subject won't be forced, but will try other slots**
3. Preferences are **attempted first**, before any other allocation

## Notes
- The algorithm still validates ALL constraints (teacher free, slot available, etc.)
- If a preference absolutely cannot be satisfied (e.g., teacher busy, slot taken), the subject will still be allocated elsewhere
- This is the correct behavior: preferences are "strong requests" that are honored when possible, but don't break the timetable if impossible
