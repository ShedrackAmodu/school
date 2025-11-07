# apps/assessment/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from django.core.validators import FileExtensionValidator

from django.utils import timezone
from datetime import datetime

from apps.core.models import CoreBaseModel
# Use app-label strings for related models to avoid import-time side-effects


class AssessmentBaseModel(CoreBaseModel):
    """
    Base model for all assessment-related models.
    """
    class Meta:
        abstract = True


class ExamType(AssessmentBaseModel):
    """
    Types of examinations: Unit Test, Mid-Term, Final, Quiz, etc.
    """
    name = models.CharField(_('exam type name'), max_length=100)
    code = models.CharField(_('exam type code'), max_length=20, unique=True)
    description = models.TextField(_('description'), blank=True)
    weightage = models.DecimalField(
        _('weightage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Weightage in percentage for final grade calculation')
    )
    is_final = models.BooleanField(_('is final exam'), default=False)
    order = models.PositiveIntegerField(_('display order'), default=0)

    class Meta:
        verbose_name = _('Exam Type')
        verbose_name_plural = _('Exam Types')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class GradingSystem(AssessmentBaseModel):
    """
    Grading system configuration (A+, A, B+, etc.)
    """
    name = models.CharField(_('grading system name'), max_length=100)
    code = models.CharField(_('grading system code'), max_length=20, unique=True)
    description = models.TextField(_('description'), blank=True)
    is_active = models.BooleanField(_('is active'), default=True)

    class Meta:
        verbose_name = _('Grading System')
        verbose_name_plural = _('Grading Systems')
        ordering = ['name']

    def __str__(self):
        return self.name


class Grade(AssessmentBaseModel):
    """
    Individual grades within a grading system.
    """
    grading_system = models.ForeignKey(
        GradingSystem,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name=_('grading system')
    )
    grade = models.CharField(_('grade'), max_length=10)
    description = models.CharField(_('description'), max_length=100)
    min_mark = models.DecimalField(
        _('minimum marks'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    max_mark = models.DecimalField(
        _('maximum marks'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    grade_point = models.DecimalField(
        _('grade point'),
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(4.0)]
    )
    remark = models.CharField(_('remark'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Grade')
        verbose_name_plural = _('Grades')
        ordering = ['grading_system', 'min_mark']
        unique_together = ['grading_system', 'grade']

    def __str__(self):
        return f"{self.grade} ({self.grading_system})"

    def clean(self):
        if self.min_mark >= self.max_mark:
            raise ValidationError(_('Minimum mark must be less than maximum mark.'))


class Exam(AssessmentBaseModel):
    """
    Examination schedule and details.
    """
    name = models.CharField(_('exam name'), max_length=200)
    code = models.CharField(_('exam code'), max_length=50, unique=True)
    exam_type = models.ForeignKey(
        ExamType,
        on_delete=models.PROTECT,
        related_name='exams',
        verbose_name=_('exam type')
    )
    academic_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name=_('academic class')
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name=_('subject')
    )
    exam_date = models.DateField(_('exam date'))
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    total_marks = models.DecimalField(
        _('total marks'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    passing_marks = models.DecimalField(
        _('passing marks'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    venue = models.CharField(_('exam venue'), max_length=200, blank=True)
    instructions = models.TextField(_('instructions'), blank=True)
    is_published = models.BooleanField(_('is published'), default=False)
    published_at = models.DateTimeField(_('published at'), null=True, blank=True)

    class Meta:
        verbose_name = _('Exam')
        verbose_name_plural = _('Exams')
        ordering = ['exam_date', 'start_time']
        indexes = [
            models.Index(fields=['academic_class', 'exam_date']),
            models.Index(fields=['subject', 'exam_type']),
        ]

    def __str__(self):
        return f"{self.name} - {self.academic_class} - {self.subject}"

    def clean(self):
        if self.passing_marks > self.total_marks:
            raise ValidationError(_('Passing marks cannot exceed total marks.'))
        
        if self.end_time <= self.start_time:
            raise ValidationError(_('End time must be after start time.'))

    @property
    def duration(self):
        """Calculate exam duration in minutes."""
        from datetime import datetime
        start = datetime.combine(self.exam_date, self.start_time)
        end = datetime.combine(self.exam_date, self.end_time)
        duration = end - start
        return duration.total_seconds() / 60


class ExamAttendance(CoreBaseModel):
    """
    Track student attendance for exams.
    """
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_attendance',
        verbose_name=_('exam')
    )
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='exam_attendance',
        verbose_name=_('student')
    )
    is_present = models.BooleanField(_('is present'), default=True)
    late_minutes = models.PositiveIntegerField(_('late minutes'), default=0)
    remarks = models.TextField(_('remarks'), blank=True)

    class Meta:
        verbose_name = _('Exam Attendance')
        verbose_name_plural = _('Exam Attendance')
        unique_together = ['exam', 'student']
        indexes = [
            models.Index(fields=['exam', 'student']),
        ]

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student} - {self.exam} - {status}"


class Mark(AssessmentBaseModel):
    """
    Individual student marks for exams.
    """
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='marks',
        verbose_name=_('exam')
    )
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='marks',
        verbose_name=_('student')
    )
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_marks = models.DecimalField(
        _('maximum marks'),
        max_digits=6,
        decimal_places=2,
        editable=False
    )
    percentage = models.DecimalField(
        _('percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        editable=False
    )
    is_absent = models.BooleanField(_('is absent'), default=False)
    grace_marks = models.DecimalField(
        _('grace marks'),
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    remarks = models.TextField(_('remarks'), blank=True)
    entered_by = models.ForeignKey(
        'academics.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        related_name='entered_marks',
        verbose_name=_('entered by')
    )
    entered_at = models.DateTimeField(_('entered at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Mark')
        verbose_name_plural = _('Marks')
        unique_together = ['exam', 'student']
        indexes = [
            models.Index(fields=['exam', 'student']),
            models.Index(fields=['student', 'exam']),
        ]

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.marks_obtained}"

    def clean(self):
        if not self.is_absent and self.marks_obtained > self.max_marks:
            raise ValidationError(_('Marks obtained cannot exceed maximum marks.'))

    def save(self, *args, **kwargs):
        # Set max_marks from exam
        if not self.max_marks:
            self.max_marks = self.exam.total_marks
        
        # Calculate percentage
        if not self.is_absent and self.max_marks > 0:
            self.percentage = (self.marks_obtained / self.max_marks) * 100
        else:
            self.percentage = 0
        
        super().save(*args, **kwargs)

    @property
    def is_pass(self):
        """Check if student passed the exam."""
        if self.is_absent:
            return False
        total_marks = self.marks_obtained + self.grace_marks
        return total_marks >= self.exam.passing_marks

    @property
    def final_marks(self):
        """Return marks including grace marks."""
        return self.marks_obtained + self.grace_marks


class Assignment(CoreBaseModel):
    class AssignmentType(models.TextChoices):
        HOMEWORK = 'homework', _('Homework')
        CLASSWORK = 'classwork', _('Classwork')
        PROJECT = 'project', _('Project')
        RESEARCH = 'research', _('Research Paper')
        PRESENTATION = 'presentation', _('Presentation')
        QUIZ = 'quiz', _('Quiz')
        EXAM = 'exam', _('Exam')
        LAB_REPORT = 'lab_report', _('Lab Report')
        ESSAY = 'essay', _('Essay')
        GROUP_PROJECT = 'group_project', _('Group Project')

    class SubmissionStatus(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SUBMITTED = 'submitted', _('Submitted')
        LATE = 'late', _('Late')
        UNDER_REVIEW = 'under_review', _('Under Review')
        GRADED = 'graded', _('Graded')
        RETURNED = 'returned', _('Returned')
        RESUBMITTED = 'resubmitted', _('Resubmitted')
        REJECTED = 'rejected', _('Rejected')

    # === BASIC INFORMATION ===
    title = models.CharField(_('assignment title'), max_length=200)
    assignment_type = models.CharField(
        _('assignment type'),
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.HOMEWORK
    )
    description = models.TextField(_('description'))
    instructions = models.TextField(_('instructions'), blank=True)
    
    # === ACADEMIC CONTEXT ===
    # From first model
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('subject')
    )
    teacher = models.ForeignKey(
        'academics.Teacher',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('teacher')
    )
    academic_session = models.ForeignKey(
        'academics.AcademicSession',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('academic session')
    )
    
    academic_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('academic class'),
        null=True,
        blank=True
    )

    # Backwards-compatible field used in several older indexes and helper methods
    class_assigned = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='assigned_assignments',
        verbose_name=_('class assigned'),
        null=True,
        blank=True
    )
    
    # === TIMING & DATES ===
    # From first model
    publish_date = models.DateTimeField(_('publish date'), default=timezone.now)
    due_date = models.DateTimeField(_('due date'))
    
    # From second model
    assigned_date = models.DateField(_('assigned date'), null=True, blank=True)
    
    # === GRADING & MARKS ===
    total_marks = models.DecimalField(
        _('total marks'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    passing_marks = models.DecimalField(
        _('passing marks'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Weightage fields from both models
    weightage = models.DecimalField(
        _('weightage in final grade'),
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Weightage in percentage for final grade')
    )
    
    grading_criteria = models.TextField(_('grading criteria'), blank=True)
    
    # === SUBMISSION MANAGEMENT ===
    allow_late_submissions = models.BooleanField(
        _('allow late submissions'),
        default=True
    )
    late_submission_penalty = models.DecimalField(
        _('late submission penalty percentage'),
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    max_submission_attempts = models.PositiveIntegerField(
        _('maximum submission attempts'),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    # === FILE MANAGEMENT ===
    attachment = models.FileField(
        _('attachment'),
        upload_to='assignments/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 'jpg', 'jpeg', 'png']
            )
        ]
    )
    file_size = models.PositiveIntegerField(_('file size in bytes'), null=True, blank=True)
    max_file_size = models.PositiveIntegerField(
        _('maximum file size for submissions'),
        default=10 * 1024 * 1024  # 10MB
    )
    
    # === ADDITIONAL FEATURES ===
    tags = models.CharField(_('tags'), max_length=500, blank=True)
    is_published = models.BooleanField(_('is published'), default=False)
    display_order = models.PositiveIntegerField(_('display order'), default=0)

    # === SUBMISSION FIELDS (for student submissions) ===
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        verbose_name=_('student'),
        null=True,
        blank=True
    )
    
    # Submission Content
    submission_date = models.DateTimeField(_('submission date'), null=True, blank=True)
    submission_text = models.TextField(_('submission text'), blank=True)
    submitted_content = models.TextField(_('submitted content'), blank=True)  # From second model
    
    submission_attachment = models.FileField(
        _('submission attachment'),
        upload_to='assignment_submissions/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 
                                  'jpg', 'jpeg', 'png', 'mp4', 'mp3']
            )
        ]
    )
    submission_file_size = models.PositiveIntegerField(_('submission file size in bytes'), null=True, blank=True)
    submission_file_name = models.CharField(_('original file name'), max_length=255, blank=True)
    
    # Submission Management
    submission_status = models.CharField(
        _('submission status'),
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.DRAFT
    )
    submission_attempt = models.PositiveIntegerField(_('submission attempt'), default=1)
    original_submission = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='resubmissions',
        verbose_name=_('original submission')
    )
    
    # Late Submission Tracking
    is_late_submission = models.BooleanField(_('is late submission'), default=False)
    late_minutes = models.PositiveIntegerField(_('minutes late'), default=0)

    # Grading fields
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    penalty_applied = models.DecimalField(
        _('penalty applied'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    final_marks = models.DecimalField(
        _('final marks after penalty'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    rubric_scores = models.JSONField(
        _('rubric scores'),
        null=True,
        blank=True
    )
    
    # Feedback System
    feedback = models.TextField(_('teacher feedback'), blank=True)
    student_feedback = models.TextField(_('student feedback'), blank=True)
    graded_by = models.ForeignKey(
        'academics.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
        verbose_name=_('graded by')
    )
    graded_date = models.DateTimeField(_('graded date'), null=True, blank=True)
    feedback_date = models.DateTimeField(_('feedback date'), null=True, blank=True)
    is_feedback_read = models.BooleanField(_('is feedback read by student'), default=False)
    feedback_read_date = models.DateTimeField(_('feedback read date'), null=True, blank=True)
    
    # Additional Metadata
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True)

    class Meta:
        verbose_name = _('Assignment')
        verbose_name_plural = _('Assignments')
        ordering = ['display_order', '-due_date', 'subject']
        indexes = [
            models.Index(fields=['subject', 'class_assigned']),
            models.Index(fields=['subject', 'academic_class']),
            models.Index(fields=['due_date', 'is_published']),
            models.Index(fields=['teacher', 'academic_session']),
            models.Index(fields=['assignment_type']),
            models.Index(fields=['student', 'submission_status']),
            models.Index(fields=['submission_status', 'graded_date']),
            models.Index(fields=['is_late_submission', 'submission_date']),
            models.Index(fields=['academic_class', 'due_date']),
            models.Index(fields=['subject', 'teacher']),
            models.Index(fields=['student', 'submission_date']),
        ]

    def __str__(self):
        if self.student:
            return f"{self.student} - {self.title} (Attempt {self.submission_attempt})"
        return f"{self.title} - {self.subject}"

    def clean(self):
        """Enhanced validation combining all validation rules"""
        # Date validations from both models
        if self.publish_date and self.due_date:
            if self.publish_date >= self.due_date:
                raise ValidationError(_('Due date must be after publish date.'))
        
        if self.assigned_date and self.due_date:
            if self.due_date.date() < self.assigned_date:
                raise ValidationError(_('Due date cannot be before assigned date.'))
        
        # Marks validations
        if self.passing_marks and self.passing_marks > self.total_marks:
            raise ValidationError(_('Passing marks cannot exceed total marks.'))
            
        if self.late_submission_penalty and self.late_submission_penalty > 100:
            raise ValidationError(_('Late submission penalty cannot exceed 100%.'))

        # Submission validations
        if self.marks_obtained is not None:
            if self.marks_obtained > self.total_marks:
                raise ValidationError(_('Obtained marks cannot exceed assignment total marks.'))
        
        if self.penalty_applied and self.penalty_applied < 0:
            raise ValidationError(_('Penalty cannot be negative.'))
            
        if self.final_marks and self.final_marks < 0:
            raise ValidationError(_('Final marks cannot be negative.'))
            
        # Class validation - ensure at least one class is set
        if not self.class_assigned and not self.academic_class:
            raise ValidationError(_('Either class_assigned or academic_class must be set.'))

    def save(self, *args, **kwargs):
        """Auto-manage assignment and submission logic"""
        # Auto-calculate file sizes
        if self.attachment:
            self.file_size = self.attachment.size
        
        if self.submission_attachment:
            self.submission_file_size = self.submission_attachment.size
            self.submission_file_name = self.submission_attachment.name
        
        # Handle date synchronization
        if self.assigned_date and not self.publish_date:
            self.publish_date = timezone.make_aware(
                datetime.combine(self.assigned_date, datetime.min.time())
            )
        
        # Auto-detect late submission
        if self.submission_date and self.submission_status in [self.SubmissionStatus.SUBMITTED, self.SubmissionStatus.LATE]:
            if self.submission_date > self.due_date:
                self.is_late_submission = True
                self.submission_status = self.SubmissionStatus.LATE

                # Calculate late minutes
                late_delta = self.submission_date - self.due_date
                self.late_minutes = int(late_delta.total_seconds() / 60)

                # Auto-apply penalty if configured
                if self.late_submission_penalty > 0 and self.marks_obtained:
                    self.penalty_applied = (self.marks_obtained * self.late_submission_penalty) / 100
                    self.final_marks = self.marks_obtained - self.penalty_applied

        # Auto-set graded dates
        if self.marks_obtained is not None:
            if not self.graded_date:
                self.graded_date = timezone.now()
            
        super().save(*args, **kwargs)

    @property
    def submission_count(self):
        """Get number of submissions for this assignment"""
        return Assignment.objects.filter(
            # Use the same identifying fields to find submissions for this assignment
            subject=self.subject,
            title=self.title,
            student__isnull=False
        ).count()

    @property
    def graded_count(self):
        """Get number of graded submissions"""
        return Assignment.objects.filter(
            subject=self.subject,
            title=self.title,
            student__isnull=False,
            submission_status=self.SubmissionStatus.GRADED
        ).count()

    @property
    def is_overdue(self):
        """Check if assignment is overdue"""
        return timezone.now() > self.due_date

    @property
    def days_until_due(self):
        """Get days until due date"""
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None

    @property
    def submission_rate(self):
        """Calculate submission rate percentage"""
        total_students = self.get_class().current_student_count if self.get_class() else 0
        if total_students > 0:
            return (self.submission_count / total_students) * 100
        return 0

    # === SUBMISSION PROPERTIES ===
    @property
    def is_graded(self):
        """Check if submission is graded"""
        return self.marks_obtained is not None

    @property
    def percentage(self):
        """Calculate percentage if graded"""
        current_marks = self.final_marks or self.marks_obtained
        if current_marks is not None and self.total_marks > 0:
            return (current_marks / self.total_marks) * 100
        return 0

    @property
    def is_passing(self):
        """Check if submission is passing."""
        current_marks = self.final_marks or self.marks_obtained
        if current_marks is not None and self.passing_marks:
            return current_marks >= self.passing_marks
        return None

    @property
    def can_resubmit(self):
        """Check if student can resubmit."""
        return (self.submission_attempt < self.max_submission_attempts and
                (self.allow_late_submissions or not self.is_late_submission))

    # === HELPER METHODS ===
    def get_class(self):
        """Get the class object, preferring academic_class over class_assigned"""
        return self.academic_class or self.class_assigned

    def get_marks(self):
        """Get the current marks, checking all possible fields"""
        return self.final_marks or self.marks_obtained

    def set_marks(self, marks):
        """Set marks across all relevant fields"""
        self.marks_obtained = marks
        if not self.is_late_submission or not self.late_submission_penalty:
            self.final_marks = marks

    def create_resubmission(self):
        """Create a new resubmission attempt."""
        if not self.can_resubmit:
            raise ValidationError(_('Maximum submission attempts reached.'))
            
        resubmission = Assignment(
            # Assignment fields
            title=self.title,
            assignment_type=self.assignment_type,
            description=self.description,
            instructions=self.instructions,
            subject=self.subject,
            class_assigned=self.class_assigned,
            academic_class=self.academic_class,
            teacher=self.teacher,
            academic_session=self.academic_session,
            total_marks=self.total_marks,
            passing_marks=self.passing_marks,
            weightage=self.weightage,
            grading_criteria=self.grading_criteria,
            publish_date=self.publish_date,
            due_date=self.due_date,
            assigned_date=self.assigned_date,
            allow_late_submissions=self.allow_late_submissions,
            late_submission_penalty=self.late_submission_penalty,
            max_submission_attempts=self.max_submission_attempts,
            max_file_size=self.max_file_size,
            
            # Submission fields
            student=self.student,
            original_submission=self,
            submission_attempt=self.submission_attempt + 1,
            submission_status=self.SubmissionStatus.DRAFT
        )
        return resubmission

    @classmethod
    def create_assignment_template(cls, **kwargs):
        """Create an assignment template without student submission data"""
        kwargs.update({
            'student': None,
            'submission_status': cls.SubmissionStatus.DRAFT,
            'submission_attempt': 1
        })
        return cls(**kwargs)

    def is_submission(self):
        """Check if this instance represents a student submission"""
        return self.student is not None

    def get_submissions(self):
        """Get all submissions for this assignment"""
        if self.is_submission():
            # This is a submission, get other submissions for the same assignment
            return Assignment.objects.filter(
                subject=self.subject,
                title=self.title,
                student__isnull=False
            ).exclude(pk=self.pk)
        else:
            # This is an assignment template, get all submissions
            return Assignment.objects.filter(
                subject=self.subject,
                title=self.title,
                student__isnull=False
            )


class Result(AssessmentBaseModel):
    """
    Consolidated results for students per academic class and exam type.
    """
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('student')
    )
    academic_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('academic class')
    )
    exam_type = models.ForeignKey(
        ExamType,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('exam type')
    )
    total_marks = models.DecimalField(
        _('total marks'),
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    percentage = models.DecimalField(
        _('percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    grade = models.ForeignKey(
        Grade,
        on_delete=models.PROTECT,
        related_name='results',
        verbose_name=_('grade'),
        null=True,
        blank=True
    )
    rank = models.PositiveIntegerField(_('rank'), null=True, blank=True)
    total_students = models.PositiveIntegerField(_('total students'))
    attendance_percentage = models.DecimalField(
        _('attendance percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Attendance percentage for the period')
    )
    remarks = models.TextField(_('remarks'), blank=True)
    is_promoted = models.BooleanField(_('is promoted'), default=False)
    promoted_to_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promoted_results',
        verbose_name=_('promoted to class')
    )

    class Meta:
        verbose_name = _('Result')
        verbose_name_plural = _('Results')
        unique_together = ['student', 'academic_class', 'exam_type']
        indexes = [
            models.Index(fields=['student', 'academic_class']),
            models.Index(fields=['academic_class', 'exam_type', 'rank']),
        ]

    def __str__(self):
        return f"{self.student} - {self.academic_class} - {self.exam_type}"

    def calculate_attendance_percentage(self):
        """Calculate attendance percentage for the result period."""
        # This would integrate with the attendance app
        # For now, it's a placeholder
        return 95.0  # Example value

    def save(self, *args, **kwargs):
        if not self.attendance_percentage:
            self.attendance_percentage = self.calculate_attendance_percentage()
        
        # Calculate percentage if not set
        if self.total_marks > 0 and not self.percentage:
            self.percentage = (self.marks_obtained / self.total_marks) * 100
        
        super().save(*args, **kwargs)


class ResultSubject(AssessmentBaseModel):
    """
    Subject-wise marks within a result.
    """
    result = models.ForeignKey(
        Result,
        on_delete=models.CASCADE,
        related_name='subject_marks',
        verbose_name=_('result')
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='result_marks',
        verbose_name=_('subject')
    )
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_marks = models.DecimalField(
        _('maximum marks'),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    percentage = models.DecimalField(
        _('percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    grade = models.ForeignKey(
        Grade,
        on_delete=models.PROTECT,
        related_name='subject_results',
        verbose_name=_('grade'),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Result Subject')
        verbose_name_plural = _('Result Subjects')
        unique_together = ['result', 'subject']
        ordering = ['subject__name']

    def __str__(self):
        return f"{self.result} - {self.subject}"

    def save(self, *args, **kwargs):
        # Calculate percentage
        if self.max_marks > 0:
            self.percentage = (self.marks_obtained / self.max_marks) * 100
        super().save(*args, **kwargs)


class ReportCard(AssessmentBaseModel):
    """
    Generated report cards for students.
    """
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='report_cards',
        verbose_name=_('student')
    )
    academic_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='report_cards',
        verbose_name=_('academic class')
    )
    exam_type = models.ForeignKey(
        ExamType,
        on_delete=models.CASCADE,
        related_name='report_cards',
        verbose_name=_('exam type')
    )
    result = models.OneToOneField(
        Result,
        on_delete=models.CASCADE,
        related_name='report_card',
        verbose_name=_('result')
    )
    generated_by = models.ForeignKey(
       'academics.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_report_cards',
        verbose_name=_('generated by')
    )
    generated_at = models.DateTimeField(_('generated at'), auto_now_add=True)
    is_approved = models.BooleanField(_('is approved'), default=False)
    approved_by = models.ForeignKey(
        'academics.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_report_cards',
        verbose_name=_('approved by')
    )
    approved_at = models.DateTimeField(_('approved at'), null=True, blank=True)
    comments = models.TextField(_('comments'), blank=True)
    parent_signature = models.BooleanField(_('parent signature received'), default=False)

    class Meta:
        verbose_name = _('Report Card')
        verbose_name_plural = _('Report Cards')
        unique_together = ['student', 'academic_class', 'exam_type']
        ordering = ['-generated_at']

    def __str__(self):
        return f"Report Card - {self.student} - {self.academic_class}"


class AssessmentRule(AssessmentBaseModel):
    """
    Rules and configurations for assessment system.
    """
    name = models.CharField(_('rule name'), max_length=200)
    key = models.CharField(_('rule key'), max_length=100, unique=True)
    value = models.JSONField(_('rule value'), default=dict)
    description = models.TextField(_('description'), blank=True)
    applies_to = models.CharField(
        _('applies to'),
        max_length=50,
        choices=[
            ('all', _('All')),
            ('exam', _('Exams')),
            ('assignment', _('Assignments')),
            ('grading', _('Grading')),
            ('attendance', _('Attendance'))
        ],
        default='all'
    )

    class Meta:
        verbose_name = _('Assessment Rule')
        verbose_name_plural = _('Assessment Rules')
        ordering = ['applies_to', 'name']

    def __str__(self):
        return f"{self.name} ({self.applies_to})"


class QuestionBank(AssessmentBaseModel):
    """
    Question bank for organizing questions by subject and topic.
    """
    name = models.CharField(_('question bank name'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='question_banks',
        verbose_name=_('subject')
    )
    academic_class = models.ForeignKey(
        'academics.Class',
        on_delete=models.CASCADE,
        related_name='question_banks',
        verbose_name=_('academic class')
    )
    topic = models.CharField(_('topic/chapter'), max_length=200, blank=True)
    difficulty_level = models.CharField(
        _('difficulty level'),
        max_length=20,
        choices=[
            ('easy', _('Easy')),
            ('medium', _('Medium')),
            ('hard', _('Hard')),
            ('expert', _('Expert'))
        ],
        default='medium'
    )
    is_active = models.BooleanField(_('is active'), default=True)

    class Meta:
        verbose_name = _('Question Bank')
        verbose_name_plural = _('Question Banks')
        ordering = ['subject', 'topic', 'difficulty_level']

    def __str__(self):
        return f"{self.name} - {self.subject} ({self.academic_class})"


class Question(AssessmentBaseModel):
    """
    Question model supporting multiple question types.
    """
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'multiple_choice', _('Multiple Choice')
        TRUE_FALSE = 'true_false', _('True/False')
        SHORT_ANSWER = 'short_answer', _('Short Answer')
        ESSAY = 'essay', _('Essay')

    question_bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('question bank')
    )
    question_type = models.CharField(
        _('question type'),
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE
    )
    question_text = models.TextField(_('question text'))
    explanation = models.TextField(_('explanation/answer key'), blank=True)
    marks = models.DecimalField(
        _('marks'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=1.0
    )
    time_limit = models.PositiveIntegerField(
        _('time limit in seconds'),
        null=True,
        blank=True,
        help_text=_('Time limit for answering this question')
    )
    difficulty_level = models.CharField(
        _('difficulty level'),
        max_length=20,
        choices=[
            ('easy', _('Easy')),
            ('medium', _('Medium')),
            ('hard', _('Hard')),
            ('expert', _('Expert'))
        ],
        default='medium'
    )
    tags = models.CharField(_('tags'), max_length=500, blank=True)
    is_active = models.BooleanField(_('is active'), default=True)

    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ['question_bank', 'difficulty_level', '-created_at']

    def __str__(self):
        return f"{self.question_text[:50]}... ({self.question_type})"

    def get_correct_options(self):
        """Get correct options for this question."""
        return self.options.filter(is_correct=True)

    def check_answer(self, answer_text, selected_options=None):
        """
        Check if the provided answer is correct.
        Returns (is_correct, marks_obtained)
        """
        if self.question_type in [self.QuestionType.MULTIPLE_CHOICE, self.QuestionType.TRUE_FALSE]:
            # For objective questions, check selected options
            if not selected_options:
                return False, 0

            correct_options = set(self.get_correct_options().values_list('id', flat=True))
            selected_set = set(selected_options)

            is_correct = correct_options == selected_set
            marks = self.marks if is_correct else 0
            return is_correct, marks

        elif self.question_type == self.QuestionType.SHORT_ANSWER:
            # For short answer, this would need manual grading
            # For now, return False (needs manual grading)
            return False, 0

        elif self.question_type == self.QuestionType.ESSAY:
            # Essays always need manual grading
            return False, 0

        return False, 0


class QuestionOption(AssessmentBaseModel):
    """
    Options for multiple choice and true/false questions.
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name=_('question')
    )
    option_text = models.TextField(_('option text'))
    is_correct = models.BooleanField(_('is correct'), default=False)
    order = models.PositiveIntegerField(_('display order'), default=0)

    class Meta:
        verbose_name = _('Question Option')
        verbose_name_plural = _('Question Options')
        ordering = ['question', 'order']
        unique_together = ['question', 'order']

    def __str__(self):
        return f"Option {self.order}: {self.option_text[:30]}..."

    def clean(self):
        if self.question.question_type == Question.QuestionType.TRUE_FALSE:
            # True/False questions should only have 2 options
            existing_options = QuestionOption.objects.filter(
                question=self.question
            ).exclude(pk=self.pk)
            if existing_options.count() >= 2:
                raise ValidationError(_('True/False questions can only have 2 options.'))

        elif self.question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
            # Multiple choice should have 2-6 options
            existing_options = QuestionOption.objects.filter(
                question=self.question
            ).exclude(pk=self.pk)
            if existing_options.count() >= 6:
                raise ValidationError(_('Multiple choice questions can have maximum 6 options.'))


class ExamQuestion(AssessmentBaseModel):
    """
    Links questions to exams with specific marks and order.
    """
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_questions',
        verbose_name=_('exam')
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='exam_questions',
        verbose_name=_('question')
    )
    marks = models.DecimalField(
        _('marks for this question'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    order = models.PositiveIntegerField(_('question order'), default=0)
    time_limit = models.PositiveIntegerField(
        _('time limit in seconds'),
        null=True,
        blank=True,
        help_text=_('Override question time limit for this exam')
    )

    class Meta:
        verbose_name = _('Exam Question')
        verbose_name_plural = _('Exam Questions')
        ordering = ['exam', 'order']
        unique_together = ['exam', 'question']

    def __str__(self):
        return f"{self.exam} - Q{self.order}: {self.question.question_text[:30]}..."

    def get_time_limit(self):
        """Get effective time limit (exam override or question default)."""
        return self.time_limit or self.question.time_limit


class StudentAnswer(AssessmentBaseModel):
    """
    Stores student answers for exam questions.
    """
    exam_question = models.ForeignKey(
        ExamQuestion,
        on_delete=models.CASCADE,
        related_name='student_answers',
        verbose_name=_('exam question')
    )
    student = models.ForeignKey(
        'academics.Student',
        on_delete=models.CASCADE,
        related_name='exam_answers',
        verbose_name=_('student')
    )
    answer_text = models.TextField(_('answer text'), blank=True)
    selected_options = models.JSONField(
        _('selected options'),
        null=True,
        blank=True,
        help_text=_('List of selected option IDs for multiple choice')
    )
    is_correct = models.BooleanField(_('is correct'), null=True, blank=True)
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    time_taken = models.PositiveIntegerField(
        _('time taken in seconds'),
        null=True,
        blank=True
    )
    submitted_at = models.DateTimeField(_('submitted at'), auto_now_add=True)
    is_graded = models.BooleanField(_('is graded'), default=False)

    class Meta:
        verbose_name = _('Student Answer')
        verbose_name_plural = _('Student Answers')
        unique_together = ['exam_question', 'student']
        ordering = ['exam_question__order', 'submitted_at']

    def __str__(self):
        return f"{self.student} - {self.exam_question} - {'Correct' if self.is_correct else 'Incorrect'}"

    def save(self, *args, **kwargs):
        # Auto-grade objective questions
        if not self.is_graded and self.exam_question:
            question = self.exam_question.question
            if question.question_type in [Question.QuestionType.MULTIPLE_CHOICE, Question.QuestionType.TRUE_FALSE]:
                self.is_correct, self.marks_obtained = question.check_answer(
                    self.answer_text,
                    self.selected_options
                )
                self.is_graded = True

        super().save(*args, **kwargs)

    def get_selected_option_objects(self):
        """Get the selected option objects."""
        if self.selected_options:
            return QuestionOption.objects.filter(id__in=self.selected_options)
        return QuestionOption.objects.none()


# Signal handlers for parent notifications
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Result)
def notify_parents_result_created(sender, instance, created, **kwargs):
    """Notify parents when a new result is created or updated."""
    if created or instance.pk:  # Only notify on creation or significant updates
        from apps.communication.views import create_notification
        from apps.academics.models import StudentParentRelationship

        student = instance.student

        # Get all parent relationships for this student
        parent_relationships = StudentParentRelationship.objects.filter(
            student=student,
            can_access_records=True
        ).select_related('parent__user')

        message = f"Your child {student.user.get_full_name()} has received results for {instance.exam_type.name} in {instance.academic_class.name}. "

        if instance.grade:
            message += f"Grade: {instance.grade.grade} ({instance.percentage:.1f}%)"
        else:
            message += f"Percentage: {instance.percentage:.1f}%"

        for relationship in parent_relationships:
            if relationship.parent.user:  # Ensure parent has a user account
                create_notification(
                    user=relationship.parent.user,
                    title=f"Academic Results - {student.user.get_full_name()}",
                    message=message,
                    notification_type='academic',
                    priority='high',
                    action_url=f"/academics/my-records/"  # Link to student records if parent has access
                )


@receiver(post_save, sender=ReportCard)
def notify_parents_report_card(sender, instance, created, **kwargs):
    """Notify parents when a report card is generated or approved."""
    if created or (instance.is_approved and not instance.approved_at):
        from apps.notification.views import create_notification
        from apps.academics.models import StudentParentRelationship

        student = instance.student

        # Get all parent relationships for this student
        parent_relationships = StudentParentRelationship.objects.filter(
            student=student,
            can_access_records=True
        ).select_related('parent__user')

        status = "generated" if created else "approved"
        message = f"Report card for {student.user.get_full_name()} has been {status} for {instance.exam_type.name} in {instance.academic_class.name}."

        for relationship in parent_relationships:
            if relationship.parent.user:
                create_notification(
                    user=relationship.parent.user,
                    title=f"Report Card {status.title()} - {student.user.get_full_name()}",
                    message=message,
                    notification_type='academic',
                    priority='high',
                    action_url=f"/assessment/report-cards/{instance.id}/"
                )


@receiver(post_save, sender=Mark)
def notify_parents_low_grades(sender, instance, created, **kwargs):
    """Notify parents when student receives low grades."""
    if created and instance.percentage < 50:  # Notify for grades below 50%
        from apps.notification.views import create_notification
        from apps.academics.models import StudentParentRelationship

        student = instance.student

        # Get all parent relationships for this student
        parent_relationships = StudentParentRelationship.objects.filter(
            student=student,
            can_access_records=True
        ).select_related('parent__user')

        message = f"Attention: Your child {student.user.get_full_name()} scored {instance.percentage:.1f}% in {instance.exam.subject.name} ({instance.exam.exam_type.name}). Please review their performance."

        for relationship in parent_relationships:
            if relationship.parent.user:
                create_notification(
                    user=relationship.parent.user,
                    title=f"Low Grade Alert - {student.user.get_full_name()}",
                    message=message,
                    notification_type='warning',
                    priority='high',
                    action_url=f"/academics/my-records/"
                )
