# DEBUGGING PREFERENCE ALLOCATION - INSTRUCTIONS

## What I Added
I've added detailed debug logging to the PREFERENCE LOCKING PASS in `app/views.py`. 
This will show you EXACTLY what's happening when the system tries to lock preferences.

## How to Test

### Step 1: Start Your Django Server
```bash
cd "c:\Users\Rohan H G\OneDrive\Desktop\mini project\cse_1\project"
python manage.py runserver
```

### Step 2: Create a Timetable with Preferences
1. Go to your timetable generation page
2. Add a teacher/subject
3. **Set a preference** (e.g., Monday, Period 0)
4. Click "Generate Timetable"

### Step 3: Check the Console Output
Look at the terminal/console where Django is running. You should see output like:

```
=== PREFERENCE LOCKING PASS DEBUG ===

=== Processing Math (Year 1, Teacher: John) ===
    Preferences: {'Mon': '0', 'Wed': '3'}
    Theory remaining: 5
  Trying preference: Mon at period 0
    ✅ SUCCESS: Placed Math on Mon at period 0
```

OR if it fails, you'll see WHY:

```
=== Processing Math (Year 1, Teacher: John) ===
    Preferences: {'Mon': '0'}
    Theory remaining: 5
  Trying preference: Mon at period 0
    ❌ SKIP: Period 0 not in schedulable indices [0, 1, 3, 4, 6, 7, 8]
```

## What Each Error Means

### ❌ SKIP: No time specified
- The preference day was set but no time/period was selected

### ❌ SKIP: Invalid period format
- The period value couldn't be converted to a number

### ❌ SKIP: Day not in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
- The preference day name doesn't match the expected format
- **COMMON ISSUE**: Check if your form is sending "Monday" instead of "Mon"

### ❌ SKIP: Period X not in schedulable indices
- The period number is invalid (e.g., period 2, 5, or 9+ don't exist)
- Valid periods are: 0, 1, 3, 4, 6, 7, 8

### ❌ SKIP: Slot already occupied
- Another subject already took this slot in an earlier pass
- This shouldn't happen in PREFERENCE LOCKING (it runs first)

### ❌ SKIP: Teacher not free
- The teacher is already teaching something else at this time
- Multiple subjects for same teacher with same preference

### ❌ SKIP: Subject already assigned on this day
- The subject is already scheduled on this day (one per day rule)

### ❌ SKIP: Period already used by subject
- This subject already used this period number another day

## Next Steps

1. **Run the test** and capture the console output
2. **Share the debug output** with me - it will show exactly why preferences aren't working
3. Based on the output, we can:
   - Fix data format issues (e.g., "Monday" vs "Mon")
   - Fix period number mapping
   - Identify constraint conflicts
   - Adjust the logic as needed

## Quick Check: Data Format
The preferences should be stored as JSON like this:
```json
{
  "Mon": "0",
  "Wed": "3",
  "Fri": "6"
}
```

NOT like this:
```json
{
  "Monday": "Period 1",
  "Wednesday": "Period 4"
}
```

The key must be: "Mon", "Tue", "Wed", "Thu", or "Fri"
The value must be: "0", "1", "3", "4", "6", "7", or "8" (as strings)

## Run and Report Back!
After you generate a timetable with preferences, copy and paste the **console output** here so I can see exactly what's happening!
