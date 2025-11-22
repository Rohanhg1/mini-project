import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.forms import TeacherForm

def test_validation():
    # Test valid data
    valid_data = {
        'teacher_name': 'Test Teacher',
        'years_handling': ['1'],
        'subject_y1': 'Math',
        'hours_y1': 2,
        'lab_y1': False,
        'external_y1': False,
    }
    form = TeacherForm(data=valid_data)
    print("Valid form is_valid:", form.is_valid())
    if not form.is_valid():
        print("Errors:", form.errors)

    # Test invalid: missing subject for selected year
    invalid_data1 = {
        'teacher_name': 'Test Teacher',
        'years_handling': ['1'],
        'subject_y1': '',  # missing
        'hours_y1': 2,
        'lab_y1': False,
        'external_y1': False,
    }
    form1 = TeacherForm(data=invalid_data1)
    print("Invalid form (missing subject) is_valid:", form1.is_valid())
    if not form1.is_valid():
        print("Errors:", form1.errors)

    # Test invalid: negative hours
    invalid_data2 = {
        'teacher_name': 'Test Teacher',
        'years_handling': ['1'],
        'subject_y1': 'Math',
        'hours_y1': -1,  # invalid
        'lab_y1': False,
        'external_y1': False,
    }
    form2 = TeacherForm(data=invalid_data2)
    print("Invalid form (negative hours) is_valid:", form2.is_valid())
    if not form2.is_valid():
        print("Errors:", form2.errors)

    # Test invalid: zero hours
    invalid_data3 = {
        'teacher_name': 'Test Teacher',
        'years_handling': ['1'],
        'subject_y1': 'Math',
        'hours_y1': 0,  # invalid
        'lab_y1': False,
        'external_y1': False,
    }
    form3 = TeacherForm(data=invalid_data3)
    print("Invalid form (zero hours) is_valid:", form3.is_valid())
    if not form3.is_valid():
        print("Errors:", form3.errors)

if __name__ == '__main__':
    test_validation()
