# Timetable Constraint Updates

## Changes Made
Date: 2025-11-25

## ⚠️ IMPORTANT: Theory Hours for Integrated Subjects

**Key Rule**: When a subject is **integrated** (whether or not it's also external), the `hours` field represents **ONLY theory hours**. Lab allocation happens **separately** and does **NOT** consume theory hours.

**Examples**:
- Subject with `hours=5`, `integrated=True`: Gets **5 theory periods** + **1 lab block** (2 periods)
- Subject with `hours=3`, `integrated=True`, `external=True`: Gets **3 theory periods** + **1 lab block** (3 periods)
- Subject with `hours=4`, `integrated=False`, `is_lab=False`: Gets **4 theory periods** only

**Code Location**: Lines 798-822 in `views.py`

### New Constraints Added

#### 1. Integrated + External Labs → 2:30-5:00 PM Only (Constraint C5)

**Requirement**: If a subject is both integrated AND external, its lab must always be scheduled only between 2:30 PM – 5:00 PM.

**Implementation**:
- Added `is_integrated` and `is_external_lab` flags to the `lab_reqs` dictionary
- Created constraint C5 that forces labs marked as both integrated AND external to only start at period 6
- Period 6 corresponds to the 2:30-5:00 PM time slot (periods 6, 7, 8)

**Code Location**: Lines 892-902 in `views.py`

```python
# C5. Integrated + External Labs MUST be in 2:30-5:00 PM slot (period 6 start only)
for r_idx, req in enumerate(lab_reqs):
    if req.get('is_integrated') and req.get('is_external_lab'):
        # Force all non-period-6 starts to be 0
        valid_starts = [0, 3, 6, 7] if req['duration'] == 2 else [0, 3, 6]
        for d in DAYS:
            for p in valid_starts:
                if p != 6:  # Only period 6 is allowed
                    model.Add(lab_vars[(r_idx, d, p)] == 0)
```

#### 1b. Integrated-Only Labs → Morning/Midday Only (Constraint C5b)

**Requirement**: If a subject is ONLY integrated (integrated=True but external=False), its lab must be scheduled only in the morning or midday slots: 9:00-11:00 or 11:15-1:15.

**Implementation**:
- Created constraint C5b that restricts integrated-only labs to start at period 0 or period 3 only
- Period 0 = 9:00-11:00 slot
- Period 3 = 11:15-1:15 slot
- This prevents integrated-only labs from appearing in the afternoon (2:30-5:00 PM)

**Code Location**: Lines 904-915 in `views.py`

```python
# C5b. Integrated-ONLY Labs (not external) MUST be in morning/midday slots
for r_idx, req in enumerate(lab_reqs):
    if req.get('is_integrated') and not req.get('is_external_lab'):
        # Force afternoon start periods (6, 7) to be 0
        valid_starts = [0, 3, 6, 7] if req['duration'] == 2 else [0, 3, 6]
        for d in DAYS:
            for p in valid_starts:
                if p not in [0, 3]:  # Only periods 0 and 3 are allowed
                    model.Add(lab_vars[(r_idx, d, p)] == 0)
```


#### 2. One Theory Class Per Subject Per Day (Constraint C6)

**Requirement**: For every subject in a particular semester, allow only one theory class to be allocated for that subject per day (not more than one).

**Implementation**:
- Group all theory requirements by (year, subject)
- For each unique subject-year combination, add a constraint that limits theory classes to at most 1 per day
- This prevents the same subject from appearing multiple times in a single day's schedule

**Code Location**: Lines 917-933 in `views.py`

```python
# C6. Only one theory class per subject per day
subject_theory_map = {}  # (year, subject) -> [list of r_idx]
for r_idx, req in enumerate(theory_reqs):
    key = (req['year'], req['subject'])
    if key not in subject_theory_map:
        subject_theory_map[key] = []
    subject_theory_map[key].append(r_idx)

# For each subject, ensure at most 1 theory class per day
for (year, subject), req_indices in subject_theory_map.items():
    for d in DAYS:
        day_vars = []
        for r_idx in req_indices:
            for p in TEACHING_PERIODS:
                day_vars.append(theory_vars[(r_idx, d, p)])
        model.Add(sum(day_vars) <= 1)
```

#### 3. Morning Periods Must Be Filled (Constraint C7)

**Requirement**: For every semester, on every working day, the first 3 teaching periods (morning session) must be completely filled with no empty slots.

**Implementation**:
- Identifies the first 3 teaching periods: Period 0 (9:00-10:00), Period 1 (10:00-11:00), Period 3 (11:15-12:15)
- Note: Period 2 is the break, so it's skipped
- For each semester, each day, and each morning period, ensures at least one class is scheduled
- This eliminates "Tutorial" placeholders in morning slots
- Forces efficient use of morning time when students are most alert

**Code Location**: Lines 1009-1044 in `views.py`

```python
# C7. Morning Periods Must Be Filled
MORNING_PERIODS = [0, 1, 3]

for y in years:
    for d in DAYS:
        for p in MORNING_PERIODS:
            # At least one class must be scheduled in this morning period
            active_vars = []
            
            # Collect all theory and lab vars for this year/day/period
            for r_idx, req in enumerate(theory_reqs):
                if req['year'] == y:
                    active_vars.append(theory_vars[(r_idx, d, p)])
            
            # Also check labs that cover this period
            for r_idx, req in enumerate(lab_reqs):
                if req['year'] == y:
                    # ... (check if lab covers period p)
                    if covers_p:
                        active_vars.append(lab_vars[(r_idx, d, start)])
            
            # Constraint: Morning period MUST have at least 1 class
            model.Add(sum(active_vars) >= 1)
```

#### 4. Afternoon Periods Must Be Filled in Order (Constraint C8)

**Requirement**: Afternoon periods must be filled sequentially from period 6 onwards - no irregular patterns allowed. Classes must start from period 6 and continue in order.

**Implementation**:
- Afternoon periods are: Period 6 (2:30-3:20), Period 7 (3:20-4:15), Period 8 (4:15-5:00)
- **Rule 1**: If period 7 is occupied, period 6 MUST also be occupied
- **Rule 2**: If period 8 is occupied, period 7 MUST also be occupied
- Combined effect: If period 8 is occupied, both 6 AND 7 must be occupied (P8 ⇒ P7 ⇒ P6)
- This enforces sequential filling from left to right

**Valid Afternoon Patterns** ✅:
  - **Empty**: No afternoon classes at all
  - **[P6 only]**: One class at 2:30-3:20
  - **[P6, P7]**: Two classes, 2:30-4:15 (continuous)
  - **[P6, P7, P8]**: Full afternoon, 2:30-5:00 (continuous)

**Invalid Patterns** ✗:
  - **[P7 only]**: Starts at 3:20 without filling 2:30 slot first
  - **[P8 only]**: Starts at 4:15 without filling earlier slots
  - **[P7, P8]**: Starts at 3:20 without filling 2:30 slot first
  - **[P6, P8]**: Has gap at 3:20 (period 7)

**Code Location**: Lines 1046-1135 in `views.py`

```python
# C8. Afternoon Periods Must Be Filled in Order (Sequential)
AFTERNOON_PERIODS = [6, 7, 8]

for y in years:
    for d in DAYS:
        # Create boolean indicators for each period
        period_6_occupied = model.NewBoolVar(f'P6_occupied_Y{y}_D{d}')
        period_7_occupied = model.NewBoolVar(f'P7_occupied_Y{y}_D{d}')
        period_8_occupied = model.NewBoolVar(f'P8_occupied_Y{y}_D{d}')
        
        # Constraint 1: If period 7 is occupied, period 6 MUST be occupied
        # P7 => P6  (equivalent to: NOT P7 OR P6)
        model.AddBoolOr([period_7_occupied.Not(), period_6_occupied])
        
        # Constraint 2: If period 8 is occupied, period 7 MUST be occupied
        # P8 => P7  (equivalent to: NOT P8 OR P7)
        model.AddBoolOr([period_8_occupied.Not(), period_7_occupied])
        
        # Combined: P8 => P7 => P6 (sequential filling enforced)
```

## Testing Recommendations

1. **Test Integrated + External Labs (C5)**:
   - Create a subject with both `integrated_y1=True` AND `external_y1=True`
   - Verify that the lab appears only in the 2:30-5:00 PM slot (periods 6, 7, 8)
   - It should NOT appear in morning (9:00-11:00) or midday (11:15-1:15) slots

2. **Test Integrated-Only Labs (C5b)**:
   - Create a subject with `integrated_y1=True` but `external_y1=False` (uncheck external)
   - Verify that the lab appears ONLY in morning (9:00-11:00) OR midday (11:15-1:15) slots
   - It should NOT appear in the afternoon (2:30-5:00 PM) slot

3. **Test One Theory Per Day (C6)**:
   - Create a subject with multiple theory hours (e.g., 5 hours)
   - Generate the timetable
   - Verify that the subject appears at most once per day across all days
   - Example: If "Mathematics" has 5 hours, it should be spread across 5 different days

4. **Test Morning Periods Filled (C7)**:
   - Generate a timetable for any semester
   - Check every day (Mon-Fri) in the generated timetable
   - Verify that periods 0, 1, and 3 (9:00-10:00, 10:00-11:00, 11:15-12:15) are ALL filled
   - There should be NO "Tutorial" placeholders in these morning slots
   - All morning periods should have actual subjects or labs scheduled

5. **Test Afternoon Sequential Filling (C8)**:
   - Generate a timetable for any semester
   - For each day, check the afternoon periods (6, 7, 8)
   - Verify that afternoon periods fill in order from period 6
   - **Valid patterns to expect**:
     * No afternoon classes (all empty) ✓
     * Period 6 only ✓
     * Periods 6 and 7 only ✓
     * Periods 6, 7, and 8 all filled ✓
   - **Invalid patterns (should NEVER occur)**:
     * Period 7 filled but period 6 empty ✗
     * Period 8 filled but period 7 or 6 empty ✗
     * Periods 7 and 8 filled but period 6 empty ✗
     * Periods 6 and 8 filled but period 7 empty ✗

## Impact on Existing Functionality

- **No breaking changes**: These are additive constraints
- **Solver performance**: May slightly increase solving time due to additional constraints
- **Solution feasibility**: Some previously valid timetables may now be infeasible if they violate these rules
- If the solver cannot find a solution, check if the new constraints make the problem over-constrained

## Period Reference

For reference, here are the period mappings:
- Period 0: 1st (9:00-10:00)
- Period 1: 2nd (10:00-11:00)
- Period 2: Break (11:00-11:15) - NOT SCHEDULABLE
- Period 3: 3rd (11:15-12:15)
- Period 4: 4th (12:15-1:15)
- Period 5: Lunch (1:15-2:30) - NOT SCHEDULABLE
- **Period 6: 5th (2:30-3:20)** ← Integrated+External labs start here
- **Period 7: 6th (3:20-4:15)**
- **Period 8: 7th (4:15-5:00)**
