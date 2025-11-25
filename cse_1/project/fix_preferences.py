"""
Quick fix for preferences - make them HARD constraints instead of soft
"""

with open('app/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the preference section and rewrite it to use hard constraints
in_pref_section = False
new_lines = []
skip_until = -1

for i, line in enumerate(lines):
    if i < skip_until:
        continue
        
    # Find where the old preference code starts
    if '# --- Objective: Preferences ---' in line:
        # Replace with hard constraint version
        new_lines.append('    # --- Preferences as HARD Constraints ---\n')
        new_lines.append('    # If a preference is specified, FORCE allocation at that time\n')
        new_lines.append('    for r_idx, req in enumerate(theory_reqs):\n')
        new_lines.append('        prefs = req.get("prefs", {})\n')
        new_lines.append('        for d in DAYS:\n')
        new_lines.append('            if d in prefs and prefs[d]:\n')
        new_lines.append('                try:\n')
        new_lines.append('                    pref_period = int(prefs[d])\n')
        new_lines.append('                    if pref_period in TEACHING_PERIODS:\n')
        new_lines.append('                        # HARD constraint: this class MUST be at this time\n')
        new_lines.append('                        model.Add(theory_vars[(r_idx, d, pref_period)] >= 1)\n')
        new_lines.append('                        print(f"[PREF] Locked {req[\'subject\']} to {d} period {pref_period}")\n')
        new_lines.append('                except (ValueError, TypeError):\n')
        new_lines.append('                    pass\n')
        new_lines.append('\n')
        
        # Skip old preference code
        skip_until = i + 1
        while skip_until < len(lines) and '# --- Solve ---' not in lines[skip_until]:
            skip_until += 1
        continue
    
    new_lines.append(line)

# Write back
with open('app/views.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("[OK] Fixed preferences to use HARD constraints!")
print("Now when you specify a day/time, the class WILL be scheduled there.")
