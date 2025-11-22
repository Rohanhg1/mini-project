import os
import django
import re

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

def check_total(total):
    # POST the total to start page then GET teachers page
    start_resp = client.post('/timetable/start/', {'total_teachers': total})
    teach_resp = client.get('/timetable/teachers/')
    content = teach_resp.content.decode('utf-8')
    # Count forms by searching for teacher_name fields per form
    matches = re.findall(r'teachers-\d+-teacher_name', content)
    # also verify management forms
    total_forms = re.search(r'teachers-TOTAL_FORMS" value="(\d+)"', content)
    total_forms_val = total_forms.group(1) if total_forms else 'MISSING'
    print(f"Total requested: {total} -> teacher_name fields found: {len(matches)}, TOTAL_FORMS={total_forms_val}, status={teach_resp.status_code}")
    # print short excerpt of first two forms
    idx = content.find('id="id_teachers-0-teacher_name"')
    if idx != -1:
        excerpt = content[idx:idx+800]
        print('--- excerpt (first form) ---')
        print(excerpt)
    else:
        print('No first form id found in HTML')

if __name__ == '__main__':
    for t in [4, 5, 6, 7]:
        check_total(t)
