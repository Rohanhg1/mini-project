import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import Client

c = Client()
logged = c.login(username='test', password='testpass')
if not logged:
    print('login failed')
else:
    s = c.session
    s['total_teachers'] = 7
    s.save()
    r = c.get('/timetable/teachers/')
    html = r.content.decode('utf-8')
    print('status', r.status_code)
    has = 'teacher-grid' in html
    print('has teacher-grid', has)
    idx = html.find('teacher-grid')
    if idx != -1:
        start = max(0, idx - 120)
        print(html[start:idx + 300])
    else:
        print(html[:800])
