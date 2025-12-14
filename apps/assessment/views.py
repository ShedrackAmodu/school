# apps/assessment/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Max, Min, Count, Sum
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import (
    ExamType, GradingSystem, Grade, Exam, ExamAttendance, Mark,
    Assignment, Result, ResultSubject, ReportCard, AssessmentRule,
    QuestionBank, Question, QuestionOption, ExamQuestion, StudentAnswer
)
from .forms import (
    QuestionBankForm, QuestionForm, ExamCompositionForm, ExamForm
)
from apps.academics.models import Student, Teacher, Class, Subject
from apps.users.models import User


# =============================================================================
# PERMISSION DECORATORS AND MIXINS
# =============================================================================

def is_teacher(user):
    """Check if user is a teacher."""
    return hasattr(user, 'teacher_profile')

def is_student(user):
    """Check if user is a student."""
    return hasattr(user, 'student_profile')

def is_admin_or_teacher(user):
    """Check if user is admin or teacher."""
    return user.is_staff or hasattr(user, 'teacher_profile')

class TeacherRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a teacher."""
    def test_func(self):
        return is_teacher(self.request.user)

class StudentRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a student."""
    def test_func(self):
        return is_student(self.request.user)

class AdminOrTeacherRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is admin or teacher."""
    def test_func(self):
        return is_admin_or_teacher(self.request.user)


# =============================================================================
# EXAM VIEWS
# =============================================================================

class ExamListView(LoginRequiredMixin, ListView):
    """List all exams with filtering options."""
    model = Exam
    template_name = 'assessment/exams/exam_list.html'
    context_object_name = 'exams'
    paginate_by = 20

    def get_queryset(self):
        queryset = Exam.objects.select_related(
            'exam_type', 'academic_class', 'subject'
        ).filter(is_published=True)
        
        # Filter by class if provided
        class_id = self.request.GET.get('class_id')
        if class_id:
            queryset = queryset.filter(academic_class_id=class_id)
        
        # Filter by subject if provided
        subject_id = self.request.GET.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        # Filter by exam type if provided
        exam_type_id = self.request.GET.get('exam_type_id')
        if exam_type_id:
            queryset = queryset.filter(exam_type_id=exam_type_id)
        
        # For students, show only their class exams
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            current_class = student.current_class
            if current_class:
                queryset = queryset.filter(academic_class=current_class)
        
        # For teachers, show only exams they're involved in
        elif hasattr(self.request.user, 'teacher_profile'):
            teacher = self.request.user.teacher_profile
            # Get classes taught by this teacher
            taught_classes = Class.objects.filter(
                subject_assignments__teacher=teacher,
                subject_assignments__academic_session__is_current=True
            )
            queryset = queryset.filter(academic_class__in=taught_classes)
        
        return queryset.order_by('-exam_date', '-start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exam_types'] = ExamType.objects.filter(status='active')
        context['classes'] = Class.objects.filter(academic_session__is_current=True)
        context['subjects'] = Subject.objects.filter(is_active=True)
        return context


class ExamDetailView(LoginRequiredMixin, DetailView):
    """Display exam details."""
    model = Exam
    template_name = 'assessment/exams/exam_detail.html'
    context_object_name = 'exam'

    def get_queryset(self):
        queryset = Exam.objects.select_related(
            'exam_type', 'academic_class', 'subject'
        )

        # Filter based on user role
        user = self.request.user
        if hasattr(user, 'student_profile'):
            # Students can only see exams for their class
            queryset = queryset.filter(academic_class=user.student_profile.current_class)
        elif hasattr(user, 'teacher_profile'):
            # Teachers can only see exams for classes they teach
            taught_classes = Class.objects.filter(
                subject_assignments__teacher=user.teacher_profile,
                subject_assignments__academic_session__is_current=True
            ).distinct()
            queryset = queryset.filter(academic_class__in=taught_classes)
        else:
            # Admins can see all exams
            pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add attendance status for students
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            attendance = ExamAttendance.objects.filter(
                exam=self.object, student=student
            ).first()
            context['attendance'] = attendance

        # Add marks if available and published (only for authorized users)
        if self.object.is_published:
            marks_queryset = Mark.objects.filter(exam=self.object).select_related('student__user')

            # Filter marks based on user role
            user = self.request.user
            if hasattr(user, 'student_profile'):
                # Students can only see their own marks
                marks_queryset = marks_queryset.filter(student=user.student_profile)
            elif hasattr(user, 'teacher_profile'):
                # Teachers can see marks for their class
                marks_queryset = marks_queryset.filter(exam__academic_class__in=
                    Class.objects.filter(
                        subject_assignments__teacher=user.teacher_profile,
                        subject_assignments__academic_session__is_current=True
                    ).distinct())

            context['marks'] = marks_queryset

        return context


class ExamCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    """Create a new exam."""
    model = Exam
    form_class = ExamForm
    template_name = 'assessment/exams/exam_form.html'

    def get_success_url(self):
        return reverse_lazy('assessment:exam_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Set initial values for the form."""
        initial = super().get_initial()

        # Set default exam type if available
        default_exam_type = ExamType.objects.filter(
            status='active',
            is_final=False
        ).first()

        if default_exam_type:
            initial['exam_type'] = default_exam_type

        # Set default total marks
        initial['total_marks'] = 100
        initial['passing_marks'] = 40

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add exam types for template if needed
        context['exam_types'] = ExamType.objects.filter(status='active')

        # Add teacher's classes and subjects
        teacher = self.request.user.teacher_profile
        context['teacher_classes'] = Class.objects.filter(
            subject_assignments__teacher=teacher,
            subject_assignments__academic_session__is_current=True
        ).distinct()

        return context

    def form_valid(self, form):
        # Set the exam as unpublished by default
        form.instance.is_published = False

        # Add success message
        messages.success(self.request, 'Exam created successfully! You can now add questions to it.')

        response = super().form_valid(form)

        # Redirect to exam composition after creation
        return redirect('assessment:compose_exam', exam_id=self.object.pk)

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ExamUpdateView(LoginRequiredMixin, TeacherRequiredMixin, UpdateView):
    """Update an existing exam."""
    model = Exam
    form_class = ExamForm
    template_name = 'assessment/exams/exam_form.html'
    success_url = reverse_lazy('assessment:exam_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.instance.is_published and not form.instance.published_at:
            form.instance.published_at = timezone.now()
        messages.success(self.request, 'Exam updated successfully!')
        return super().form_valid(form)


@login_required
@user_passes_test(is_teacher)
def exam_attendance(request, exam_id):
    """Manage exam attendance for students."""
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == 'POST':
        # Check if this is a bulk save operation (JSON data)
        attendance_data_json = request.POST.get('attendance_data')
        if attendance_data_json:
            # Handle bulk save from JavaScript
            try:
                attendance_data = json.loads(attendance_data_json)
                is_final = request.POST.get('is_final') == 'true'

                created_count = 0
                updated_count = 0

                for student_id, data in attendance_data.items():
                    student = get_object_or_404(Student, id=int(student_id))
                    attendance, created = ExamAttendance.objects.update_or_create(
                        exam=exam,
                        student=student,
                        defaults={
                            'is_present': data.get('is_present', False),
                            'late_minutes': data.get('late_minutes', 0),
                            'remarks': data.get('remarks', '')
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                # Additional processing if finalized
                if is_final and not exam.is_locked_for_editing:
                    exam.save()  # Could add locking logic here

                return JsonResponse({
                    'success': True,
                    'created': created_count,
                    'updated': updated_count,
                    'message': f'Attendance {"finalized" if is_final else "saved"} successfully!'
                })

            except (json.JSONDecodeError, ValueError) as e:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid attendance data format'
                }, status=400)

        # Legacy: Handle individual student updates (for backward compatibility)
        student_id = request.POST.get('student_id')
        if student_id:
            is_present = request.POST.get('is_present') == 'true'
            late_minutes = int(request.POST.get('late_minutes', 0))
            remarks = request.POST.get('remarks', '')

            student = get_object_or_404(Student, id=student_id)

            attendance, created = ExamAttendance.objects.update_or_create(
                exam=exam,
                student=student,
                defaults={
                    'is_present': is_present,
                    'late_minutes': late_minutes,
                    'remarks': remarks
                }
            )

            return JsonResponse({'success': True, 'created': created})
        else:
            return JsonResponse({
                'success': False,
                'error': 'No valid data provided'
            }, status=400)

    # GET request - show attendance page
    students = exam.academic_class.enrollments.filter(
        enrollment_status='active'
    ).select_related('student__user')

    attendance_records = {
        record.student_id: record
        for record in ExamAttendance.objects.filter(exam=exam)
    }

    context = {
        'exam': exam,
        'students': students,
        'attendance_records': attendance_records
    }
    return render(request, 'assessment/exams/exam_attendance.html', context)


# =============================================================================
# MARK MANAGEMENT VIEWS
# =============================================================================

@login_required
@user_passes_test(is_teacher)
def enter_marks(request, exam_id):
    """Enter marks for an exam."""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        marks_data = json.loads(request.POST.get('marks_data', '{}'))
        
        for student_id, mark_data in marks_data.items():
            student = get_object_or_404(Student, id=student_id)
            marks_obtained = mark_data.get('marks_obtained')
            is_absent = mark_data.get('is_absent', False)
            grace_marks = mark_data.get('grace_marks', 0)
            remarks = mark_data.get('remarks', '')
            
            mark, created = Mark.objects.update_or_create(
                exam=exam,
                student=student,
                defaults={
                    'marks_obtained': marks_obtained if not is_absent else 0,
                    'is_absent': is_absent,
                    'grace_marks': grace_marks,
                    'remarks': remarks,
                    'entered_by': request.user.teacher_profile
                }
            )
        
        messages.success(request, 'Marks entered successfully!')
        return JsonResponse({'success': True})
    
    # GET request - show marks entry page
    students = exam.academic_class.enrollments.filter(
        enrollment_status='active'
    ).select_related('student__user')
    
    existing_marks = {
        mark.student_id: mark 
        for mark in Mark.objects.filter(exam=exam)
    }
    
    context = {
        'exam': exam,
        'students': students,
        'existing_marks': existing_marks
    }
    return render(request, 'assessment/exams/enter_marks.html', context)


@login_required
@user_passes_test(is_teacher)
def grading_overview(request):
    """Show grading overview for teachers - list of exams they can enter marks for."""
    teacher = request.user.teacher_profile

    # Get classes taught by this teacher
    taught_classes = Class.objects.filter(
        subject_assignments__teacher=teacher,
        subject_assignments__academic_session__is_current=True
    ).distinct()

    # Get exams for these classes
    exams = Exam.objects.filter(
        academic_class__in=taught_classes
    ).select_related('exam_type', 'academic_class', 'subject').order_by('-exam_date', '-start_time')

    # Add mark entry status for each exam
    exam_data = []
    for exam in exams:
        marks_entered = Mark.objects.filter(exam=exam).count()
        total_students = exam.academic_class.enrollments.filter(enrollment_status='active').count()

        exam_data.append({
            'exam': exam,
            'marks_entered': marks_entered,
            'total_students': total_students,
            'completion_percentage': (marks_entered / total_students * 100) if total_students > 0 else 0
        })

    context = {
        'exam_data': exam_data,
        'taught_classes': taught_classes
    }

    return render(request, 'assessment/grading_overview.html', context)


class StudentMarksView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    """View for students to see their marks."""
    template_name = 'assessment/results/student_marks.html'
    context_object_name = 'marks'
    paginate_by = 20

    def get_queryset(self):
        student = self.request.user.student_profile
        return Mark.objects.filter(
            student=student
        ).select_related('exam', 'exam__subject', 'exam__academic_class').order_by('-exam__exam_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        
        # Add summary statistics
        marks = self.get_queryset()
        if marks:
            context['total_exams'] = marks.count()
            context['average_percentage'] = marks.aggregate(
                avg=Avg('percentage')
            )['avg']
            context['highest_percentage'] = marks.aggregate(
                max=Max('percentage')
            )['max']
        
        return context


# =============================================================================
# ASSIGNMENT VIEWS
# =============================================================================

class AssignmentListView(LoginRequiredMixin, ListView):
    """List assignments with filtering."""
    model = Assignment
    template_name = 'assessment/assignments/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 15

    def get_queryset(self):
        # Get assignment templates (not student submissions)
        queryset = Assignment.objects.filter(
            student__isnull=True,
            is_published=True
        ).select_related('subject', 'teacher__user', 'academic_class')
        
        # Apply filters
        subject_id = self.request.GET.get('subject_id')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        assignment_type = self.request.GET.get('assignment_type')
        if assignment_type:
            queryset = queryset.filter(assignment_type=assignment_type)
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(due_date__gte=timezone.now())
        elif status == 'overdue':
            queryset = queryset.filter(due_date__lt=timezone.now())
        
        # For students, show only assignments for their class
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            current_class = student.current_class
            if current_class:
                queryset = queryset.filter(
                    Q(academic_class=current_class) | 
                    Q(class_assigned=current_class)
                )
        
        # For teachers, show only their assignments
        elif hasattr(self.request.user, 'teacher_profile'):
            teacher = self.request.user.teacher_profile
            queryset = queryset.filter(teacher=teacher)
        
        return queryset.order_by('-due_date', 'display_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(is_active=True)
        context['assignment_types'] = Assignment.AssignmentType.choices
        
        # Add submission status for students
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            submissions = {
                sub.title: sub 
                for sub in Assignment.objects.filter(
                    student=student,
                    title__in=[a.title for a in context['assignments']]
                )
            }
            context['submissions'] = submissions
        
        return context


class AssignmentDetailView(LoginRequiredMixin, DetailView):
    """Display assignment details."""
    model = Assignment
    template_name = 'assessment/assignments/assignment_detail.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        queryset = Assignment.objects.select_related(
            'subject', 'teacher__user', 'academic_class'
        )

        # Filter based on user role
        user = self.request.user
        if hasattr(user, 'student_profile'):
            # Students can only see assignments for their class or assigned to them
            queryset = queryset.filter(
                Q(academic_class=user.student_profile.current_class) |
                Q(class_assigned=user.student_profile.current_class) |
                Q(student=user.student_profile)
            )
        elif hasattr(user, 'teacher_profile'):
            # Teachers can only see their own assignments
            queryset = queryset.filter(teacher=user.teacher_profile)
        else:
            # Admins can see all assignments
            pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # For students, show their submission if exists
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            submission = Assignment.objects.filter(
                student=student,
                title=self.object.title,
                subject=self.object.subject
            ).order_by('-submission_attempt').first()
            context['submission'] = submission

        # For teachers, show submission statistics
        elif hasattr(self.request.user, 'teacher_profile'):
            submissions = Assignment.objects.filter(
                student__isnull=False,
                title=self.object.title,
                subject=self.object.subject
            ).select_related('student__user')
            context['submissions'] = submissions
            context['submission_count'] = submissions.count()
            context['graded_count'] = submissions.filter(
                submission_status=Assignment.SubmissionStatus.GRADED
            ).count()

        return context


class AssignmentCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    """Create a new assignment."""
    model = Assignment
    template_name = 'assessment/assignments/assignment_form.html'
    fields = [
        'title', 'assignment_type', 'subject', 'academic_class', 'class_assigned',
        'description', 'instructions', 'total_marks', 'passing_marks', 'weightage',
        'due_date', 'allow_late_submissions', 'late_submission_penalty',
        'max_submission_attempts', 'max_file_size', 'attachment', 'tags'
    ]
    success_url = reverse_lazy('assessment:assignment_list')

    def form_valid(self, form):
        form.instance.teacher = self.request.user.teacher_profile
        form.instance.academic_session = self.get_current_academic_session()
        form.instance.is_published = True
        messages.success(self.request, 'Assignment created successfully!')
        return super().form_valid(form)

    def get_current_academic_session(self):
        """Get current academic session."""
        from apps.academics.models import AcademicSession
        return AcademicSession.objects.filter(is_current=True).first()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Limit to classes taught by the teacher
        teacher = self.request.user.teacher_profile
        form.fields['academic_class'].queryset = Class.objects.filter(
            subject_assignments__teacher=teacher,
            subject_assignments__academic_session__is_current=True
        ).distinct()
        form.fields['class_assigned'].queryset = form.fields['academic_class'].queryset
        return form


class AssignmentSubmissionView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    """Submit an assignment."""
    model = Assignment
    template_name = 'assessment/assignments/assignment_submission.html'
    fields = ['submission_text', 'submission_attachment']
    
    def get_success_url(self):
        return reverse_lazy('assessment:assignment_detail', kwargs={'pk': self.kwargs['assignment_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment'] = get_object_or_404(
            Assignment, id=self.kwargs['assignment_id'], student__isnull=True
        )
        
        # Check for existing submissions
        student = self.request.user.student_profile
        existing_submissions = Assignment.objects.filter(
            student=student,
            title=context['assignment'].title,
            subject=context['assignment'].subject
        ).order_by('-submission_attempt')
        
        context['existing_submissions'] = existing_submissions
        context['latest_submission'] = existing_submissions.first()
        
        return context

    def form_valid(self, form):
        assignment_template = get_object_or_404(
            Assignment, id=self.kwargs['assignment_id'], student__isnull=True
        )
        student = self.request.user.student_profile
        
        # Check if student can submit
        latest_submission = Assignment.objects.filter(
            student=student,
            title=assignment_template.title,
            subject=assignment_template.subject
        ).order_by('-submission_attempt').first()
        
        if latest_submission:
            if not latest_submission.can_resubmit:
                messages.error(self.request, 'Maximum submission attempts reached.')
                return self.form_invalid(form)
            submission_attempt = latest_submission.submission_attempt + 1
            original_submission = latest_submission.original_submission or latest_submission
        else:
            submission_attempt = 1
            original_submission = None
        
        # Create submission
        submission = form.save(commit=False)
        submission.title = assignment_template.title
        submission.assignment_type = assignment_template.assignment_type
        submission.description = assignment_template.description
        submission.instructions = assignment_template.instructions
        submission.subject = assignment_template.subject
        submission.academic_class = assignment_template.academic_class
        submission.class_assigned = assignment_template.class_assigned
        submission.teacher = assignment_template.teacher
        submission.academic_session = assignment_template.academic_session
        submission.total_marks = assignment_template.total_marks
        submission.passing_marks = assignment_template.passing_marks
        submission.weightage = assignment_template.weightage
        submission.grading_criteria = assignment_template.grading_criteria
        submission.publish_date = assignment_template.publish_date
        submission.due_date = assignment_template.due_date
        submission.allow_late_submissions = assignment_template.allow_late_submissions
        submission.late_submission_penalty = assignment_template.late_submission_penalty
        submission.max_submission_attempts = assignment_template.max_submission_attempts
        submission.max_file_size = assignment_template.max_file_size
        
        submission.student = student
        submission.submission_attempt = submission_attempt
        submission.original_submission = original_submission
        submission.submission_date = timezone.now()
        submission.submission_status = Assignment.SubmissionStatus.SUBMITTED
        
        submission.save()
        messages.success(self.request, 'Assignment submitted successfully!')
        return redirect(self.get_success_url())


@login_required
@user_passes_test(is_teacher)
def grade_assignment(request, submission_id):
    """Grade a student's assignment submission."""
    submission = get_object_or_404(Assignment, id=submission_id, student__isnull=False)
    
    if request.method == 'POST':
        marks_obtained = request.POST.get('marks_obtained')
        feedback = request.POST.get('feedback', '')
        rubric_scores = request.POST.get('rubric_scores')
        
        if marks_obtained:
            submission.marks_obtained = marks_obtained
            submission.feedback = feedback
            submission.graded_by = request.user.teacher_profile
            submission.graded_date = timezone.now()
            submission.graded_at = timezone.now()
            submission.submission_status = Assignment.SubmissionStatus.GRADED
            
            if rubric_scores:
                submission.rubric_scores = json.loads(rubric_scores)
            
            submission.save()
            messages.success(request, 'Assignment graded successfully!')
        
        return redirect('assessment:assignment_detail', pk=submission.original_submission.id if submission.original_submission else submission.id)
    
    context = {
        'submission': submission,
        'assignment_template': submission.original_submission if submission.original_submission else submission
    }
    return render(request, 'assessment/assignments/grade_assignment.html', context)


# =============================================================================
# RESULT AND REPORT CARD VIEWS
# =============================================================================

class ResultListView(LoginRequiredMixin, ListView):
    """List results for students or teachers."""
    template_name = 'assessment/results/result_list.html'
    context_object_name = 'results'
    paginate_by = 20

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            # Student view - show their results
            student = self.request.user.student_profile
            return Result.objects.filter(
                student=student
            ).select_related('academic_class', 'exam_type', 'grade')
        
        elif hasattr(self.request.user, 'teacher_profile'):
            # Teacher view - show results for their classes
            teacher = self.request.user.teacher_profile
            taught_classes = Class.objects.filter(
                subject_assignments__teacher=teacher,
                subject_assignments__academic_session__is_current=True
            )
            return Result.objects.filter(
                academic_class__in=taught_classes
            ).select_related('student__user', 'academic_class', 'exam_type', 'grade')
        
        return Result.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options for teachers
        if hasattr(self.request.user, 'teacher_profile'):
            context['classes'] = Class.objects.filter(
                academic_session__is_current=True
            )
            context['exam_types'] = ExamType.objects.filter(status='active')
        
        return context


class ResultDetailView(LoginRequiredMixin, DetailView):
    """Display detailed result information."""
    model = Result
    template_name = 'assessment/results/result_detail.html'
    context_object_name = 'result'

    def get_queryset(self):
        queryset = Result.objects.select_related(
            'student__user', 'academic_class', 'exam_type', 'grade'
        ).prefetch_related('subject_marks__subject')

        # Filter based on user role
        user = self.request.user
        if hasattr(user, 'student_profile'):
            # Students can only see their own results
            queryset = queryset.filter(student=user.student_profile)
        elif hasattr(user, 'teacher_profile'):
            # Teachers can only see results for classes they teach
            taught_classes = Class.objects.filter(
                subject_assignments__teacher=user.teacher_profile,
                subject_assignments__academic_session__is_current=True
            ).distinct()
            queryset = queryset.filter(academic_class__in=taught_classes)
        else:
            # Admins can see all results
            pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add subject marks
        context['subject_marks'] = self.object.subject_marks.select_related('subject', 'grade')

        return context


class ReportCardListView(LoginRequiredMixin, ListView):
    """List report cards."""
    template_name = 'assessment/results/reportcard_list.html'
    context_object_name = 'report_cards'
    paginate_by = 15

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            # Student view
            student = self.request.user.student_profile
            return ReportCard.objects.filter(
                student=student, is_approved=True
            ).select_related('academic_class', 'exam_type', 'result')
        
        elif hasattr(self.request.user, 'teacher_profile'):
            # Teacher view
            teacher = self.request.user.teacher_profile
            taught_classes = Class.objects.filter(
                subject_assignments__teacher=teacher,
                subject_assignments__academic_session__is_current=True
            )
            return ReportCard.objects.filter(
                academic_class__in=taught_classes
            ).select_related('student__user', 'academic_class', 'exam_type', 'result')
        
        return ReportCard.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics for teachers
        if hasattr(self.request.user, 'teacher_profile'):
            report_cards = self.get_queryset()
            context['total_report_cards'] = report_cards.count()
            context['approved_count'] = report_cards.filter(is_approved=True).count()
            context['pending_approval'] = report_cards.filter(is_approved=False).count()
        
        return context


class ReportCardDetailView(LoginRequiredMixin, DetailView):
    """Display report card details."""
    model = ReportCard
    template_name = 'assessment/results/reportcard_detail.html'
    context_object_name = 'report_card'

    def get_queryset(self):
        return ReportCard.objects.select_related(
            'student__user', 'academic_class', 'exam_type', 'result'
        ).prefetch_related('result__subject_marks__subject')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check permissions
        user = self.request.user
        report_card = self.object
        
        if (hasattr(user, 'student_profile') and 
            report_card.student != user.student_profile):
            messages.error(self.request, 'You do not have permission to view this report card.')
            return redirect('assessment:reportcard_list')
        
        return context


@login_required
@user_passes_test(is_teacher)
def generate_report_card(request, result_id):
    """Generate a report card for a result."""
    result = get_object_or_404(Result, id=result_id)
    
    # Check if report card already exists
    report_card, created = ReportCard.objects.get_or_create(
        student=result.student,
        academic_class=result.academic_class,
        exam_type=result.exam_type,
        defaults={
            'result': result,
            'generated_by': request.user.teacher_profile,
            'is_approved': False
        }
    )
    
    if created:
        messages.success(request, 'Report card generated successfully!')
    else:
        messages.info(request, 'Report card already exists.')
    
    return redirect('assessment:reportcard_detail', pk=report_card.id)


@login_required
@user_passes_test(is_teacher)
def approve_report_card(request, reportcard_id):
    """Approve a report card."""
    report_card = get_object_or_404(ReportCard, id=reportcard_id)
    
    if request.method == 'POST':
        report_card.is_approved = True
        report_card.approved_by = request.user.teacher_profile
        report_card.approved_at = timezone.now()
        report_card.save()
        
        messages.success(request, 'Report card approved successfully!')
    
    return redirect('assessment:reportcard_detail', pk=reportcard_id)


# =============================================================================
# DASHBOARD AND ANALYTICS VIEWS
# =============================================================================

@login_required
def assessment_dashboard(request):
    """Assessment dashboard for students and teachers."""
    context = {}
    
    if hasattr(request.user, 'student_profile'):
        # Student dashboard
        student = request.user.student_profile
        context['recent_assignments'] = Assignment.objects.filter(
            Q(academic_class=student.current_class) | 
            Q(class_assigned=student.current_class),
            student__isnull=True,
            is_published=True
        ).select_related('subject')[:5]
        
        context['upcoming_exams'] = Exam.objects.filter(
            academic_class=student.current_class,
            exam_date__gte=timezone.now().date(),
            is_published=True
        ).select_related('subject')[:5]
        
        context['recent_marks'] = Mark.objects.filter(
            student=student
        ).select_related('exam', 'exam__subject')[:10]
        
        # Performance summary
        marks = Mark.objects.filter(student=student)
        if marks.exists():
            context['average_percentage'] = marks.aggregate(avg=Avg('percentage'))['avg']
            context['total_exams'] = marks.count()
            context['passed_exams'] = marks.filter(
                marks_obtained__gte=models.F('exam__passing_marks')
            ).count()
    
    elif hasattr(request.user, 'teacher_profile'):
        # Teacher dashboard
        teacher = request.user.teacher_profile
        taught_classes = Class.objects.filter(
            subject_assignments__teacher=teacher,
            subject_assignments__academic_session__is_current=True
        )
        
        context['recent_assignments'] = Assignment.objects.filter(
            teacher=teacher,
            student__isnull=True
        ).select_related('subject', 'academic_class')[:5]
        
        context['upcoming_exams'] = Exam.objects.filter(
            academic_class__in=taught_classes,
            exam_date__gte=timezone.now().date()
        ).select_related('subject', 'academic_class')[:5]
        
        context['pending_grading'] = Assignment.objects.filter(
            teacher=teacher,
            student__isnull=False,
            submission_status=Assignment.SubmissionStatus.SUBMITTED
        ).count()
        
        # Class performance summary
        class_performance = []
        for class_obj in taught_classes:
            marks = Mark.objects.filter(
                exam__academic_class=class_obj,
                exam__subject__in=class_obj.subject_assignments.filter(
                    teacher=teacher
                ).values('subject')
            )
            if marks.exists():
                avg_percentage = marks.aggregate(avg=Avg('percentage'))['avg']
                class_performance.append({
                    'class': class_obj,
                    'average_percentage': avg_percentage,
                    'total_students': class_obj.current_student_count
                })
        
        context['class_performance'] = class_performance
    
    return render(request, 'assessment/dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_teacher)
def assessment_analytics(request):
    """Advanced analytics for assessment data."""
    context = {}
    
    # Get filter parameters
    class_id = request.GET.get('class_id')
    subject_id = request.GET.get('subject_id')
    exam_type_id = request.GET.get('exam_type_id')
    
    # Base querysets
    marks_qs = Mark.objects.select_related('exam', 'student__user')
    assignments_qs = Assignment.objects.filter(student__isnull=False)
    
    # Apply filters
    if class_id:
        marks_qs = marks_qs.filter(exam__academic_class_id=class_id)
        assignments_qs = assignments_qs.filter(
            Q(academic_class_id=class_id) | Q(class_assigned_id=class_id)
        )
    
    if subject_id:
        marks_qs = marks_qs.filter(exam__subject_id=subject_id)
        assignments_qs = assignments_qs.filter(subject_id=subject_id)
    
    if exam_type_id:
        marks_qs = marks_qs.filter(exam__exam_type_id=exam_type_id)
    
    # Performance statistics
    if marks_qs.exists():
        context['marks_stats'] = marks_qs.aggregate(
            avg_percentage=Avg('percentage'),
            max_percentage=Max('percentage'),
            min_percentage=Min('percentage'),
            total_entries=Count('id')
        )
        
        # Grade distribution
        context['grade_distribution'] = marks_qs.values(
            'exam__academic_class__name'
        ).annotate(
            avg_percentage=Avg('percentage'),
            student_count=Count('student', distinct=True)
        )
    
    # Assignment statistics
    if assignments_qs.exists():
        context['assignment_stats'] = assignments_qs.aggregate(
            total_submissions=Count('id'),
            avg_marks=Avg('marks_obtained'),
            submission_rate=Count('id') * 100 / assignments_qs.values('student').distinct().count()
        )
    
    # Filter options
    context['classes'] = Class.objects.filter(academic_session__is_current=True)
    context['subjects'] = Subject.objects.filter(is_active=True)
    context['exam_types'] = ExamType.objects.filter(status='active')
    
    return render(request, 'assessment/dashboard/analytics.html', context)


# =============================================================================
# API VIEWS FOR AJAX CALLS
# =============================================================================

@login_required
@require_http_methods(["GET"])
def get_class_subjects(request, class_id):
    """Get subjects for a specific class (AJAX)."""
    subjects = Subject.objects.filter(
        subject_assignments__class_assigned_id=class_id,
        subject_assignments__academic_session__is_current=True
    ).distinct().values('id', 'name')
    
    return JsonResponse(list(subjects), safe=False)


@login_required
@require_http_methods(["GET"])
def get_student_progress(request, student_id):
    """Get student progress data (AJAX)."""
    student = get_object_or_404(Student, id=student_id)

    # Check permissions
    if (hasattr(request.user, 'teacher_profile') or
        (hasattr(request.user, 'student_profile') and request.user.student_profile == student)):

        marks = Mark.objects.filter(student=student).select_related('exam__subject')
        assignments = Assignment.objects.filter(student=student).select_related('subject')

        progress_data = {
            'subject_performance': [],
            'assignment_completion': {
                'total': assignments.count(),
                'graded': assignments.filter(submission_status='graded').count(),
                'pending': assignments.filter(submission_status='submitted').count()
            }
        }

        # Subject-wise performance
        for subject in Subject.objects.filter(
            exams__marks__student=student
        ).distinct():
            subject_marks = marks.filter(exam__subject=subject)
            if subject_marks.exists():
                avg_percentage = subject_marks.aggregate(avg=Avg('percentage'))['avg']
                progress_data['subject_performance'].append({
                    'subject': subject.name,
                    'average_percentage': avg_percentage,
                    'exam_count': subject_marks.count()
                })

        return JsonResponse(progress_data)

    return JsonResponse({'error': 'Permission denied'}, status=403)


# =============================================================================
# QUESTION BANK AND QUESTION MANAGEMENT VIEWS
# =============================================================================

class QuestionBankListView(LoginRequiredMixin, TeacherRequiredMixin, ListView):
    """List question banks for teachers."""
    model = QuestionBank
    template_name = 'assessment/questions/question_bank_list.html'
    context_object_name = 'question_banks'
    paginate_by = 20

    def get_queryset(self):
        teacher = self.request.user.teacher_profile

        # Get classes taught by this teacher
        taught_classes = Class.objects.filter(
            subject_assignments__teacher=teacher,
            subject_assignments__academic_session__is_current=True
        ).distinct()

        return QuestionBank.objects.filter(
            academic_class__in=taught_classes
        ).select_related('subject', 'academic_class').order_by('-created_at')


class QuestionBankCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    """Create a new question bank."""
    model = QuestionBank
    form_class = QuestionBankForm
    template_name = 'assessment/questions/question_bank_form.html'
    success_url = reverse_lazy('assessment:question_bank_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user.teacher_profile
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user.teacher_profile
        messages.success(self.request, 'Question bank created successfully!')
        return super().form_valid(form)


class QuestionListView(LoginRequiredMixin, TeacherRequiredMixin, ListView):
    """List questions with filtering."""
    model = Question
    template_name = 'assessment/questions/question_list.html'
    context_object_name = 'questions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Question.objects.select_related(
            'question_bank__subject', 'question_bank__academic_class'
        )

        # Filter by question bank if provided
        question_bank_id = self.request.GET.get('question_bank_id')
        if question_bank_id:
            queryset = queryset.filter(question_bank_id=question_bank_id)

        # Filter by question type
        question_type = self.request.GET.get('question_type')
        if question_type:
            queryset = queryset.filter(question_type=question_type)

        # Filter by difficulty
        difficulty = self.request.GET.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)

        # Only show questions from question banks accessible to the teacher
        teacher = self.request.user.teacher_profile
        taught_classes = Class.objects.filter(
            subject_assignments__teacher=teacher,
            subject_assignments__academic_session__is_current=True
        ).distinct()

        queryset = queryset.filter(question_bank__academic_class__in=taught_classes)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['question_banks'] = QuestionBank.objects.filter(
            academic_class__in=Class.objects.filter(
                subject_assignments__teacher=self.request.user.teacher_profile,
                subject_assignments__academic_session__is_current=True
            ).distinct()
        )
        context['question_types'] = Question.QuestionType.choices
        context['difficulty_levels'] = [
            ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard'), ('expert', 'Expert')
        ]
        return context


class QuestionCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    """Create a new question."""
    model = Question
    form_class = QuestionForm
    template_name = 'assessment/questions/question_form.html'
    success_url = reverse_lazy('assessment:question_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['teacher'] = self.request.user.teacher_profile
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        # Handle options for multiple choice and true/false questions
        question = self.object
        if question.question_type in ['multiple_choice', 'true_false']:
            options_data = self.request.POST.getlist('option_text')
            correct_options = self.request.POST.getlist('is_correct')

            for i, option_text in enumerate(options_data):
                if option_text.strip():  # Only create non-empty options
                    QuestionOption.objects.create(
                        question=question,
                        option_text=option_text.strip(),
                        is_correct=str(i) in correct_options,
                        order=i
                    )

        messages.success(self.request, 'Question created successfully!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_options'] = 6 if self.request.POST.get('question_type') == 'multiple_choice' else 2
        return context


@login_required
@user_passes_test(is_teacher)
def compose_exam(request, exam_id):
    """Compose an exam by selecting questions from question banks."""
    exam = get_object_or_404(Exam, id=exam_id)
    teacher = request.user.teacher_profile

    # Check if teacher has access to this exam
    if not Class.objects.filter(
        subject_assignments__teacher=teacher,
        subject_assignments__subject=exam.subject,
        subject_assignments__academic_session__is_current=True
    ).exists():
        messages.error(request, 'You do not have permission to modify this exam.')
        return redirect('assessment:exam_list')

    if request.method == 'POST':
        form = ExamCompositionForm(request.POST, exam=exam)
        if form.is_valid():
            question_bank = form.cleaned_data['question_bank']
            num_mc = form.cleaned_data['num_multiple_choice']
            num_tf = form.cleaned_data['num_true_false']
            num_sa = form.cleaned_data['num_short_answer']
            num_essay = form.cleaned_data['num_essay']
            marks_mc = form.cleaned_data['marks_per_multiple_choice']
            marks_tf = form.cleaned_data['marks_per_true_false']
            randomize = form.cleaned_data['randomize_order']

            # Get questions from the selected question bank
            mc_questions = list(Question.objects.filter(
                question_bank=question_bank,
                question_type='multiple_choice',
                is_active=True
            ))
            tf_questions = list(Question.objects.filter(
                question_bank=question_bank,
                question_type='true_false',
                is_active=True
            ))
            sa_questions = list(Question.objects.filter(
                question_bank=question_bank,
                question_type='short_answer',
                is_active=True
            ))
            essay_questions = list(Question.objects.filter(
                question_bank=question_bank,
                question_type='essay',
                is_active=True
            ))

            if randomize:
                import random
                random.shuffle(mc_questions)
                random.shuffle(tf_questions)
                random.shuffle(sa_questions)
                random.shuffle(essay_questions)

            # Select the required number of questions
            selected_questions = []
            order = 0

            # Add multiple choice questions
            for q in mc_questions[:num_mc]:
                selected_questions.append((q, marks_mc, order))
                order += 1

            # Add true/false questions
            for q in tf_questions[:num_tf]:
                selected_questions.append((q, marks_tf, order))
                order += 1

            # Add short answer questions (assume 5 marks each if not specified)
            for q in sa_questions[:num_sa]:
                selected_questions.append((q, 5.0, order))
                order += 1

            # Add essay questions (assume 10 marks each if not specified)
            for q in essay_questions[:num_essay]:
                selected_questions.append((q, 10.0, order))
                order += 1

            # Create ExamQuestion instances
            for question, marks, order_num in selected_questions:
                ExamQuestion.objects.create(
                    exam=exam,
                    question=question,
                    marks=marks,
                    order=order_num
                )

            # Update exam total marks
            total_marks = sum(marks for _, marks, _ in selected_questions)
            exam.total_marks = total_marks
            exam.save()

            messages.success(request, f'Exam composed successfully with {len(selected_questions)} questions!')
            return redirect('assessment:exam_detail', pk=exam.id)
    else:
        form = ExamCompositionForm(exam=exam)

    context = {
        'exam': exam,
        'form': form,
        'existing_questions': ExamQuestion.objects.filter(exam=exam).select_related('question')
    }
    return render(request, 'assessment/exams/exam_compose.html', context)


# =============================================================================
# STUDENT EXAM TAKING VIEWS
# =============================================================================

@login_required
@user_passes_test(is_student)
def take_exam(request, exam_id):
    """Allow students to take an exam."""
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)
    student = request.user.student_profile

    # Check if student belongs to the exam class
    if student.current_class != exam.academic_class:
        messages.error(request, 'You are not enrolled in this class.')
        return redirect('assessment:exam_list')

    # Check if exam is currently active
    now = timezone.now()
    exam_start = timezone.make_aware(
        datetime.combine(exam.exam_date, exam.start_time)
    )
    exam_end = timezone.make_aware(
        datetime.combine(exam.exam_date, exam.end_time)
    )

    if now < exam_start:
        messages.error(request, 'Exam has not started yet.')
        return redirect('assessment:exam_list')
    elif now > exam_end:
        messages.error(request, 'Exam has already ended.')
        return redirect('assessment:exam_list')

    # Check attendance
    attendance = ExamAttendance.objects.filter(
        exam=exam, student=student, is_present=True
    ).exists()
    if not attendance:
        messages.error(request, 'You are not marked as present for this exam.')
        return redirect('assessment:exam_list')

    # Get exam questions
    exam_questions = ExamQuestion.objects.filter(
        exam=exam
    ).select_related('question').order_by('order')

    if not exam_questions.exists():
        messages.error(request, 'No questions available for this exam.')
        return redirect('assessment:exam_list')

    if request.method == 'POST':
        # Process submitted answers
        for eq in exam_questions:
            answer_text = request.POST.get(f'answer_{eq.id}', '')
            selected_options = request.POST.getlist(f'options_{eq.id}')

            # Create or update student answer
            StudentAnswer.objects.update_or_create(
                exam_question=eq,
                student=student,
                defaults={
                    'answer_text': answer_text,
                    'selected_options': selected_options if selected_options else None,
                    'submitted_at': timezone.now()
                }
            )

        messages.success(request, 'Exam submitted successfully!')
        return redirect('assessment:exam_list')

    # GET request - show exam
    existing_answers = {
        sa.exam_question_id: sa
        for sa in StudentAnswer.objects.filter(
            exam_question__exam=exam,
            student=student
        )
    }

    context = {
        'exam': exam,
        'exam_questions': exam_questions,
        'existing_answers': existing_answers,
        'time_remaining': int((exam_end - now).total_seconds())
    }
    return render(request, 'assessment/exams/take_exam.html', context)


@login_required
@user_passes_test(is_teacher)
def grade_exam_answers(request, exam_id):
    """Grade subjective answers in an exam."""
    exam = get_object_or_404(Exam, id=exam_id)
    teacher = request.user.teacher_profile

    # Check permissions
    if not Class.objects.filter(
        subject_assignments__teacher=teacher,
        subject_assignments__subject=exam.subject
    ).exists():
        messages.error(request, 'You do not have permission to grade this exam.')
        return redirect('assessment:exam_list')

    if request.method == 'POST':
        answer_id = request.POST.get('answer_id')
        marks = request.POST.get('marks_obtained')

        if answer_id and marks:
            answer = get_object_or_404(StudentAnswer, id=answer_id, exam_question__exam=exam)
            answer.marks_obtained = marks
            answer.is_graded = True
            answer.save()

            messages.success(request, 'Answer graded successfully!')

        return redirect('assessment:grade_exam_answers', exam_id=exam.id)

    # Get all student answers for subjective questions
    subjective_questions = ExamQuestion.objects.filter(
        exam=exam,
        question__question_type__in=['short_answer', 'essay']
    ).values_list('id', flat=True)

    student_answers = StudentAnswer.objects.filter(
        exam_question_id__in=subjective_questions
    ).select_related(
        'exam_question__question', 'student__user'
    ).order_by('student__user__first_name', 'exam_question__order')

    context = {
        'exam': exam,
        'student_answers': student_answers,
        'total_to_grade': student_answers.filter(is_graded=False).count()
    }
    return render(request, 'assessment/exams/grade_exam_answers.html', context)


@login_required
@user_passes_test(is_teacher)
def auto_calculate_marks(request, exam_id):
    """Automatically calculate marks for an exam based on question-based answers."""
    exam = get_object_or_404(Exam, id=exam_id)

    # Calculate marks for each student
    students = exam.academic_class.enrollments.filter(
        enrollment_status='active'
    ).values_list('student', flat=True)

    calculated_marks = []
    for student_id in students:
        student = Student.objects.get(id=student_id)

        # Sum up marks from all answered questions
        total_marks = StudentAnswer.objects.filter(
            exam_question__exam=exam,
            student=student,
            is_graded=True
        ).aggregate(total=Sum('marks_obtained'))['total'] or 0

        # Create or update mark record
        mark, created = Mark.objects.update_or_create(
            exam=exam,
            student=student,
            defaults={
                'marks_obtained': total_marks,
                'entered_by': request.user.teacher_profile
            }
        )

        calculated_marks.append({
            'student': student,
            'marks': total_marks,
            'created': created
        })

    messages.success(request, f'Marks calculated for {len(calculated_marks)} students!')
    return redirect('assessment:exam_detail', pk=exam.id)
