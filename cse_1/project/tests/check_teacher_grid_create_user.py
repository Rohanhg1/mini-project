import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

username = 'test'
password = 'testpass'

if not User.objects.filter(username=username).exists():
    print('creating test user')
    User.objects.create_user(username=username, password=password)
else:
    print('test user already exists')

c = Client()
logged = c.login(username=username, password=password)
print('login success:', logged)
if not logged:
    print('login failed; aborting')
else:
    s = c.session
    s['total_teachers'] = 7
    s.save()
    r = c.get('/timetable/teachers/')
    print('response status code:', r.status_code)
    try:
        html = r.content.decode('utf-8')
    except Exception as ex:
        print('could not decode HTML:', ex)
        html = ''
    print('html length:', len(html))
    if html:
        has = 'teacher-grid' in html
        print('has teacher-grid', has)
        # count teacher headings
        count = html.count('<h4>Teacher')
        print('teacher h4 count:', count)
        # write full HTML to a file inside the workspace for inspection
        out = os.path.join(os.path.dirname(__file__), 'timetable_teachers_output.html')
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(html)
        print('wrote HTML to', out)
    else:
        print('empty HTML; check view permissions or login')
