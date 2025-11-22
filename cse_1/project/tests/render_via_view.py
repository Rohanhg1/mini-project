import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from app import views

# ensure test user exists
User.objects.create_user('test_view_user', password='testpass') if not User.objects.filter(username='test_view_user').exists() else None

rf = RequestFactory()
req = rf.get('/timetable/teachers/')
# attach a session and user to the request
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model

middleware = SessionMiddleware()
middleware.process_request(req)
req.session.save()
req.user = User.objects.get(username='test_view_user')

# set session total_teachers
req.session['total_teachers'] = 7
req.session.save()

resp = views.timetable_teachers(req)
# resp may be an HttpResponse; get content
try:
    content = resp.content.decode('utf-8')
except Exception:
    content = str(resp)

out = os.path.join(os.path.dirname(__file__), 'rendered_via_view.html')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write(content)
print('wrote', out)
