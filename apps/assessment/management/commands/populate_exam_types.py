"""
Management command to populate default exam types.

This command creates standard exam types that are commonly used in school management systems.
It is safe to run multiple times as it uses get_or_create to avoid duplicates.
"""

from django.core.management.base import BaseCommand
from apps.assessment.models import ExamType


class Command(BaseCommand):
    help = 'Populate database with default exam types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all exam types before creating defaults',
        )

    def handle(self, *args, **options):
        # Default exam types with their configurations
        default_exam_types = [
            {
                'name': 'Unit Test',
                'code': 'UNIT',
                'description': 'Small unit tests to assess specific topics or chapters',
                'weightage': 10.0,
                'is_final': False,
                'order': 1,
            },
            {
                'name': 'Mid-Term',
                'code': 'MID',
                'description': 'Mid-term examination covering half the syllabus',
                'weightage': 30.0,
                'is_final': False,
                'order': 2,
            },
            {
                'name': 'Final Exam',
                'code': 'FINAL',
                'description': 'Final examination covering the complete syllabus',
                'weightage': 60.0,
                'is_final': True,
                'order': 3,
            },
            {
                'name': 'Quiz',
                'code': 'QUIZ',
                'description': 'Short assessment to test understanding of recent topics',
                'weightage': 5.0,
                'is_final': False,
                'order': 4,
            },
            {
                'name': 'Practical',
                'code': 'PRAC',
                'description': 'Practical examination for subjects requiring hands-on assessment',
                'weightage': 20.0,
                'is_final': False,
                'order': 5,
            },
        ]

        if options['reset']:
            self.stdout.write('Resetting all exam types...')
            ExamType.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('All exam types deleted')
            )

        created_count = 0
        updated_count = 0

        for exam_type_data in default_exam_types:
            exam_type, created = ExamType.objects.get_or_create(
                code=exam_type_data['code'],
                defaults=exam_type_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created exam type: {exam_type.name} ({exam_type.code})'
                    )
                )
            else:
                # Update existing exam type if any fields have changed
                updated = False
                for field, value in exam_type_data.items():
                    if getattr(exam_type, field) != value:
                        setattr(exam_type, field, value)
                        updated = True

                if updated:
                    exam_type.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Updated exam type: {exam_type.name} ({exam_type.code})'
                        )
                    )

        # Summary
        total_count = ExamType.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} created, {updated_count} updated, '
                f'{total_count} total exam types'
            )
        )

        # Validate weightage distribution
        total_weightage = sum(ExamType.objects.values_list('weightage', flat=True))
        if total_weightage > 100:
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Total weightage ({total_weightage}%) exceeds 100%'
                )
            )
        elif total_weightage < 100:
            self.stdout.write(
                self.style.WARNING(
                    f'Note: Total weightage ({total_weightage}%) is less than 100%. '
                    'This is normal if not all exam types are used together.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Total weightage: {total_weightage}% (perfect distribution)'
                )
            )

        self.stdout.write(
            self.style.SUCCESS('Exam types population completed successfully!')
        )
