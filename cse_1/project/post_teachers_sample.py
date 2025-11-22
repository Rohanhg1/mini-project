import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()
user, created = User.objects.get_or_create(username='testbot')
if created:
    user.set_password('testpass')
    user.save()

client = Client()
client.force_login(user)

# set total via start
client.post('/timetable/start/', {'total_teachers': 7})

# Build POST data for 7 teachers
post = {}
post['teachers-TOTAL_FORMS'] = '7'
post['teachers-INITIAL_FORMS'] = '0'
post['teachers-MIN_NUM_FORMS'] = '0'
post['teachers-MAX_NUM_FORMS'] = '1000'

for i in range(7):
    prefix = f'teachers-{i}-'
    post[prefix + 'teacher_name'] = f'Teacher {i+1}'
    # Each will handle year 1
    post[prefix + 'years_handling'] = '1'
    post[prefix + 'subject_y1'] = f'Sub{ i+1 }-Y1'
    post[prefix + 'hours_y1'] = '2'

resp = client.post('/timetable/teachers/', data=post)
print('POST status:', resp.status_code)
if resp.status_code == 200:
    print('Rendered length:', len(resp.content))
    print(resp.content[:1200].decode('utf-8'))
else:
    print('Redirected to:', resp['Location'] if 'Location' in resp else 'n/a')
