# views.py
# Python 3.10+ compatible
import random
import copy
import PyPDF2
import logging
from io import BytesIO

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.forms import formset_factory

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .forms import TeacherForm, TotalTeachersForm, SeatingForm

TeacherFormSet = formset_factory(TeacherForm, extra=0)
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
@login_required
def download_seating_pdf(request):
    arrangement = request.session.get("seating_arrangement")
    students_per_bench = request.session.get("students_per_bench", 2)
    if not arrangement:
        return redirect('seating')

    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    elements = []
    styles = getSampleStyleSheet()

    # Title style
    title_style = styles['Title']
    title_style.fontSize = 18
    title_style.alignment = 1  # center

    # Decide column headers based on students_per_bench
    if students_per_bench == 3:
        col_headers = ["column 1 (left)", "column 2 (middle)", "column 3 (right)"]
    elif students_per_bench == 2:
        col_headers = ["column 1 (left)", "column 2 (right)"]
    else:
        col_headers = [f"Student {j+1}" for j in range(students_per_bench)]

    headers = ['Bench'] + col_headers

    # Page width for colWidths
    page_width = 555  # approx usable width (A4 - margins)
    bench_width = 60
    student_width = (page_width - bench_width) / students_per_bench
    colWidths = [bench_width] + [student_width] * students_per_bench

    # Cell style for student cells
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontSize=10,
        leading=10
    )

    for room_index, (room, benches) in enumerate(arrangement):
        # Room title
        elements.append(Paragraph(f"Seating Arrangement - Room {room}", title_style))
        elements.append(Spacer(1, 12))

        # ✅ make sure bench numbers are in order
        benches_sorted = sorted(benches, key=lambda x: x[0])

        # ✅ create a SEPARATE TABLE for every 5 benches
        for start in range(0, len(benches_sorted), 5):
            chunk = benches_sorted[start:start + 5]

            data = [headers]

            for bench_num, students in chunk:
                row = [str(bench_num)]
                for s in students:
                    if s:
                        parts = s.split(' ', 1)
                        usn = parts[0]
                        name = parts[1] if len(parts) > 1 else ''
                        cell_text = f"{usn}<br/>{name}" if name else usn
                        row.append(Paragraph(cell_text, cell_style))
                    else:
                        row.append('')
                data.append(row)

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
            elements.append(Spacer(1, 16))  # space between groups of 5 benches

        # Page break between rooms
        if room_index < len(arrangement) - 1:
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
                    # Get preference data (JSON format: {"Mon": "0", "Wed": "3", ...})
                    has_pref = cd.get("has_preference_y1") or False
                    day_time_json = cd.get("day_time_prefs_y1") or "{}"
                    import json
                    try:
                        day_time_prefs = json.loads(day_time_json) if day_time_json else {}
                    except:
                        day_time_prefs = {}
                    
                    # DEBUG: Print what we received
                    if has_pref or day_time_prefs:
                        print(f"\n🔍 DEBUG: Preference data for {name} - Year 1:")
                        print(f"   has_preference_y1: {has_pref}")
                        print(f"   day_time_prefs_y1 JSON: {day_time_json}")
                        print(f"   Parsed preferences: {day_time_prefs}")
                    
                    # Allow lab-only subjects (hours may be zero) — set is_lab/is_external accordingly
                    if hrs > 0:
                        entries.append({"teacher": name, "year": 1, "subject": subj, "hours": hrs, "is_integrated": integrated, "is_lab": False, "is_external_lab": ext, "remaining": hrs, "day_time_prefs": day_time_prefs if has_pref else {}})
                    else:
                        # if hours == 0 but lab checkbox checked, include entry so lab allocation can occur
                        if integrated or ext or cd.get("lab_y1") or cd.get("external_lab_y1"):
                            entries.append({"teacher": name, "year": 1, "subject": subj, "hours": 0, "is_integrated": integrated, "is_lab": True if cd.get("lab_y1") else False, "is_external_lab": ext, "remaining": 0, "day_time_prefs": day_time_prefs if has_pref else {}})
                if "2" in years:
                    subj = cd.get("subject_y2") or f"{name}-Y2"
                    hrs = cd.get("hours_y2") or 0
                    integrated = cd.get("integrated_y2") or False
                    ext = cd.get("external_y2") or False
                    # Get preference data (JSON format)
                    has_pref = cd.get("has_preference_y2") or False
                    day_time_json = cd.get("day_time_prefs_y2") or "{}"
                    try:
                        day_time_prefs = json.loads(day_time_json) if day_time_json else {}
                    except:
                        day_time_prefs = {}
                    if hrs > 0:
                        entries.append({"teacher": name, "year": 2, "subject": subj, "hours": hrs, "is_integrated": integrated, "is_lab": False, "is_external_lab": ext, "remaining": hrs, "day_time_prefs": day_time_prefs if has_pref else {}})
                    else:
                        if integrated or ext or cd.get("lab_y2") or cd.get("external_lab_y2"):
                            entries.append({"teacher": name, "year": 2, "subject": subj, "hours": 0, "is_integrated": integrated, "is_lab": True if cd.get("lab_y2") else False, "is_external_lab": ext, "remaining": 0, "day_time_prefs": day_time_prefs if has_pref else {}})
                if "3" in years:
                    subj = cd.get("subject_y3") or f"{name}-Y3"
                    hrs = cd.get("hours_y3") or 0
                    integrated = cd.get("integrated_y3") or False
                    ext = cd.get("external_y3") or False
                    # Get preference data (JSON format)
                    has_pref = cd.get("has_preference_y3") or False
                    day_time_json = cd.get("day_time_prefs_y3") or "{}"
                    try:
                        day_time_prefs = json.loads(day_time_json) if day_time_json else {}
                    except:
                        day_time_prefs = {}
                    if hrs > 0:
                        entries.append({"teacher": name, "year": 3, "subject": subj, "hours": hrs, "is_integrated": integrated, "is_lab": False, "is_external_lab": ext, "remaining": hrs, "day_time_prefs": day_time_prefs if has_pref else {}})
                    else:
                        if integrated or ext or cd.get("lab_y3") or cd.get("external_lab_y3"):
                            entries.append({"teacher": name, "year": 3, "subject": subj, "hours": 0, "is_integrated": integrated, "is_lab": True if cd.get("lab_y3") else False, "is_external_lab": ext, "remaining": 0, "day_time_prefs": day_time_prefs if has_pref else {}})

            # Store entries in session for regeneration
            request.session["entries"] = entries
            
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
# TIMETABLE ALLOCATION WITH GOOGLE OR-TOOLS (CP-SAT)
# ----------------------
def allocate_timetable_with_ga(entries_input):
    """
    Allocates timetable using Constraint Programming (Google OR-Tools).
    Guarantees strict adherence to:
    1. Teacher availability (no double booking)
    2. Rest periods (no consecutive classes)
    3. Lab block validity
    4. Single class per slot per year
    """
    import copy
    from ortools.sat.python import cp_model
    
    entries = copy.deepcopy(entries_input)
    model = cp_model.CpModel()

    # --- Constants & Data Prep ---
    PERIODS = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # Internal indices
    TEACHING_PERIODS = [0, 1, 3, 4, 6, 7, 8] # Periods where classes can happen
    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    
    # Map periods to next rest period
    # 0->1, 1->3, 3->4, 4->6, 6->7, 7->8, 8->None
    NEXT_REST_MAP = {0: 1, 1: 3, 3: 4, 4: 6, 6: 7, 7: 8, 8: None}

    # Extract Years and Teachers
    years = sorted(list(set(int(e.get("year", 1)) for e in entries)))
    teachers = sorted(list(set(e['teacher'] for e in entries)))
    
    # Organize entries by ID for easy access
    # Split entries into Theory and Lab components
    theory_reqs = [] # (entry_idx, year, teacher, subject, hours, prefs)
    lab_reqs = []    # (entry_idx, year, teacher, subject, duration, prefs)
    
    for i, e in enumerate(entries):
        y = int(e.get("year", 1))
        t = e['teacher']
        s = e['subject']
        prefs = e.get('day_time_prefs', {})
        
        # Theory Component
        # IMPORTANT: For integrated subjects (with or without external), 
        # the 'hours' field represents ONLY theory hours.
        # Labs are allocated separately and do NOT consume theory hours.
        th_hours = 0
        if e.get("is_integrated") or e.get("is_integrated") and e.get("is_external_lab"):
            # Integrated subjects: 'hours' = theory hours only
            th_hours = int(e.get("hours", 0))
        elif not (e.get("is_lab") or e.get("is_external_lab")):
            # Pure theory subjects (no lab component)
            th_hours = int(e.get("hours", 0))
        # Note: For pure lab subjects (is_lab=True but not integrated), 
        # th_hours stays 0 as all time is in lab
        
        if th_hours > 0:
            theory_reqs.append({
                'id': i, 'year': y, 'teacher': t, 'subject': s, 
                'hours': th_hours, 'prefs': prefs
            })

        # Lab Component
        # Labs are allocated if: is_lab OR is_external_lab OR is_integrated
        # For integrated subjects, lab allocation is INDEPENDENT of theory hours
        is_lab = e.get("is_lab") or e.get("is_external_lab") or e.get("is_integrated")
        if is_lab:
            lab_dur = 3 if e.get("is_external_lab") else 2
            lab_reqs.append({
                'id': i, 'year': y, 'teacher': t, 'subject': s, 
                'duration': lab_dur, 'prefs': prefs,
                'is_integrated': e.get("is_integrated", False),
                'is_external_lab': e.get("is_external_lab", False)
            })

    # --- Variables ---
    # theory_vars[(req_idx, day, period)] = bool
    theory_vars = {} 
    # lab_vars[(req_idx, day, start_period)] = bool
    lab_vars = {}
    
    # 1. Create Theory Variables
    for r_idx, req in enumerate(theory_reqs):
        for d in DAYS:
            for p in TEACHING_PERIODS:
                theory_vars[(r_idx, d, p)] = model.NewBoolVar(f'T_{r_idx}_{d}_{p}')

    # 2. Create Lab Variables
    for r_idx, req in enumerate(lab_reqs):
        dur = req['duration']
        valid_starts = []
        if dur == 2:
            valid_starts = [0, 3, 6, 7]
        elif dur == 3:
            valid_starts = [0, 3, 6]
            
        for d in DAYS:
            for p in valid_starts:
                lab_vars[(r_idx, d, p)] = model.NewBoolVar(f'L_{r_idx}_{d}_{p}')

    # --- Constraints ---

    # C1. Subject Hours (Theory)
    for r_idx, req in enumerate(theory_reqs):
        model.Add(sum(theory_vars[(r_idx, d, p)] for d in DAYS for p in TEACHING_PERIODS) == req['hours'])

    # C2. Subject Hours (Lab) - Exactly one slot per lab requirement
    for r_idx, req in enumerate(lab_reqs):
        valid_starts = [0, 3, 6, 7] if req['duration'] == 2 else [0, 3, 6]
        model.Add(sum(lab_vars[(r_idx, d, p)] for d in DAYS for p in valid_starts) == 1)

    # C3. Single Class per Year/Day/Period
    for y in years:
        for d in DAYS:
            for p in TEACHING_PERIODS:
                # Gather all theory vars for this y,d,p
                active_vars = []
                for r_idx, req in enumerate(theory_reqs):
                    if req['year'] == y:
                        active_vars.append(theory_vars[(r_idx, d, p)])
                
                # Gather all lab vars that COVER this p
                for r_idx, req in enumerate(lab_reqs):
                    if req['year'] == y:
                        dur = req['duration']
                        valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                        for start in valid_starts:
                            covers_p = False
                            if start == 0:
                                if dur == 2: covers_p = (p in [0, 1])
                                else: covers_p = (p in [0, 1, 3]) 
                            elif start == 3:
                                if dur == 2: covers_p = (p in [3, 4])
                                else: covers_p = (p in [3, 4, 6])
                            elif start == 6:
                                if dur == 2: covers_p = (p in [6, 7])
                                else: covers_p = (p in [6, 7, 8])
                            elif start == 7: 
                                covers_p = (p in [7, 8])
                                
                            if covers_p:
                                active_vars.append(lab_vars[(r_idx, d, start)])
                
                model.Add(sum(active_vars) <= 1)

    # C5. Integrated + External Labs MUST be in 2:30-5:00 PM slot (period 6 start only)
    # If a subject is both integrated AND external, its lab can ONLY start at period 6
    for r_idx, req in enumerate(lab_reqs):
        if req.get('is_integrated') and req.get('is_external_lab'):
            # This lab MUST start at period 6 (the 2:30-5:00 slot)
            # Force all other start periods to be 0
            valid_starts = [0, 3, 6, 7] if req['duration'] == 2 else [0, 3, 6]
            for d in DAYS:
                for p in valid_starts:
                    if p != 6:  # Only period 6 is allowed
                        model.Add(lab_vars[(r_idx, d, p)] == 0)
    
    # C5b. Integrated-ONLY Labs (not external) MUST be in morning/midday slots
    # If a subject is integrated but NOT external, its lab can ONLY start at period 0 or 3
    # (9:00-11:00 or 11:15-1:15, excluding the afternoon 2:30-5:00 slot)
    for r_idx, req in enumerate(lab_reqs):
        if req.get('is_integrated') and not req.get('is_external_lab'):
            # This lab can ONLY start at period 0 or 3 (morning/midday slots)
            # Force afternoon start periods (6, 7) to be 0
            valid_starts = [0, 3, 6, 7] if req['duration'] == 2 else [0, 3, 6]
            for d in DAYS:
                for p in valid_starts:
                    if p not in [0, 3]:  # Only periods 0 and 3 are allowed
                        model.Add(lab_vars[(r_idx, d, p)] == 0)
    
    # C6. Only one theory class per subject per day
    # Group theory_reqs by (year, subject)
    subject_theory_map = {}  # (year, subject) -> [list of r_idx]
    for r_idx, req in enumerate(theory_reqs):
        key = (req['year'], req['subject'])
        if key not in subject_theory_map:
            subject_theory_map[key] = []
        subject_theory_map[key].append(r_idx)
    
    # For each subject, ensure at most 1 theory class per day
    for (year, subject), req_indices in subject_theory_map.items():
        for d in DAYS:
            # Sum all theory vars for this subject on this day
            day_vars = []
            for r_idx in req_indices:
                for p in TEACHING_PERIODS:
                    day_vars.append(theory_vars[(r_idx, d, p)])
            # At most 1 theory class for this subject on this day
            model.Add(sum(day_vars) <= 1)

    # C4. Teacher Availability & Rest Periods
    for t in teachers:
        for d in DAYS:
            for p in TEACHING_PERIODS:
                # 1. Is teacher busy at p?
                busy_vars = []
                
                # Theory
                for r_idx, req in enumerate(theory_reqs):
                    if req['teacher'] == t:
                        busy_vars.append(theory_vars[(r_idx, d, p)])
                
                # Labs
                for r_idx, req in enumerate(lab_reqs):
                    if req['teacher'] == t:
                        dur = req['duration']
                        valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                        for start in valid_starts:
                            covers_p = False
                            if start == 0: covers_p = (p in ([0, 1] if dur==2 else [0, 1, 3]))
                            elif start == 3: covers_p = (p in ([3, 4] if dur==2 else [3, 4, 6]))
                            elif start == 6: covers_p = (p in ([6, 7] if dur==2 else [6, 7, 8]))
                            elif start == 7: covers_p = (p in [7, 8])
                            
                            if covers_p:
                                busy_vars.append(lab_vars[(r_idx, d, start)])
                
                # Constraint: Teacher busy at most once at p
                is_busy = model.NewBoolVar(f'Busy_{t}_{d}_{p}')
                model.Add(sum(busy_vars) == is_busy)
                
                # 2. Rest Period Constraint
                # If is_busy is true, then teacher CANNOT be busy at next_period
                # unless it's part of the SAME lab block.
                # But we handle this by checking who forces a rest.
                
                rest_vars = [] # Variables that force a rest at 'p'
                
                # Theory at 'prev' forces rest at 'p' if NEXT_REST_MAP[prev] == p
                for prev in TEACHING_PERIODS:
                    if NEXT_REST_MAP.get(prev) == p:
                        for r_idx, req in enumerate(theory_reqs):
                            if req['teacher'] == t:
                                rest_vars.append(theory_vars[(r_idx, d, prev)])
                
                # Lab ending before 'p' forces rest at 'p'
                for r_idx, req in enumerate(lab_reqs):
                    if req['teacher'] == t:
                        dur = req['duration']
                        valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                        for start in valid_starts:
                            last_p = -1
                            if start == 0: last_p = 1 if dur==2 else 3
                            elif start == 3: last_p = 4 if dur==2 else 6
                            elif start == 6: last_p = 7 if dur==2 else 8
                            elif start == 7: last_p = 8
                            
                            if NEXT_REST_MAP.get(last_p) == p:
                                rest_vars.append(lab_vars[(r_idx, d, start)])

                # Constraint: If any variable in rest_vars is True, then is_busy must be False
                model.Add(sum(rest_vars) + is_busy <= 1)

    # C7. Morning Periods Must Be Filled
    # For every semester (year) on every working day, the first 3 periods MUST be filled
    # First 3 periods = Period 0 (9:00-10:00), Period 1 (10:00-11:00), Period 3 (11:15-12:15)
    # Note: Period 2 is Break, so we skip it
    MORNING_PERIODS = [0, 1, 3]
    
    for y in years:
        for d in DAYS:
            for p in MORNING_PERIODS:
                # At least one class must be scheduled in this morning period
                active_vars = []
                
                # Collect all theory vars for this year/day/period
                for r_idx, req in enumerate(theory_reqs):
                    if req['year'] == y:
                        active_vars.append(theory_vars[(r_idx, d, p)])
                
                # Collect all lab vars that COVER this period
                for r_idx, req in enumerate(lab_reqs):
                    if req['year'] == y:
                        dur = req['duration']
                        valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                        for start in valid_starts:
                            covers_p = False
                            if start == 0:
                                if dur == 2: covers_p = (p in [0, 1])
                                else: covers_p = (p in [0, 1, 3])
                            elif start == 3:
                                if dur == 2: covers_p = (p in [3, 4])
                                else: covers_p = (p in [3, 4, 6])
                            
                            if covers_p:
                                active_vars.append(lab_vars[(r_idx, d, start)])
                
                # Constraint: Morning period MUST have at least 1 class
                model.Add(sum(active_vars) >= 1)

    # C8. Afternoon Periods Must Be Filled in Order (Sequential)
    # Afternoon periods must be filled sequentially from period 6 onwards.
    # Afternoon periods: 6 (2:30-3:20), 7 (3:20-4:15), 8 (4:15-5:00)
    # Rules:
    #   - If period 7 is occupied, period 6 MUST also be occupied
    #   - If period 8 is occupied, periods 6 AND 7 MUST also be occupied
    # This ensures patterns like: [P6], [P6,P7], [P6,P7,P8], or [empty]
    # NOT allowed: [P7], [P8], [P7,P8], [P6,P8]
    AFTERNOON_PERIODS = [6, 7, 8]
    
    for y in years:
        for d in DAYS:
            # Check if period 6 has a class
            period_6_vars = []
            for r_idx, req in enumerate(theory_reqs):
                if req['year'] == y:
                    period_6_vars.append(theory_vars[(r_idx, d, 6)])
            for r_idx, req in enumerate(lab_reqs):
                if req['year'] == y:
                    dur = req['duration']
                    valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                    for start in valid_starts:
                        if start == 6 or (start == 3 and dur == 3):  # Labs covering period 6
                            period_6_vars.append(lab_vars[(r_idx, d, start)])
            
            # Check if period 7 has a class
            period_7_vars = []
            for r_idx, req in enumerate(theory_reqs):
                if req['year'] == y:
                    period_7_vars.append(theory_vars[(r_idx, d, 7)])
            for r_idx, req in enumerate(lab_reqs):
                if req['year'] == y:
                    dur = req['duration']
                    valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                    for start in valid_starts:
                        covers_7 = False
                        if start == 6: covers_7 = True  # All labs starting at 6 cover 7
                        elif start == 7: covers_7 = True  # Labs starting at 7 cover 7
                        if covers_7:
                            period_7_vars.append(lab_vars[(r_idx, d, start)])
            
            # Check if period 8 has a class
            period_8_vars = []
            for r_idx, req in enumerate(theory_reqs):
                if req['year'] == y:
                    period_8_vars.append(theory_vars[(r_idx, d, 8)])
            for r_idx, req in enumerate(lab_reqs):
                if req['year'] == y:
                    dur = req['duration']
                    valid_starts = [0, 3, 6, 7] if dur == 2 else [0, 3, 6]
                    for start in valid_starts:
                        if start == 6 or start == 7:  # Labs covering period 8
                            period_8_vars.append(lab_vars[(r_idx, d, start)])
            
            # Create boolean indicators for each period
            period_6_occupied = model.NewBoolVar(f'P6_occupied_Y{y}_D{d}')
            model.Add(sum(period_6_vars) >= 1).OnlyEnforceIf(period_6_occupied)
            model.Add(sum(period_6_vars) == 0).OnlyEnforceIf(period_6_occupied.Not())
            
            period_7_occupied = model.NewBoolVar(f'P7_occupied_Y{y}_D{d}')
            model.Add(sum(period_7_vars) >= 1).OnlyEnforceIf(period_7_occupied)
            model.Add(sum(period_7_vars) == 0).OnlyEnforceIf(period_7_occupied.Not())
            
            period_8_occupied = model.NewBoolVar(f'P8_occupied_Y{y}_D{d}')
            model.Add(sum(period_8_vars) >= 1).OnlyEnforceIf(period_8_occupied)
            model.Add(sum(period_8_vars) == 0).OnlyEnforceIf(period_8_occupied.Not())
            
            # Constraint 1: If period 7 is occupied, period 6 MUST be occupied
            # P7 => P6  (equivalent to: NOT P7 OR P6)
            model.AddBoolOr([period_7_occupied.Not(), period_6_occupied])
            
            # Constraint 2: If period 8 is occupied, period 7 MUST be occupied
            # P8 => P7  (equivalent to: NOT P8 OR P7)
            model.AddBoolOr([period_8_occupied.Not(), period_7_occupied])
            
            # Note: Constraint 2 combined with Constraint 1 ensures:
            # P8 => P7 => P6 (if 8 is filled, then 7 and 6 must also be filled)


    # --- Objective: Preferences ---
    pref_score = []
    for r_idx, req in enumerate(theory_reqs):
        prefs = req['prefs']
        for d in DAYS:
            for p in TEACHING_PERIODS:
                # Check preference
                score = 0
                if d in prefs:
                    if prefs[d] and int(prefs[d]) == p:
                        score = 100 # High bonus for exact match
                    else:
                        score = 10 # Small bonus for day match
                
                if score > 0:
                    pref_score.append(theory_vars[(r_idx, d, p)] * score)
                    
    model.Maximize(sum(pref_score))

    # --- Solve ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    # --- Reconstruct Timetable ---
    timetables = {y: {d: [None] * len(PERIODS) for d in DAYS} for y in years}
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("✅ OR-Tools found a solution!")
        
        # Fill Theory
        for r_idx, req in enumerate(theory_reqs):
            for d in DAYS:
                for p in TEACHING_PERIODS:
                    if solver.Value(theory_vars[(r_idx, d, p)]):
                        y = req['year']
                        s = req['subject']
                        timetables[y][d][p] = s

        # Fill Labs
        for r_idx, req in enumerate(lab_reqs):
            for d in DAYS:
                valid_starts = [0, 3, 6, 7] if req['duration'] == 2 else [0, 3, 6]
                for start in valid_starts:
                    if solver.Value(lab_vars[(r_idx, d, start)]):
                        y = req['year']
                        s = req['subject']
                        dur = req['duration']
                        label = f"{s} - Lab"
                        
                        periods = []
                        if start == 0: periods = [0, 1] if dur==2 else [0, 1, 3]
                        elif start == 3: periods = [3, 4] if dur==2 else [3, 4, 6]
                        elif start == 6: periods = [6, 7] if dur==2 else [6, 7, 8]
                        elif start == 7: periods = [7, 8]
                        
                        for p in periods:
                            timetables[y][d][p] = label

        # Fill empty slots with Tutorial
        for y in years:
            for d in DAYS:
                for p in TEACHING_PERIODS:
                    if timetables[y][d][p] is None:
                        timetables[y][d][p] = "Tutorial"

    else:
        print("❌ OR-Tools FAILED to find a solution. Constraints might be too tight.")
    
    return timetables, []
