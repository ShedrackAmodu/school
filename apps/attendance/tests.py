# apps/attendance/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

from apps.academics.models import Student, Class, AcademicSession, Subject, Timetable
from apps.users.models import UserProfile, Role, UserRole
from .models import (
    AttendanceConfig, AttendanceSession, DailyAttendance, 
    LeaveType, LeaveApplication
)

User = get_user_model()


class AttendanceViewsTestCase(TestCase):
    """Test cases for attendance views"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='testpass123'
        )
        # Create teacher profile
        self.teacher_profile = UserProfile.objects.create(
            user=self.teacher_user,
            employee_id='T001'
        )
        # Create teacher role
        teacher_role = Role.objects.create(
            name='Teacher',
            role_type='teacher',
            description='Teacher role'
        )
        # Assign role to teacher
        UserRole.objects.create(
            user=self.teacher_user,
            role=teacher_role,
            is_primary=True
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123'
        )
        self.student = Student.objects.create(
            user=self.student_user,
            admission_number='S001',
            date_of_birth=date(2010, 1, 1)
        )
        
        # Create academic session
        self.academic_session = AcademicSession.objects.create(
            name='2024/2025',
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True
        )
        
        # Create class
        self.class_obj = Class.objects.create(
            name='Primary 1',
            grade_level='Primary',
            section='A',
            academic_session=self.academic_session
        )
        self.class_obj.students.add(self.student)
        
        # Create attendance session
        self.attendance_session = AttendanceSession.objects.create(
            name='Morning Session',
            session_type='morning',
            start_time='08:00:00',
            end_time='12:00:00',
            academic_session=self.academic_session,
            is_active=True
        )
        
        # Create subject and timetable
        self.subject = Subject.objects.create(
            name='Mathematics',
            code='MATH001',
            academic_session=self.academic_session
        )
        
        self.timetable = Timetable.objects.create(
            class_assigned=self.class_obj,
            subject=self.subject,
            teacher=self.teacher_profile,
            day_of_week='monday',
            period_number=1,
            start_time='08:00:00',
            end_time='09:00:00',
            academic_session=self.academic_session,
            is_published=True
        )
        
        # Create leave type
        self.leave_type = LeaveType.objects.create(
            name='Sick Leave',
            allowed_for_students=True,
            allowed_for_teachers=True,
            max_days_per_year=10
        )
        
        self.client = Client()
    
    def test_attendance_dashboard_access(self):
        """Test attendance dashboard access for different user types"""
        # Test anonymous user
        response = self.client.get(reverse('attendance:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test student access
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('attendance:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Attendance')
        
        # Test teacher access
        self.client.logout()
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('attendance:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher Attendance Interface')
        
        # Test admin access
        self.client.logout()
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('attendance:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin dashboard')
    
    def test_teacher_attendance_interface(self):
        """Test teacher attendance interface access"""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('attendance:teacher_attendance_interface'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher Attendance Interface')
        self.assertContains(response, self.class_obj.name)
    
    def test_bulk_attendance_view(self):
        """Test bulk attendance marking view"""
        self.client.login(username='teacher', password='testpass123')
        
        # Test class selection page
        response = self.client.get(reverse('attendance:bulk_class_select'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.class_obj.name)
        
        # Test bulk marking page
        response = self.client.get(reverse('attendance:bulk_mark', kwargs={'class_id': self.class_obj.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.class_obj.name)
        self.assertContains(response, self.student.user.get_full_name())
    
    def test_daily_attendance_creation(self):
        """Test creating daily attendance records"""
        self.client.login(username='teacher', password='testpass123')
        
        # Test GET request
        response = self.client.get(reverse('attendance:daily_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Attendance Record')
        
        # Test POST request
        form_data = {
            'student': self.student.id,
            'date': date.today(),
            'attendance_session': self.attendance_session.id,
            'status': 'present',
            'remarks': 'Test attendance'
        }
        response = self.client.post(reverse('attendance:daily_create'), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Verify attendance was created
        attendance = DailyAttendance.objects.filter(
            student=self.student,
            date=date.today(),
            attendance_session=self.attendance_session
        ).first()
        self.assertIsNotNone(attendance)
        self.assertEqual(attendance.status, 'present')
        self.assertEqual(attendance.remarks, 'Test attendance')
        self.assertEqual(attendance.marked_by, self.teacher_user)
    
    def test_leave_application_creation(self):
        """Test leave application creation"""
        self.client.login(username='student', password='testpass123')
        
        # Test GET request
        response = self.client.get(reverse('attendance:leave_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apply for Leave')
        
        # Test POST request
        form_data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=1),
            'reason': 'Sick leave'
        }
        response = self.client.post(reverse('attendance:leave_create'), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Verify leave application was created
        leave = LeaveApplication.objects.filter(applicant=self.student_user).first()
        self.assertIsNotNone(leave)
        self.assertEqual(leave.leave_type, self.leave_type)
        self.assertEqual(leave.status, 'pending')
        self.assertEqual(leave.reason, 'Sick leave')
    
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        self.client.login(username='teacher', password='testpass123')
        
        # Create some test attendance data
        DailyAttendance.objects.create(
            student=self.student,
            date=date.today(),
            attendance_session=self.attendance_session,
            status='present',
            marked_by=self.teacher_user
        )
        
        # Test student attendance API
        response = self.client.get(reverse('attendance:api_student_attendance', kwargs={'student_id': self.student.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('monthly_data', data)
        self.assertIn('status_breakdown', data)
        self.assertIn('total_days', data)
        
        # Test mark attendance API
        response = self.client.post(reverse('attendance:api_mark_attendance'), {
            'student_id': self.student.id,
            'date': date.today(),
            'session_id': self.attendance_session.id,
            'status': 'late'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['created'])  # Should be True for new record
    
    def test_permission_required_views(self):
        """Test that permission-required views work correctly"""
        # Test that non-teacher cannot access teacher interface
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('attendance:teacher_attendance_interface'))
        self.assertEqual(response.status_code, 302)  # Redirect to login/dashboard
        
        # Test that non-staff cannot access admin views
        response = self.client.get(reverse('attendance:config'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class AttendanceModelsTestCase(TestCase):
    """Test cases for attendance models"""
    
    def setUp(self):
        """Set up test data"""
        self.academic_session = AcademicSession.objects.create(
            name='2024/2025',
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True
        )
        
        self.attendance_session = AttendanceSession.objects.create(
            name='Morning Session',
            session_type='morning',
            start_time='08:00:00',
            end_time='12:00:00',
            academic_session=self.academic_session,
            is_active=True
        )
    
    def test_attendance_session_str(self):
        """Test AttendanceSession string representation"""
        self.assertEqual(str(self.attendance_session), 'Morning Session')
    
    def test_daily_attendance_str(self):
        """Test DailyAttendance string representation"""
        user = User.objects.create_user(username='testuser', password='testpass')
        student = Student.objects.create(
            user=user,
            admission_number='S001',
            date_of_birth=date(2010, 1, 1)
        )
        
        attendance = DailyAttendance.objects.create(
            student=student,
            date=date.today(),
            attendance_session=self.attendance_session,
            status='present'
        )
        
        expected_str = f"{student.user.get_full_name()} - {date.today()} - Present"
        self.assertEqual(str(attendance), expected_str)
    
    def test_leave_application_str(self):
        """Test LeaveApplication string representation"""
        user = User.objects.create_user(username='testuser2', password='testpass')
        leave_type = LeaveType.objects.create(
            name='Sick Leave',
            allowed_for_students=True,
            allowed_for_teachers=True
        )
        
        leave = LeaveApplication.objects.create(
            applicant=user,
            leave_type=leave_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            reason='Test reason'
        )
        
        expected_str = f"{user.get_full_name()} - Sick Leave - {date.today()} to {date.today() + timedelta(days=1)}"
        self.assertEqual(str(leave), expected_str)
    


class AttendanceUtilsTestCase(TestCase):
    """Test cases for attendance utility functions"""
    
    def test_attendance_status_choices(self):
        """Test that attendance status choices are valid"""
        from .models import DailyAttendance
        
        status_choices = [choice[0] for choice in DailyAttendance.AttendanceStatus.choices]
        expected_statuses = ['present', 'absent', 'late', 'half_day', 'leave']
        
        for status in expected_statuses:
            self.assertIn(status, status_choices)
    
    def test_leave_status_choices(self):
        """Test that leave status choices are valid"""
        from .models import LeaveApplication
        
        status_choices = [choice[0] for choice in LeaveApplication.LeaveStatus.choices]
        expected_statuses = ['pending', 'approved', 'rejected', 'cancelled']
        
        for status in expected_statuses:
            self.assertIn(status, status_choices)
    
