# views.py
# Python 3.10+ compatible
import random
import copy
import PyPDF2
import logging
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.http import HttpResponse
from deap import base, creator, tools, algorithms
import numpy as np

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.views.decorators.csrf import csrf_exempt

from .forms import SeatingForm, TotalTeachersForm, TeacherForm

# ----------------------
# Utility / Auth views
def user_login(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('choice')
        error = 'Invalid credentials'
    return render(request, 'app/login.html', {'error': error})


@login_required
def user_logout(request):
    auth_logout(request)
    return redirect('login')


@login_required
def choice_page(request):
    return render(request, 'app/choice.html')


# ----------------------
# Seating arrangement views
@login_required
def seating_arrangement(request):
    arrangement = []
    student_lists = []

    if request.method == 'POST':
        form = SeatingForm(request.POST, request.FILES)
        if form.is_valid():
            # Get number of semesters from POST data
            num_sems = int(request.POST.get('num_sems', 2))  # Default to 2 if not provided

            # Collect PDFs based on num_sems
            pdf_files = []
            for i in range(1, num_sems + 1):
                file_key = f'pdf_sem_{i}'
                if file_key in request.FILES:
                    pdf_files.append(request.FILES[file_key])

            total_rooms = form.cleaned_data.get('num_classes', 0)
            benches_per_room = form.cleaned_data.get('benches_per_class', 0)
            students_per_bench = form.cleaned_data.get('students_per_bench', 2)

            # Read PDFs and collect student lists
            student_lists = []
            for pdf_file in pdf_files:
                pdf = PyPDF2.PdfReader(pdf_file)
                text = ''.join(page.extract_text() for page in pdf.pages if page.extract_text())
                students = [line.strip() for line in text.split('\n') if line.strip()]
                # Filter out lines that are page numbers, serial numbers, or headers (case-insensitive)
                students = [
                    line for line in students
                    if not line.isdigit()
                    and not line.lower().startswith('page')
                    and not any(word in line.lower() for word in ['sl no', 'sl.no', 'serial', 'usn', 'name'])
                    and len(line) > 5
                    and any(c.isalpha() for c in line)
                ]
                student_lists.append(students)

            # Group students by section
            section_students = [[] for _ in range(num_sems)]
            for section_idx, students in enumerate(student_lists):
                for student in students:
                    section_students[section_idx].append(student)
            # Shuffle within sections
            for sec in section_students:
                random.shuffle(sec)

            # Assign students to benches using round-robin to ensure different sections per bench
            from collections import deque
            section_deques = [deque(sec) for sec in section_students]
            benches = []
            bench = []
            sec_cycle = 0
            while any(d for d in section_deques):
                if section_deques[sec_cycle]:
                    student = section_deques[sec_cycle].popleft()
                    bench.append(student)
                    if len(bench) == students_per_bench:
                        benches.append(bench)
                        bench = []
                sec_cycle = (sec_cycle + 1) % num_sems
            # Add remaining students to benches
            for sec_idx in range(num_sems):
                while section_deques[sec_idx]:
                    student = section_deques[sec_idx].popleft()
                    if not benches or len(benches[-1]) == students_per_bench:
                        benches.append([student])
                    else:
                        benches[-1].append(student)
            if bench:
                benches.append(bench)

            # Assign benches to rooms
            arrangement = []
            bench_idx = 0
            for room in range(1, max(1, total_rooms) + 1):
                room_benches = []
                for b in range(1, max(1, benches_per_room) + 1):
                    if bench_idx < len(benches):
                        # Pad bench to students_per_bench with None if necessary
                        bench_students = benches[bench_idx] + [None] * (students_per_bench - len(benches[bench_idx]))
                        room_benches.append((b, bench_students))
                        bench_idx += 1
                    else:
                        room_benches.append((b, [None] * students_per_bench))
                arrangement.append((room, room_benches))

            # Store arrangement and students_per_bench in session for download
            request.session["seating_arrangement"] = arrangement
            request.session["students_per_bench"] = students_per_bench

            # Redirect to result page with data
            return render(request, 'app/seating_result.html', {
                'arrangement': arrangement,
                'students_per_bench': students_per_bench
            })
    else:
        form = SeatingForm()

    return render(request, 'app/seating.html', {
        'form': form,
        'arrangement': arrangement,
        'student_lists': student_lists
    })


@login_required
def download_seating_pdf(request):
    arrangement = request.session.get("seating_arrangement")
    students_per_bench = request.session.get("students_per_bench", 2)
    if not arrangement:
        return redirect('seating')

    # Generate PDF for all rooms, each on a separate page, using full page
    buffer = BytesIO()
    # Set small margins to use complete page
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # Larger title style for better page utilization
    title_style = styles['Title']
    title_style.fontSize = 18
    title_style.alignment = 1  # Center

    for i, (room, benches) in enumerate(arrangement):
        elements.append(Paragraph(f"Seating Arrangement - Room {room}", title_style))
        elements.append(Spacer(1, 12))  # Spacer

        # Prepare table data
        headers = ['Bench'] + [f'Student {j+1}' for j in range(students_per_bench)]
        data = [headers]
        for bench, students in benches:
            row = [str(bench)]
            for s in students:
                if s:
                    parts = s.split(' ', 1)
                    usn = parts[0]
                    name = parts[1] if len(parts) > 1 else ''
                    cell_text = f"{usn}<br/>{name}" if name else usn
                    # Larger font for cells
                    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=10, leading=10)
                    row.append(Paragraph(cell_text, cell_style))
                else:
                    row.append('')
            data.append(row)

        # Calculate colWidths to fill the page width (A4 width ~595, minus margins 20+20=40, so ~555 available)
        page_width = 555  # Approximate usable width
        num_cols = 1 + students_per_bench
        bench_width = 60  # Fixed width for Bench column
        student_width = (page_width - bench_width) / students_per_bench
        colWidths = [bench_width] + [student_width] * students_per_bench

        # Create table with adjusted widths and larger fonts
        table = Table(data, colWidths=colWidths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table)

        # Add page break if not the last room
        if i < len(arrangement) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="seating_arrangement.pdf"'
    return response


# ----------------------
# Periods and indices:
PERIODS = [
    ("1st", "9:00-10:00"), ("2nd", "10:00-11:00"),
    ("Break", "11:00-11:15"),
    ("3rd", "11:15-12:15"), ("4th", "12:15-1:15"),
    ("Lunch", "1:15-2:30"),
    ("5th", "2:30-3:20"), ("6th", "3:20-4:15"), ("7th", "4:15-5:00")
]

# Days used in timetable generation
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# Schedulable period indices (exclude Break and Lunch)
SCHEDULABLE_PERIOD_INDICES = [0, 1, 3, 4, 6, 7, 8]

# Lab slot tuples and lengths
# Lab slots: prioritize morning (9:00-11:00), then mid (11:15-1:15), then afternoon (2:30-5:00)
LAB_SLOTS = [(0, 1), (3, 4), (6, 7, 8)]
LAB_SLOT_LENGTH = {(6, 7, 8): 3, (0, 1): 2, (3, 4): 2}

# Last 3 slots reserved for labs if teacher has unplaced lab hours
LAST_LAB_SLOTS = [6, 7, 8]


# ----------------------
# TIMETABLE FLOW
@login_required
def start_timetable_input(request):
    if request.method == "POST":
        form = TotalTeachersForm(request.POST)
        if form.is_valid():
            request.session["total_teachers"] = form.cleaned_data["total_teachers"]
            request.session["semester_type"] = form.cleaned_data["semester_type"]
            return redirect("timetable_teachers")
    else:
        form = TotalTeachersForm()
    return render(request, "app/timetable_start.html", {"form": form})


@login_required
@csrf_exempt
def timetable_teachers(request):
    total = request.session.get("total_teachers")
    semester_type = request.session.get("semester_type", "odd")
    if not total:
        return redirect("timetable_start")
    try:
        total = int(total)
    except Exception:
        total = 0
    if total <= 0:
        return redirect("timetable_start")
    # clamp to reasonable max
    total = min(total, 50)

    # Year labels based on semester type
    if semester_type == "odd":
        year_labels = {1: "3", 2: "5", 3: "7"}
    else:
        year_labels = {1: "4", 2: "6", 3: "8"}

    # Use a safe high max_num to avoid accidental truncation.
    TeacherFormSet = formset_factory(TeacherForm, extra=0, max_num=50)
    formset_prefix = 'teachers'

    # Handle regenerate request
    if request.method == "POST" and 'regenerate' in request.POST:
        entries = request.session.get("entries")
        if entries:
            timetables, unallocated = allocate_timetable_with_ga(entries)

            # Collect teachers and their subjects
            teacher_subjects = {}
            for entry in entries:
                teacher = entry['teacher']
                subject = entry['subject']
                if teacher not in teacher_subjects:
                    teacher_subjects[teacher] = []
                if subject not in teacher_subjects[teacher]:
                    teacher_subjects[teacher].append(subject)

            # Store in session for PDF download and individual teacher views
            request.session["timetables"] = timetables
            request.session["unallocated"] = unallocated
            request.session["teacher_subjects"] = teacher_subjects
            request.session["year_labels"] = year_labels
            request.session["semester_type"] = semester_type

            return render(request, "app/timetable_result.html", {
                "timetables": timetables,
                "periods": PERIODS,
                "days": DAYS,
                "unallocated": unallocated,
                "teacher_subjects": teacher_subjects,
                "year_labels": year_labels,
                "semester_type": semester_type
            })
        else:
            return redirect("timetable_start")

    if request.method == "POST":
        # bind posted data - ensure prefix is used so management_form matches
        formset = TeacherFormSet(request.POST, request.FILES, prefix=formset_prefix, form_kwargs={'semester_type': semester_type})
        # If management form is missing, formset.is_valid() will be False;
        # we surface a helpful debug message for dev use.
        if not formset.is_bound:
            return render(request, "app/timetable_teachers_raw.html", {
                "formset": formset, "total": total,
                "error": "Formset did not bind to POST. Ensure the template includes formset.management_form and uses the correct prefix ('teachers')."
            })
        if formset.is_valid():
            entries = []
            for f in formset:
                # Only attempt to read cleaned_data if the form had data.
                cd = getattr(f, "cleaned_data", None) or {}
                name = cd.get("teacher_name")
                years = cd.get("years_handling") or []
                if "1" in years:
                    subj = cd.get("subject_y1") or f"{name}-Y1"
                    hrs = cd.get("hours_y1") or 0
                    integrated = cd.get("integrated_y1") or False
                    ext = cd.get("external_y1") or False
                    # Allow lab-only subjects (hours may be zero) — set is_lab/is_external accordingly
                    if hrs > 0:
                        entries.append({"teacher": name, "year": 1, "subject": subj, "hours": hrs, "is_integrated": integrated, "is_lab": False, "is_external_lab": ext, "remaining": hrs})
                    else:
                        # if hours == 0 but lab checkbox checked, include entry so lab allocation can occur
                        if integrated or ext or cd.get("lab_y1") or cd.get("external_lab_y1"):
                            entries.append({"teacher": name, "year": 1, "subject": subj, "hours": 0, "is_integrated": integrated, "is_lab": True if cd.get("lab_y1") else False, "is_external_lab": ext, "remaining": 0})
                if "2" in years:
                    subj = cd.get("subject_y2") or f"{name}-Y2"
                    hrs = cd.get("hours_y2") or 0
                    integrated = cd.get("integrated_y2") or False
                    ext = cd.get("external_y2") or False
                    if hrs > 0:
                        entries.append({"teacher": name, "year": 2, "subject": subj, "hours": hrs, "is_integrated": integrated, "is_lab": False, "is_external_lab": ext, "remaining": hrs})
                    else:
                        if integrated or ext or cd.get("lab_y2") or cd.get("external_lab_y2"):
                            entries.append({"teacher": name, "year": 2, "subject": subj, "hours": 0, "is_integrated": integrated, "is_lab": True if cd.get("lab_y2") else False, "is_external_lab": ext, "remaining": 0})
                if "3" in years:
                    subj = cd.get("subject_y3") or f"{name}-Y3"
                    hrs = cd.get("hours_y3") or 0
                    integrated = cd.get("integrated_y3") or False
                    ext = cd.get("external_y3") or False
                    if hrs > 0:
                        entries.append({"teacher": name, "year": 3, "subject": subj, "hours": hrs, "is_integrated": integrated, "is_lab": False, "is_external_lab": ext, "remaining": hrs})
                    else:
                        if integrated or ext or cd.get("lab_y3") or cd.get("external_lab_y3"):
                            entries.append({"teacher": name, "year": 3, "subject": subj, "hours": 0, "is_integrated": integrated, "is_lab": True if cd.get("lab_y3") else False, "is_external_lab": ext, "remaining": 0})

            # call allocation (defined in later parts)
            timetables, unallocated = allocate_timetable_with_ga(entries)

            # Collect teachers and their subjects
            teacher_subjects = {}
            for entry in entries:
                teacher = entry['teacher']
                subject = entry['subject']
                if teacher not in teacher_subjects:
                    teacher_subjects[teacher] = []
                if subject not in teacher_subjects[teacher]:
                    teacher_subjects[teacher].append(subject)

            # Store in session for PDF download and individual teacher views
            request.session["timetables"] = timetables
            request.session["unallocated"] = unallocated
            request.session["teacher_subjects"] = teacher_subjects
            request.session["year_labels"] = year_labels
            request.session["semester_type"] = semester_type

            return render(request, "app/timetable_result.html", {
                "timetables": timetables,
                "periods": PERIODS,
                "days": DAYS,
                "unallocated": unallocated,
                "teacher_subjects": teacher_subjects,
                "year_labels": year_labels,
                "semester_type": semester_type
            })
        else:
            # show form errors to user for easier debugging (no debug prints)
            error_list = []
            for form_errors in formset.errors:
                for field, errors in form_errors.items():
                    for error in errors:
                        error_list.append(f"{field}: {error}")
            for error in formset.non_form_errors():
                error_list.append(str(error))
            return render(request, "app/timetable_teachers_raw.html", {"formset": formset, "total": total, "errors": error_list, "year_labels": year_labels, "semester_type": semester_type})
    else:
        # create an unbound formset with exactly `total` empty forms
        formset = TeacherFormSet(prefix=formset_prefix, initial=[{} for _ in range(total)], form_kwargs={'semester_type': semester_type})

    return render(request, "app/timetable_teachers_raw.html", {"formset": formset, "total": total, "year_labels": year_labels, "semester_type": semester_type})

@login_required
def teacher_timetable(request, teacher_name):
    timetables = request.session.get("timetables")
    teacher_subjects = request.session.get("teacher_subjects", {})
    year_labels = request.session.get("year_labels", {})
    if not timetables or teacher_name not in teacher_subjects:
        return redirect("timetable_teachers")

    # Filter timetables to show only this teacher's assignments
    teacher_timetables = {}
    for year, days_dict in timetables.items():
        teacher_timetables[year] = {}
        for day, slots in days_dict.items():
            teacher_slots = []
            for slot in slots:
                if slot and any(subject in slot for subject in teacher_subjects[teacher_name]):
                    teacher_slots.append(slot)
                else:
                    teacher_slots.append(None)
            teacher_timetables[year][day] = teacher_slots

    return render(request, "app/teacher_timetable.html", {
        "teacher_name": teacher_name,
        "timetables": teacher_timetables,
        "periods": PERIODS,
        "days": DAYS,
        "subjects": teacher_subjects[teacher_name],
        "year_labels": year_labels
    })


@login_required
def download_timetable_pdf(request):
    timetables = request.session.get("timetables")
    unallocated = request.session.get("unallocated")
    year_labels = request.session.get("year_labels", {})
    teacher_subjects = request.session.get("teacher_subjects", {})
    if not timetables:
        return redirect("timetable_start")

    # Generate PDF matching HTML layout exactly
    buffer = BytesIO()
    # Use minimal margins to maximize space
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=10, rightMargin=10, topMargin=10, bottomMargin=10)
    elements = []
    styles = getSampleStyleSheet()

    # Centered title, smaller
    title_style = styles['Title']
    title_style.alignment = 1  # Center
    title_style.fontSize = 14
    elements.append(Paragraph("Generated Timetables", title_style))
    elements.append(Spacer(1, 6))  # Smaller spacer

    # Warning box if unallocated, smaller
    if unallocated:
        warning_text = "<strong>Warning — some hours couldn't be scheduled:</strong><br/>"
        for u in unallocated:
            theory_rem = u.get('theory_remaining', 0)
            lab_rem = u.get('lab_remaining', 0)
            warning_text += f"• {u['teacher']} (Year {u['year']}) — {u['subject']} — theory: {theory_rem}, lab: {lab_rem} — int: {'Y' if u['is_integrated'] else 'N'} — ext: {'Y' if u['is_external_lab'] else 'N'}<br/>"
        warning_style = ParagraphStyle('Warning', parent=styles['Normal'], backColor=colors.HexColor('#ffe6e6'), borderColor=colors.HexColor('#ff9999'), borderWidth=1, borderPadding=5, spaceAfter=10, fontSize=8)
        elements.append(Paragraph(warning_text, warning_style))
        elements.append(Spacer(1, 6))

    # Teacher boxes: smaller
    if teacher_subjects:
        teacher_data = []
        row = []
        for teacher, subjects in teacher_subjects.items():
            box_text = f"<strong>{teacher}</strong><br/>{', '.join(subjects)}"
            box_style = ParagraphStyle('TeacherBox', parent=styles['Normal'], backColor=colors.HexColor('#e9f7ef'), borderColor=colors.HexColor('#27ae60'), borderWidth=1, borderPadding=5, alignment=1, fontSize=8)
            row.append(Paragraph(box_text, box_style))
            if len(row) == 3:  # 3 boxes per row
                teacher_data.append(row)
                row = []
        if row:
            while len(row) < 3:
                row.append('')  # Pad row
            teacher_data.append(row)
        teacher_table = Table(teacher_data, colWidths=[180]*3)
        teacher_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        elements.append(teacher_table)
        elements.append(Spacer(1, 10))

    # Timetables per semester
    for year, days_dict in timetables.items():
        sem_label = year_labels.get(year, f"Year {year}")
        # Semester heading, smaller
        heading_style = styles['Heading3']
        heading_style.borderWidth = 0
        heading_style.borderColor = colors.HexColor('#ddd')
        heading_style.borderPadding = 2
        heading_style.spaceAfter = 5
        heading_style.fontSize = 12
        elements.append(Paragraph(f"Semester {sem_label}", heading_style))

        # Table data
        data = []
        # Header row, smaller font
        header = ['Day']
        for period_name, time in PERIODS:
            header.append(f"{period_name} {time}")
        data.append(header)

        # Data rows
        for day in DAYS:
            row = [day]
            slots = days_dict.get(day, [None] * len(PERIODS))
            for slot in slots:
                cell_text = slot if slot else '-'
                row.append(cell_text)
            data.append(row)

        # Calculate column widths to fit the page (letter: 612 points, margins 10 each, usable ~592)
        page_width = 592
        num_cols = 10  # Day + 9 periods
        col_width = page_width / num_cols
        colWidths = [col_width] * num_cols

        # Create table with fixed widths
        table = Table(data, colWidths=colWidths)
        table_styles = [
            # Header: background #f2f2f2, bold, center, tiny font
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
            ('TOPPADDING', (0, 0), (-1, 0), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            # Body: tiny font
            ('FONTSIZE', (0, 1), (-1, -1), 4),
            # Grid: thin
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
        ]

        # Apply lab highlighting
        for row_idx in range(1, len(data)):  # Skip header
            for col_idx in range(1, len(data[row_idx])):  # Skip 'Day' column
                slot = data[row_idx][col_idx]
                if slot and ' - Lab' in slot:
                    table_styles.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.lightblue))

        table.setStyle(TableStyle(table_styles))
        elements.append(table)
        elements.append(Spacer(1, 10))  # Smaller spacer

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="timetable.pdf"'
    return response


@login_required
def download_teacher_timetable_pdf(request, teacher_name):
    timetables = request.session.get("timetables")
    teacher_subjects = request.session.get("teacher_subjects", {})
    year_labels = request.session.get("year_labels", {})
    if not timetables or teacher_name not in teacher_subjects:
        return redirect("timetable_teachers")

    # Filter timetables to show only this teacher's assignments
    teacher_timetables = {}
    for year, days_dict in timetables.items():
        teacher_timetables[year] = {}
        for day, slots in days_dict.items():
            teacher_slots = []
            for slot in slots:
                if slot and any(subject in slot for subject in teacher_subjects[teacher_name]):
                    teacher_slots.append(slot)
                else:
                    teacher_slots.append(None)
            teacher_timetables[year][day] = teacher_slots

    # Generate PDF matching the HTML layout and styles
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph(f"{teacher_name}'s Timetable", styles['Title']))

    # Subjects
    subjects_str = ", ".join(teacher_subjects[teacher_name])
    elements.append(Paragraph(f"Subjects: {subjects_str}", styles['Normal']))
    elements.append(Paragraph("", styles['Normal']))  # Spacer

    for year, days_dict in teacher_timetables.items():
        # Year heading
        sem_label = year_labels.get(year, f"Year {year}")
        elements.append(Paragraph(f"Semester {sem_label}", styles['Heading1']))

        # Build table data: rows for each day, columns for Day + periods
        data = []
        # Header row
        header = ['Day']
        for period_name, time in PERIODS:
            header.append(f"{period_name}\n{time}")
        data.append(header)

        # Data rows for each day
        for day in DAYS:
            row = [day]
            slots = days_dict.get(day, [None] * len(PERIODS))
            for slot in slots:
                row.append(slot if slot else '-')
            data.append(row)

        # Create table
        table = Table(data)

        # Define styles to match HTML CSS
        table_styles = [
            # Header row: background #f2f2f2, bold, center
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            # Grid: 1px solid #ddd
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd')),
        ]

        # Apply cell-specific styles for body rows
        for row_idx in range(1, len(data)):  # Skip header
            for col_idx in range(1, len(data[row_idx])):  # Skip 'Day' column
                slot = data[row_idx][col_idx]
                if slot and slot != '-' and any(subject in slot for subject in teacher_subjects[teacher_name]):
                    # Subject highlight: background #e9f7ef, bold
                    table_styles.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#e9f7ef')))
                    table_styles.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold'))
                elif not slot or slot == '-':
                    # Empty slot: background #f9f9f9, color #999
                    table_styles.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#f9f9f9')))
                    table_styles.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#999')))

        table.setStyle(TableStyle(table_styles))
        elements.append(table)
        elements.append(Paragraph("", styles['Normal']))  # Spacer

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{teacher_name}_timetable.pdf"'
    return response


# ----------------------
# TIMETABLE ALLOCATION WITH GENETIC ALGORITHM
# ----------------------
# TIMETABLE ALLOCATION WITH SMART GA/HEURISTICS (A2-Priority-3, Reinsert-YES)
def allocate_timetable_with_ga(entries_input):
    import copy
    entries = copy.deepcopy(entries_input)

    # Defensive defaults (use module-level ones if present)
    try:
        PERIODS
    except NameError:
        PERIODS = [f"P{i}" for i in range(9)]
    try:
        DAYS
    except NameError:
        DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    try:
        SCHEDULABLE_PERIOD_INDICES
    except NameError:
        SCHEDULABLE_PERIOD_INDICES = [0, 1, 3, 4, 6, 7, 8]

    LAB_SLOTS = [(0, 1), (3, 4), (6, 7, 8)]
    LAB_SLOT_LENGTH = {(0, 1): 2, (3, 4): 2, (6, 7, 8): 3}
    LAB_STARTS = [slot[0] for slot in LAB_SLOTS]

    # ---------------- NORMALIZE ENTRIES ----------------
    years_set = set()
    for i, e in enumerate(entries):
        try:
            y_int = int(e.get("year", 1))
        except Exception:
            y_int = 1
        e["year"] = y_int
        years_set.add(y_int)

        # flags
        e["is_integrated"] = bool(e.get("is_integrated")) or \
                             ("integrated" in (e.get("subject") or "").lower())
        e["is_lab"] = bool(e.get("is_lab", False))
        e["is_external_lab"] = bool(e.get("is_external_lab", False))

        base_hours = int(e.get("hours", 0) or 0)

        if e["is_integrated"]:
            # integrated: user gave theory hours; lab is extra and mandatory
            e["theory_remaining"] = base_hours
            e["lab_needed"] = True
            e["lab_length"] = 3 if e["is_external_lab"] else 2
            e["lab_remaining"] = e["lab_length"]
        else:
            # non-integrated
            if e.get("is_lab") or e.get("is_external_lab"):
                # lab checkbox means there is a lab even if hours == 0
                e["lab_needed"] = True
                e["lab_length"] = 3 if e.get("is_external_lab") else 2
                e["lab_remaining"] = e["lab_length"]
                # keep theory only if there are separate theory hours
                e["theory_remaining"] = base_hours if base_hours > 0 and not (
                    e.get("is_lab") or e.get("is_external_lab")
                ) else 0
            else:
                # pure theory subject
                e["lab_needed"] = False
                e["lab_length"] = 0
                e["lab_remaining"] = 0
                e["theory_remaining"] = base_hours

        e["id"] = i

    years = sorted(list(years_set)) if years_set else [1, 2, 3]

    timetables = {y: {d: [None] * len(PERIODS) for d in DAYS} for y in years}

    # trackers
    teacher_occupied = {}
    for e in entries:
        teacher_occupied.setdefault(e['teacher'], set())
    subject_scheduled_one_week = {y: set() for y in years}
    subject_day_assigned = {}
    teacher_first_period_last_day = {}
    subject_period_used = {y: {} for y in years}

    def teacher_free(teacher, day, p):
        return (day, p) not in teacher_occupied.get(teacher, set())

    def lab_exists_on_day(year, day):
        """Check if a lab is already placed for that year & day."""
        row = timetables[year][day]
        for cell in row:
            if cell is not None and isinstance(cell, str) and cell.endswith(" - Lab"):
                return True
        return False

    # global queue for overridden theory reinsertion
    removed_theory_queue = []

    # ---------------- LAB CANDIDATE (A2 PRIORITY-3) ----------------
    def find_lab_candidate(year, day_idx, day, start_p_idx):
        cand = []
        for e in entries:
            if e["year"] != year:
                continue
            if e.get("lab_needed", False) and int(e.get("lab_remaining", 0)) > 0:
                cand.append(e)

        # sort: integrated+external first, then by total remaining load
        cand.sort(
            key=lambda x: (
                1 if (x.get("is_integrated", False) and x.get("is_external_lab", False)) else 0,
                x.get("theory_remaining", 0) + x.get("lab_remaining", 0)
            ),
            reverse=True
        )

        for e in cand:
            subj = e.get("subject")
            teacher = e.get("teacher")
            lab_len = int(e.get("lab_length", 0))

            if subj in subject_scheduled_one_week[year]:
                continue
            if subj in subject_day_assigned.get((year, day), set()):
                continue
            used_periods = subject_period_used[year].get(subj, set())
            if lab_len not in (2, 3):
                continue

            # slot priority
            if e.get("is_integrated", False) and e.get("is_external_lab", False):
                slot_priority = [(6, 7, 8)]
            elif e.get("is_integrated", False):
                slot_priority = [(0, 1), (3, 4)]
            else:
                slot_priority = [(0, 1), (3, 4), (6, 7, 8)]

            for slot in slot_priority:
                if slot[0] != start_p_idx:
                    continue
                if len(slot) != lab_len:
                    continue

                # STEP 1: clean placement (no override)
                clean_ok = True
                for p in slot:
                    if p not in SCHEDULABLE_PERIOD_INDICES or p >= len(PERIODS):
                        clean_ok = False
                        break
                    if timetables[year][day][p] is not None:
                        clean_ok = False
                        break
                    if not teacher_free(teacher, day, p):
                        clean_ok = False
                        break
                    if p in used_periods:
                        clean_ok = False
                        break
                if clean_ok:
                    return e, slot

                # STEP 2: smart override only theory (Priority-3)
                override_possible = True
                theory_to_reinsert = []

                for p in slot:
                    cell = timetables[year][day][p]
                    if cell is None:
                        continue
                    if isinstance(cell, str) and cell.endswith(" - Lab"):
                        override_possible = False
                        break
                    theory_sub = cell
                    # only override if that theory appears elsewhere
                    if len(subject_period_used[year].get(theory_sub, set())) == 0:
                        override_possible = False
                        break
                    theory_to_reinsert.append((p, theory_sub))

                if override_possible:
                    for p, theory_sub in theory_to_reinsert:
                        timetables[year][day][p] = None
                        removed_theory_queue.append((year, theory_sub))
                    return e, slot

        return None, None

    # ---------------- THEORY CANDIDATE ----------------
    def find_normal_candidate(year, day_idx, day, p_idx):
        cand = []
        for e in entries:
            if e["year"] != year:
                continue
            avail = int(e.get("theory_remaining", 0))
            if avail <= 0:
                continue
            subj = e.get("subject")
            if subj in subject_day_assigned.get((year, day), set()):
                continue
            used_periods = subject_period_used[year].get(subj, set())
            if p_idx in used_periods:
                continue
            if not teacher_free(e["teacher"], day, p_idx):
                continue
            if p_idx == 0:
                last = teacher_first_period_last_day.get(e["teacher"])
                if last is not None and last == day_idx - 1:
                    continue
            cand.append(e)
        if not cand:
            return None
        cand.sort(
            key=lambda x: (x.get("theory_remaining", 0) + x.get("lab_remaining", 0)),
            reverse=True
        )
        return cand[0]

    # ---------------- MAIN PASS: LABS THEN THEORY ----------------
    for y in years:
        for day_idx, day in enumerate(DAYS):
            subject_day_assigned.setdefault((y, day), set())

            # lab starts
            for start_idx in LAB_STARTS:
                if start_idx not in SCHEDULABLE_PERIOD_INDICES:
                    continue
                if timetables[y][day][start_idx] is not None:
                    continue
                if lab_exists_on_day(y, day):
                    continue

                lab_e, lab_slot = find_lab_candidate(y, day_idx, day, start_idx)
                if lab_e and lab_slot:
                    label = f"{lab_e['subject']} - Lab"
                    for p in lab_slot:
                        timetables[y][day][p] = label
                    deduct = LAB_SLOT_LENGTH.get(tuple(lab_slot), len(lab_slot))
                    lab_e["lab_remaining"] = int(lab_e.get("lab_remaining", 0)) - deduct
                    if lab_e["lab_remaining"] <= 0:
                        lab_e["lab_needed"] = False
                    subject_scheduled_one_week[y].add(lab_e['subject'])
                    subject_day_assigned[(y, day)].add(lab_e['subject'])
                    subject_period_used[y].setdefault(lab_e['subject'], set()).update(lab_slot)
                    teacher_occupied.setdefault(lab_e['teacher'], set()).update(
                        [(day, p) for p in lab_slot]
                    )
                    if lab_slot[0] == 0:
                        teacher_first_period_last_day[lab_e['teacher']] = day_idx

            # single-hour theory
            for p_idx in SCHEDULABLE_PERIOD_INDICES:
                if timetables[y][day][p_idx] is not None:
                    continue
                normal = find_normal_candidate(y, day_idx, day, p_idx)
                if normal:
                    timetables[y][day][p_idx] = normal['subject']
                    normal["theory_remaining"] = int(normal.get("theory_remaining", 0)) - 1
                    teacher_occupied.setdefault(normal['teacher'], set()).add((day, p_idx))
                    subject_day_assigned[(y, day)].add(normal['subject'])
                    subject_period_used[y].setdefault(normal['subject'], set()).add(p_idx)
                    if p_idx == 0:
                        teacher_first_period_last_day[normal['teacher']] = day_idx

    # ---------------- SECOND PASS: REMAINING LABS ----------------
    for y in years:
        for day_idx, day in enumerate(DAYS):
            for slot_tuple in LAB_SLOTS:
                a = slot_tuple[0]
                if a not in SCHEDULABLE_PERIOD_INDICES:
                    continue
                if timetables[y][day][a] is not None:
                    continue
                if lab_exists_on_day(y, day):
                    continue

                lab_e, lab_slot = find_lab_candidate(y, day_idx, day, a)
                if lab_e and lab_slot:
                    label = f"{lab_e['subject']} - Lab"
                    for p in lab_slot:
                        timetables[y][day][p] = label
                    deduct = LAB_SLOT_LENGTH.get(tuple(lab_slot), len(lab_slot))
                    lab_e["lab_remaining"] = int(lab_e.get("lab_remaining", 0)) - deduct
                    if lab_e["lab_remaining"] <= 0:
                        lab_e["lab_needed"] = False
                    subject_scheduled_one_week[y].add(lab_e['subject'])
                    subject_day_assigned[(y, day)].add(lab_e['subject'])
                    subject_period_used[y].setdefault(lab_e['subject'], set()).update(lab_slot)
                    teacher_occupied.setdefault(lab_e['teacher'], set()).update(
                        [(day, p) for p in lab_slot]
                    )
                    if lab_slot[0] == 0:
                        teacher_first_period_last_day[lab_e['teacher']] = day_idx

    # ---------------- THIRD PASS: FILL THEORY, RESERVE LAST LAB SLOTS ----------------
    has_unplaced_labs = any(
        e.get("lab_needed", False) and int(e.get("lab_remaining", 0)) > 0
        for e in entries
    )

    try:
        LAST_LAB_SLOTS
    except NameError:
        LAST_LAB_SLOTS = [6, 7, 8]

    for y in years:
        for day_idx, day in enumerate(DAYS):
            for p in SCHEDULABLE_PERIOD_INDICES:
                if timetables[y][day][p] is not None:
                    continue
                if has_unplaced_labs and p in LAST_LAB_SLOTS:
                    continue
                cand = find_normal_candidate(y, day_idx, day, p)
                if cand:
                    timetables[y][day][p] = cand['subject']
                    cand["theory_remaining"] = int(cand.get("theory_remaining", 0)) - 1
                    teacher_occupied.setdefault(cand['teacher'], set()).add((day, p))
                    subject_day_assigned[(y, day)].add(cand['subject'])
                    if p == 0:
                        teacher_first_period_last_day[cand['teacher']] = day_idx

    # ---------------- FINAL PASS: FILL WITH TUTORIAL (EXCEPT RESERVED LAST LAB) ----------------
    for y in years:
        for d in DAYS:
            for p in SCHEDULABLE_PERIOD_INDICES:
                if timetables[y][d][p] is None:
                    if not (has_unplaced_labs and p in LAST_LAB_SLOTS):
                        timetables[y][d][p] = "Tutorial"

    # ---------------- LAST-CHANCE LABS INTO TUTORIAL SLOTS ----------------
    for y in years:
        for e in entries:
            if e.get("year") != y:
                continue
            if not e.get("lab_needed", False) or int(e.get("lab_remaining", 0)) <= 0:
                continue
            lab_len = int(e.get("lab_length", 0))
            if lab_len not in (2, 3):
                continue
            subj = e['subject']
            teacher = e['teacher']

            possible_slots = [(6, 7, 8)] if lab_len == 3 else [(0, 1), (3, 4)]
            placed = False
            for day_idx, day in enumerate(DAYS):
                if lab_exists_on_day(y, day):
                    continue
                for slot in possible_slots:
                    if any(p >= len(PERIODS) for p in slot):
                        continue
                    conflict = False
                    used_periods = subject_period_used.get(y, {}).get(subj, set())
                    for p in slot:
                        if p not in SCHEDULABLE_PERIOD_INDICES:
                            conflict = True; break
                        cell = timetables[y][day][p]
                        if cell is not None and cell != "Tutorial":
                            conflict = True; break
                        if (day, p) in teacher_occupied.get(teacher, set()):
                            conflict = True; break
                        if p == 0:
                            last = teacher_first_period_last_day.get(teacher)
                            if last is not None and last == day_idx - 1:
                                conflict = True; break
                        if p in used_periods:
                            conflict = True; break
                    if conflict:
                        continue
                    label = f"{subj} - Lab"
                    for p in slot:
                        timetables[y][day][p] = label
                    teacher_occupied.setdefault(teacher, set()).update(
                        [(day, p) for p in slot]
                    )
                    if slot[0] == 0:
                        teacher_first_period_last_day[teacher] = day_idx
                    subject_scheduled_one_week[y].add(subj)
                    subject_day_assigned.setdefault((y, day), set()).add(subj)
                    subject_period_used[y].setdefault(subj, set()).update(slot)
                    deduct = LAB_SLOT_LENGTH.get(tuple(slot), len(slot))
                    e["lab_remaining"] = int(e.get("lab_remaining", 0)) - deduct
                    if e["lab_remaining"] <= 0:
                        e["lab_needed"] = False
                    placed = True
                    break
                if placed:
                    break

    # ---------------- REINSERT OVERRIDDEN THEORY ----------------
    for year, subj in removed_theory_queue:
        placed = False
        for day_idx, day in enumerate(DAYS):
            if placed:
                break
            for p in SCHEDULABLE_PERIOD_INDICES:
                if timetables[year][day][p] is None:
                    timetables[year][day][p] = subj
                    subject_period_used[year].setdefault(subj, set()).add(p)
                    subject_day_assigned.setdefault((year, day), set()).add(subj)
                    placed = True
                    break

    # ---------------- MAKE FIRST 3 PERIODS CONTINUOUS (WITHIN DAY) ----------------
    # First 3 teaching periods: indices 0, 1, 3
    for y in years:
        for day in DAYS:
            row = timetables[y][day]
            if not row:
                continue

            first_slots = [idx for idx in [0, 1, 3] if idx < len(row)]
            later_slots = [idx for idx in SCHEDULABLE_PERIOD_INDICES
                           if idx not in first_slots and idx < len(row)]

            for p in first_slots:
                # already a real class OR lab -> don't touch
                if row[p] is not None and row[p] != "Tutorial":
                    continue

                # pull a REAL *non-lab* class from later slots of same day
                for q in later_slots:
                    cell = row[q]
                    if cell is None or cell == "Tutorial":
                        continue
                    # don't break lab blocks – skip lab cells
                    if isinstance(cell, str) and cell.endswith(" - Lab"):
                        continue
                    # swap theory/normal subject into early period
                    row[p], row[q] = row[q], row[p]
                    break

    # ---------------- BALANCE ACROSS WEEK: FILL WEAK DAYS (LIKE FRIDAY) ----------------
    for y in years:
        # compute counts in first 3 for each day
        def day_count(day_name):
            r = timetables[y][day_name]
            fslots = [idx for idx in [0, 1, 3] if idx < len(r)]
            return sum(1 for p in fslots if r[p] is not None and r[p] != "Tutorial")

        # try to move single periods from heavy days to light days
        changed = True
        while changed:
            changed = False
            # days sorted by first-3 load
            days_sorted = sorted(DAYS, key=day_count)
            low = days_sorted[0]
            high = days_sorted[-1]
            low_cnt = day_count(low)
            high_cnt = day_count(high)

            # stop if fairly balanced or no difference
            if high_cnt <= low_cnt or low_cnt >= 3:
                break

            row_low = timetables[y][low]
            row_high = timetables[y][high]
            first_low = [idx for idx in [0, 1, 3] if idx < len(row_low)]
            first_high = [idx for idx in [0, 1, 3] if idx < len(row_high)]

            # find an empty/Tutorial slot in low day's first 3
            target_p = None
            for p in first_low:
                if row_low[p] is None or row_low[p] == "Tutorial":
                    target_p = p
                    break
            if target_p is None:
                break

            # choose a donor slot from high day:
            donor_p = None
            for p in [idx for idx in SCHEDULABLE_PERIOD_INDICES if idx < len(row_high)]:
                if p in first_high:
                    continue  # don't break continuity there
                cell = row_high[p]
                if cell is None or cell == "Tutorial":
                    continue
                if isinstance(cell, str) and cell.endswith(" - Lab"):
                    continue  # don't move labs across days
                donor_p = p
                break

            if donor_p is None:
                break

            # move subject: high -> low
            row_low[target_p] = row_high[donor_p]
            row_high[donor_p] = "Tutorial"
            changed = True

    # ---------------- MAKE AFTERNOON PERIODS CONTINUOUS (WITHIN DAY) ----------------
    # Afternoon teaching periods: 5th, 6th, 7th -> indices 6, 7, 8
    for y in years:
        for day in DAYS:
            row = timetables[y][day]
            if not row:
                continue

            aft_slots = [idx for idx in [6, 7, 8] if idx < len(row)]

            for p in aft_slots:
                cell = row[p]
                # already a real class OR lab -> don't touch
                if cell is not None and cell != "Tutorial":
                    continue

                # pull a REAL *non-lab* class from later afternoon slots of same day
                for q in aft_slots:
                    if q <= p:
                        continue
                    c2 = row[q]
                    if c2 is None or c2 == "Tutorial":
                        continue
                    # do not move lab cells, to keep labs continuous
                    if isinstance(c2, str) and c2.endswith(" - Lab"):
                        continue
                    # swap theory/normal subject into earlier afternoon period
                    row[p], row[q] = row[q], row[p]
                    break

    # ---------------- UNALLOCATED SUMMARY ----------------
    unallocated = []
    for e in entries:
        theory_left = int(e.get("theory_remaining", 0))
        lab_left = int(e.get("lab_remaining", 0))
        if theory_left > 0 or lab_left > 0 or e.get("lab_needed", False):
            unallocated.append({
                "id": e["id"],
                "subject": e.get("subject"),
                "teacher": e.get("teacher"),
                "year": e.get("year"),
                "theory_remaining": theory_left,
                "lab_remaining": lab_left,
                "lab_needed": bool(e.get("lab_needed", False)),
                "is_integrated": bool(e.get("is_integrated", False)),
                "is_external_lab": bool(e.get("is_external_lab", False)),
                "lab_length": int(e.get("lab_length", 0)),
            })

    return timetables, unallocated
