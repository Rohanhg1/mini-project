# TODO: Update Timetable Generation for Integrated Subjects

## Approved Plan
- Modify `allocate_timetable_with_ga` function in `views.py` to allocate theory hours for integrated subjects as specified by the user, in addition to the lab allocation.
- Keep lab allocation: 2 hours continuous for integrated without external lab.
- PDF export already matches HTML format, no changes needed.

## Steps
1. Update normalization logic in `allocate_timetable_with_ga` for integrated subjects: set `theory_remaining` to `base_hours` (user-specified hours) instead of 0.
2. Ensure lab allocation remains: set `lab_needed` to True, and lab length based on external flag.
3. Test the timetable generation to verify theory hours are allocated correctly for integrated subjects.
4. Test PDF export to confirm it matches the HTML display format exactly.
5. If issues found, fix and re-test.

## Status
- Step 1: Completed
- Step 2: Completed
- Step 3: Completed
- Step 4: Completed
- Step 5: Completed

---

# TODO: Update Year Labels in Timetable Teachers Template

## Approved Plan
- Update the timetable_teachers_raw.html template to display actual semester numbers (e.g., 3, 5, 7 for odd semesters) instead of generic 'Year 1', 'Year 2', 'Year 3'.
- Pass year_labels and semester_type from views.py to the template context.

## Steps
1. In views.py, create year_labels dict based on semester_type (odd: {1: "3", 2: "5", 3: "7"}, even: {1: "4", 2: "6", 3: "8"}).
2. Pass year_labels and semester_type to the template context in timetable_teachers view.
3. Update template to use {{ year_labels.1 }}, {{ year_labels.2 }}, {{ year_labels.3 }} instead of "Year 1", etc.

## Status
- Step 1: Completed
- Step 2: Completed
- Step 3: Completed
