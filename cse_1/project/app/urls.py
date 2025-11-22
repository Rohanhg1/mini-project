# app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("choice/", views.choice_page, name="choice"),

    # Seating
    path("seating/", views.seating_arrangement, name="seating"),
    path("seating/download/", views.download_seating_pdf, name="download_seating_pdf"),

    # Timetable flow
    path("timetable/start/", views.start_timetable_input, name="timetable_start"),
    path("timetable/teachers/", views.timetable_teachers, name="timetable_teachers"),
    path("timetable/teacher/<str:teacher_name>/", views.teacher_timetable, name="teacher_timetable"),
    path("timetable/teacher/<str:teacher_name>/download/", views.download_teacher_timetable_pdf, name="download_teacher_timetable_pdf"),
    path("timetable/download/", views.download_timetable_pdf, name="download_timetable_pdf"),
]
