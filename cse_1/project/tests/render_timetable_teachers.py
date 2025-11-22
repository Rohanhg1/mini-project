import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()

from django.forms import formset_factory
from django.template.loader import render_to_string
from app.forms import TeacherForm

# build formset exactly how the view does it
total = 7
TeacherFormSet = formset_factory(TeacherForm, extra=0, max_num=total)
formset = TeacherFormSet(prefix='teachers', initial=[{}] * total)

context = {'formset': formset, 'total': total}
html = render_to_string('app/timetable_teachers.html', context)

out = os.path.join(os.path.dirname(__file__), 'rendered_timetable_teachers.html')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write(html)
print('wrote', out)
