import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()

from django.forms import formset_factory
from app.forms import TeacherForm

TeacherFormSet = formset_factory(TeacherForm, extra=0, max_num=7)
fs = TeacherFormSet(prefix='teachers', initial=[{}]*7)
print('total_form_count()', fs.total_form_count())
print('len(forms)', len(fs.forms))
print('management TOTAL_FORMS:', fs.management_form['TOTAL_FORMS'].value())
print('management INITIAL_FORMS:', fs.management_form['INITIAL_FORMS'].value())
for i, f in enumerate(fs.forms[:10], start=1):
    print('form index', i, 'is_bound=', f.is_bound)
    # print a short HTML snippet for the first field label
    html = f.as_p()
    print(html[:120].replace('\n',' '))
