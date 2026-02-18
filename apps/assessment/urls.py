from django.urls import path
from . import views

app_name = 'assessment'

urlpatterns = [
    # Exam URLs
    path('exams/', views.ExamListView.as_view(), name='exam_list'),
    path('exams/<uuid:pk>/', views.ExamDetailView.as_view(), name='exam_detail'),
    path('exams/create/', views.ExamCreateView.as_view(), name='exam_create'),
    path('exams/<uuid:pk>/update/', views.ExamUpdateView.as_view(), name='exam_update'),
    path('exams/<uuid:exam_id>/attendance/', views.exam_attendance, name='exam_attendance'),
    path('exams/<uuid:exam_id>/marks/', views.enter_marks, name='enter_marks'),
    path('grading/', views.grading_overview, name='grading_overview'),

    # Assignment URLs
    path('assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('assignments/<uuid:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    path('assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<uuid:assignment_id>/submit/', views.AssignmentSubmissionView.as_view(), name='assignment_submit'),
    path('assignments/submissions/<uuid:submission_id>/grade/', views.grade_assignment, name='grade_assignment'),

    # Result URLs
    path('results/', views.ResultListView.as_view(), name='result_list'),
    path('results/<uuid:pk>/', views.ResultDetailView.as_view(), name='result_detail'),

    # Report Card URLs
    path('report-cards/', views.ReportCardListView.as_view(), name='reportcard_list'),
    path('report-cards/<uuid:pk>/', views.ReportCardDetailView.as_view(), name='reportcard_detail'),
    path('results/<uuid:result_id>/generate-report/', views.generate_report_card, name='generate_report_card'),
    path('report-cards/<uuid:reportcard_id>/approve/', views.approve_report_card, name='approve_report_card'),

    # Dashboard and Analytics
    path('dashboard/', views.assessment_dashboard, name='dashboard'),
    path('analytics/', views.assessment_analytics, name='analytics'),

    # Student-specific views
    path('my-marks/', views.StudentMarksView.as_view(), name='student_marks'),

    # Question Bank and Question Management
    path('question-banks/', views.QuestionBankListView.as_view(), name='question_bank_list'),
    path('question-banks/create/', views.QuestionBankCreateView.as_view(), name='question_bank_create'),
    path('questions/', views.QuestionListView.as_view(), name='question_list'),
    path('questions/create/', views.QuestionCreateView.as_view(), name='question_create'),

    # Exam Composition and Taking
    path('exams/<uuid:exam_id>/compose/', views.compose_exam, name='compose_exam'),
    path('exams/<uuid:exam_id>/take/', views.take_exam, name='take_exam'),
    path('exams/<uuid:exam_id>/grade-answers/', views.grade_exam_answers, name='grade_exam_answers'),
    path('exams/<uuid:exam_id>/auto-calculate/', views.auto_calculate_marks, name='auto_calculate_marks'),

    # API endpoints
    path('api/class/<uuid:class_id>/subjects/', views.get_class_subjects, name='api_class_subjects'),
    path('api/student/<uuid:student_id>/progress/', views.get_student_progress, name='api_student_progress'),
]
