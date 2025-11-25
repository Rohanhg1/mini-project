# Script to fix Unicode emoji issues in views.py
import sys

# Read the file
with open('app/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace emojis
content = content.replace('✅ OR-Tools found a solution!', '[SUCCESS] OR-Tools found a solution!')
content = content.replace('❌ OR-Tools FAILED to find a solution', '[ERROR] OR-Tools FAILED to find a solution')

# Write back
with open('app/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed Unicode emoji issues successfully!")
