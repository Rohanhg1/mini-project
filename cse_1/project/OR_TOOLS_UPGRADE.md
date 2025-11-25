# ARCHITECTURE UPGRADE: Google OR-Tools

## Overview
I have completely replaced the previous heuristic-based allocation algorithm with a **Constraint Programming (CP)** model using **Google OR-Tools**.

## Why this change?
The previous approach (Greedy + Smart Overrides) was prone to edge-case bugs like "Double Booking" because it made decisions sequentially without seeing the full picture.

**OR-Tools** solves the problem globally. It translates the timetable requirements into a set of mathematical equations and solves them simultaneously.

## Guarantees
The new solver strictly enforces:
1.  **Teacher Availability:** A teacher is never assigned >1 class at the same time.
2.  **Rest Periods:** If a teacher teaches a class, the next period is strictly blocked for them.
3.  **Lab Integrity:** Labs are always scheduled in valid blocks (e.g., periods 0-1, 3-4) and never split.
4.  **One Class Per Slot:** No two subjects can occupy the same room/time for a semester.

## How to Test
1.  **Restart the Django Server** (Crucial, as code changed significantly).
2.  **Generate Timetable**.
3.  **Check Console:** You will see `✅ OR-Tools found a solution!` if successful.
4.  **Verify Output:** The timetable should be 100% conflict-free.

## Troubleshooting
If the solver prints `❌ OR-Tools FAILED`, it means the constraints are **mathematically impossible** to satisfy (e.g., a teacher has 30 hours of work but only 20 slots available). In that case, reduce the constraints or hours.
