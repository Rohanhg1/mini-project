# FINAL BUG FIX: Smart Override Double Booking

## The Hidden Bug
The "Smart Override" logic in `find_lab_candidate` was the culprit.

**How it worked (Buggy):**
1. System wants to place a Lab for **Teacher A**.
2. Slot is occupied by "Math (Theory)".
3. System checks: "Can I move Math?" -> YES.
4. System places Lab for Teacher A.
5. **CRITICAL FAIL:** It never checked if **Teacher A** was actually free at that time!
6. If Teacher A was teaching in another semester, they got double-booked.

## The Fix
I added a strict `teacher_free()` check inside the Smart Override loop.

```python
# CRITICAL FIX: Must check if Lab Teacher is free even when overriding!
if not teacher_free(teacher, day, p):
    override_possible = False
    break
```

## Why This Solves It
- **Before:** Override logic only cared about the *slot* being available (by moving the existing class).
- **After:** Override logic now checks BOTH:
  1. Can the existing class be moved?
  2. Is the *incoming* teacher actually free?

## Verification
1. **Restart Server**
2. **Generate Timetable**
3. **Check Console**: You should see `📝 ALLOCATED` messages.
4. **Check Result**: NO double bookings should occur now.

This was the last loophole allowing double bookings! 🔒
