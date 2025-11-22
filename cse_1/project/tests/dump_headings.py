import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()
from django.forms import formset_factory
from app.forms import TeacherForm
from django.template.loader import render_to_string
import re

TeacherFormSet = formset_factory(TeacherForm, extra=0, max_num=7)
formset = TeacherFormSet(prefix='teachers', initial=[{}]*7)
html = render_to_string('app/timetable_teachers.html', {'formset': formset, 'total': 7})
headings = re.findall(r'<h4>\s*([^<]+)</h4>', html)
out = os.path.join(os.path.dirname(__file__), 'headings_out.txt')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(headings))
print('wrote', out)
