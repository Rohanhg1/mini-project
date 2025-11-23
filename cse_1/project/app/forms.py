# forms.py - Simplified approach using JSON field for day-time preferences
from django import forms

class TotalTeachersForm(forms.Form):
    total_teachers = forms.IntegerField(
        label="Total Number of Teachers",
        min_value=1
    )
    semester_type = forms.ChoiceField(
        label="Semester Type",
        choices=[
            ('odd', 'Odd Semester (3, 5, 7)'),
            ('even', 'Even Semester (4, 6, 8)')
        ]
    )

class TeacherForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # Accept semester_type but we don't use it in this simplified form
        self.semester_type = kwargs.pop('semester_type', 'odd')
        super().__init__(*args, **kwargs)
    
    teacher_name = forms.CharField(max_length=100, required=False)
    years_handling = forms.MultipleChoiceField(
        choices=[('1', '3rd Sem'), ('2', '5th/7th Sem'), ('3', '7th/8th Sem')],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    # Semester 1 (3rd)
    subject_y1 = forms.CharField(required=False)
    hours_y1   = forms.IntegerField(required=False)
    integrated_y1 = forms.BooleanField(required=False)
    external_y1 = forms.BooleanField(required=False)
    has_preference_y1 = forms.BooleanField(required=False, label="Set day & time preference")
    # Store as JSON: {"Mon": "0", "Wed": "3", ...}
    day_time_prefs_y1 = forms.CharField(required=False, widget=forms.HiddenInput())

    # Semester 2 (5th)
    subject_y2 = forms.CharField(required=False)
    hours_y2   = forms.IntegerField(required=False)
    integrated_y2 = forms.BooleanField(required=False)
    external_y2 = forms.BooleanField(required=False)
    has_preference_y2 = forms.BooleanField(required=False, label="Set day & time preference")
    day_time_prefs_y2 = forms.CharField(required=False, widget=forms.HiddenInput())

    # Semester 3 (7th)
    subject_y3 = forms.CharField(required=False)
    hours_y3   = forms.IntegerField(required=False)
    integrated_y3 = forms.BooleanField(required=False)
    external_y3 = forms.BooleanField(required=False)
    has_preference_y3 = forms.BooleanField(required=False, label="Set day & time preference")
    day_time_prefs_y3 = forms.CharField(required=False, widget=forms.HiddenInput())

class SeatingForm(forms.Form):
    pdf_file = forms.FileField()
