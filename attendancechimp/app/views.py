"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from datetime import datetime
import zoneinfo
import json
import io

from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
                     Lecture, QRCodeUpload, is_instructor, is_student)

CDT = zoneinfo.ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# HW2 — time, sum 
# ---------------------------------------------------------------------------

@csrf_exempt
def time_view(request):
    """Return the current Chicago time as HH:MM."""
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    now = datetime.now().astimezone(CDT)
    return HttpResponse(now.strftime("%H:%M"))


@csrf_exempt
def sum_view(request):
    """Return the sum of query parameters n1 and n2."""
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    try:
        n1 = float(request.GET['n1'])
        n2 = float(request.GET['n2'])
    except (KeyError, ValueError):
        return HttpResponse("Error: provide numeric n1 and n2", status=400)
    result = n1 + n2
    if result == int(result):
        return HttpResponse(str(int(result)))
    return HttpResponse(str(result))


# ---------------------------------------------------------------------------
# HW4  — index, user creation
# ---------------------------------------------------------------------------

def new(request):
    """Render the sign-up form (GET only)."""
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    return render(request, 'app/new.html')

def index(request):
    """Render the home page (index.html)."""
    now = datetime.now().astimezone(CDT)
    context = {
        'current_time': now.strftime("%H:%M"),
        'user': request.user,
    }
    return render(request, 'app/index.html', context)

@csrf_exempt
def createUser(request):
    """Create a new student or instructor user (POST only)."""
    if request.method != "POST":
        return HttpResponse("Error: only POST is allowed", status=405)
    try:
        user_name = request.POST['user_name']
        password = request.POST['password']
        email = request.POST['email']
        is_student_flag = request.POST.get('is_student', '1')
    except KeyError:
        return HttpResponse("Error: missing required fields", status=400)

    if User.objects.filter(email=email).exists():
        return HttpResponse("Error: email already in use", status=400)
    if User.objects.filter(username=user_name).exists():
        return HttpResponse("Error: user name already in use", status=400)

    user = User.objects.create_user(username=user_name, password=password,
                                    email=email)
    if str(is_student_flag) in ('1', 'true', 'True', 'on'):
        StudentProfile.objects.create(user=user)
    else:
        InstructorProfile.objects.create(user=user)

    user = authenticate(username=user_name, password=password)
    if user is not None:
        login(request, user)
    return HttpResponse("User created successfully", status=200)

@csrf_exempt
def new_course(request):
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    return render(request, 'app/new_course.html')

@csrf_exempt
def createCourse(request):
    if request.method != "POST":
        return HttpResponse("Error: only POST is allowed", status=405)
    if is_instructor(request.user):
        try:
            course_name = request.POST['course-name']
            start_time = request.POST['start-time']
            end_time = request.POST['end-time']
        except KeyError:
            return HttpResponse("Error: missing required fields", status=400)
        if Course.objects.filter(name=course_name).exists():
            return HttpResponse("Error: course name already in use", status=400)
        day_mon = request.POST.get('day-mon', 0)
        day_tue = request.POST.get('day-tue', 0)
        day_wed = request.POST.get('day-wed', 0)
        day_thu = request.POST.get('day-thu', 0)
        day_fri = request.POST.get('day-fri', 0)
        if not (day_mon or day_tue or day_wed or day_thu or day_fri):
            return HttpResponse("Error: no days selected", status=400)
        if day_mon != 0:
            day_mon = 1
        if day_tue != 0:
            day_tue = 1
        if day_wed != 0:
            day_wed = 1
        if day_thu != 0:
            day_thu = 1
        if day_fri != 1:
            day_fri = 1
        Course.objects.create(name=course_name, instructor = request.user, start_time = start_time,
        end_time = end_time, day_mon = day_mon, day_tue = day_tue, day_wed = day_wed, day_thu = day_thu, day_fri = day_fri)
        return HttpResponse("Course created successfully", status=200)
    else:
        return HttpResponse("Error: courses may only be created by instructors", status=401)

@csrf_exempt
def new_lecture(request):
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    return render(request, 'app/new_lecture.html')

@csrf_exempt
def createLecture(request):
    if request.method != "POST":
        return HttpResponse("Error: only POST is allowed", status=405)
    if is_instructor(request.user):
        choice = request.POST['choice']
        if not Course.objects.filter(name=choice).exists():
            return HttpResponse("Error: not a valid course", status=400)
        my_lecture = Lecture(course=Course.objects.filter(name=choice)[0])
        my_lecture.save()
        return HttpResponse("Lecture created succesfully", status=200)
    else:
        return HttpResponse("Error: lectures may only be created by instructors", status=401)

@csrf_exempt
def new_qr_upload(request):
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    return render(request, 'app/new_qr_upload.html')

@csrf_exempt
def createQRCodeUpload(request):
    if request.method != "POST":
        return HttpResponse("Error: only POST is allowed", status=405)
    if is_student(request.user):
        myimage = request.POST.get('imageUpload')
        my_qr = QRCodeUpload(student = request.user, image=myimage)
        my_qr.save()
        return HttpResponse("QR code saved succesfully", status=200)
    else:
        return HttpResponse("Error: QRs can only be uploaded by students", status=401)

@csrf_exempt
def dumpUploads(request):
    if request.method != "GET":
        return HttpResponse("Error: only GET is allowed", status=405)
    if not is_instructor(request.user):
        return HttpResponse("Error: upload dump may only be accessed by instructors",status=401)
    ret = []
    for upload in QRCodeUpload.objects.all():
        ret.append({"username": upload.student.username, "upload_time": str(upload.uploaded_at)})
    return JsonResponse(ret, safe=False)