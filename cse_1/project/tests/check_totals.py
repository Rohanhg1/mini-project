import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()

from django.forms import formset_factory
from app.forms import TeacherForm
from django.template.loader import render_to_string
import re

for t in [4,5,6,7]:
    TeacherFormSet=formset_factory(TeacherForm, extra=0, max_num=t)
    formset=TeacherFormSet(prefix='teachers', initial=[{}]*t)
    forms_list=list(enumerate(formset.forms, start=1))
    html=render_to_string('app/timetable_teachers.html', {'formset':formset,'forms_list':forms_list,'total':t})
    total_match=re.search(r'name="teachers-TOTAL_FORMS" value="(\d+)"', html)
    init_match=re.search(r'name="teachers-INITIAL_FORMS" value="(\d+)"', html)
    headings=re.findall(r'<h4>\s*([^<]+)</h4>', html)
    inputs=re.findall(r'name="(teachers-\d+-[^"]+)"', html)
    print('\n=== total', t, '===')
    print('TOTAL_FORMS=', total_match.group(1) if total_match else 'N/A', 'INITIAL_FORMS=', init_match.group(1) if init_match else 'N/A')
    print('headings:', headings[:10])
    print('first 8 input names:', inputs[:8])
