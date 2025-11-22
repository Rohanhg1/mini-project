# app/forms.py
from django import forms

class SeatingForm(forms.Form):
    num_classes = forms.IntegerField(label='Number of Classes per Semester', min_value=1)
    benches_per_class = forms.IntegerField(label='Benches per Class', min_value=1)
    students_per_bench = forms.IntegerField(label='Students per Bench', min_value=1)


class TotalTeachersForm(forms.Form):
    total_teachers = forms.IntegerField(min_value=1, label="Total number of teachers")
    semester_type = forms.ChoiceField(
        choices=[('odd', 'Odd Semester (3, 5, 7)'), ('even', 'Even Semester (4, 6, 8)')],
        label="Semester Type",
        required=True
    )


class TeacherForm(forms.Form):
    def __init__(self, *args, **kwargs):
        semester_type = kwargs.pop('semester_type', 'odd')
        super().__init__(*args, **kwargs)
        self.fields['years_handling'].choices = self.get_years_choices(semester_type)

    teacher_name = forms.CharField()

    years_handling = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple
    )

    @staticmethod
    def get_years_choices(semester_type):
        if semester_type == 'odd':
            return [("1","3rd Semester"), ("2","5th Semester"), ("3","7th Semester")]
        elif semester_type == 'even':
            return [("1","4th Semester"), ("2","6th Semester"), ("3","8th Semester")]
        else:
            return [("1","1st year"), ("2","2nd year"), ("3","3rd year")]

    # Year 1
    subject_y1 = forms.CharField(required=False)
    hours_y1   = forms.IntegerField(required=False)
    integrated_y1 = forms.BooleanField(required=False)
    external_y1 = forms.BooleanField(required=False)

    # Year 2
    subject_y2 = forms.CharField(required=False)
    hours_y2   = forms.IntegerField(required=False)
    integrated_y2 = forms.BooleanField(required=False)
    external_y2 = forms.BooleanField(required=False)

    # Year 3
    subject_y3 = forms.CharField(required=False)
    hours_y3   = forms.IntegerField(required=False)
    integrated_y3 = forms.BooleanField(required=False)
    external_y3 = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        years = cleaned_data.get('years_handling', [])
        if '1' in years:
            if not cleaned_data.get('subject_y1'):
                self.add_error('subject_y1', 'This field is required when Year 1 is selected.')
        if '2' in years:
            if not cleaned_data.get('subject_y2'):
                self.add_error('subject_y2', 'This field is required when Year 2 is selected.')
        if '3' in years:
            if not cleaned_data.get('subject_y3'):
                self.add_error('subject_y3', 'This field is required when Year 3 is selected.')
        return cleaned_data

