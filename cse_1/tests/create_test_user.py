import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

django.setup()
from django.contrib.auth.models import User

username = 'test'
password = 'testpass'
email = 'test@example.com'
if not User.objects.filter(username=username).exists():
    User.objects.create_user(username, email, password)
    print('Created user', username)
else:
    print('User already exists')
