import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()
from django.forms import formset_factory
from app.forms import TeacherForm
from django.test import Client

# Config
TOTAL = 7
TeacherFormSet = formset_factory(TeacherForm, extra=0, max_num=TOTAL)
formset = TeacherFormSet(prefix='teachers', initial=[{}]*TOTAL)

# Build POST data using management form values from an unbound formset
post = {}
post['teachers-TOTAL_FORMS'] = str(formset.total_form_count())
post['teachers-INITIAL_FORMS'] = str(formset.initial_form_count())
post['teachers-MIN_NUM_FORMS'] = '0'
post['teachers-MAX_NUM_FORMS'] = str(TOTAL)

# Fill teacher_name for all forms and set no years (so no hours)
for i in range(TOTAL):
    post[f'teachers-{i}-teacher_name'] = f'Teacher{i+1}'
    # leave years_handling empty; include an empty value for checkboxes not needed

# Login and set session
c = Client()
User = __import__('django.contrib.auth').contrib.auth.get_user_model()
if not User.objects.filter(username='test').exists():
    User.objects.create_user('test', password='testpass')
logged = c.login(username='test', password='testpass')
print('logged in', logged)

# Set session total_teachers so view doesn't redirect
s = c.session
s['total_teachers'] = TOTAL
s.save()

r = c.post('/timetable/teachers/', data=post)
print('POST status', r.status_code)
# Quick sanity: look for form error markers
content = r.content.decode('utf-8')
errors = 'This field' in content or 'errorlist' in content.lower()
print('has form errors (heuristic):', errors)
# Save response for inspection
out = os.path.join(os.path.dirname(__file__), 'post_teachers_response.html')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write(content)
print('wrote', out)
