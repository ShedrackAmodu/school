from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.support.models import FAQ, Category


class Command(BaseCommand):
    help = 'Populate the database with initial FAQs for the support system'

    def handle(self, *args, **options):
        # Ensure categories exist first
        self.create_categories()

        # Define the FAQ data organized by category
        faqs_data = [
            # Account & Login
            {
                'question': 'How do I reset my password?',
                'answer': '''
To reset your password:

1. Go to the login page and click "Forgot Password?"
2. Enter your email address
3. Check your email for a password reset link
4. Follow the link to create a new password

If you don't receive the email, please contact support or check your spam folder.
                ''',
                'category_slug': 'account-login',
                'order': 1
            },
            {
                'question': 'How do I change my profile information?',
                'answer': '''
To update your profile:

1. Log in to your account
2. Go to your profile/dashboard
3. Click on "Edit Profile" or "Account Settings"
4. Update your information as needed
5. Save your changes

For students, some information may be managed by school administrators.
                ''',
                'category_slug': 'account-login',
                'order': 2
            },
            {
                'question': 'Why can\'t I log in to my account?',
                'answer': '''
Common login issues and solutions:

**Wrong credentials**: Double-check your username/email and password (note: passwords are case-sensitive)

**Account locked**: After several failed attempts, accounts may be temporarily locked. Wait 15 minutes or contact support.

**Browser issues**: Clear your browser cache/cookies or try a different browser.

**System maintenance**: The system may be down for maintenance. Check the school website for announcements.

If none of these work, please contact support with your username/email address.
                ''',
                'category_slug': 'account-login',
                'order': 3
            },

            # Academic Information
            {
                'question': 'How can I view my grades and academic records?',
                'answer': '''
To view your academic information:

1. Log in to your student portal
2. Navigate to "Academics" or "Grades" section
3. Select the academic year/term you want to view
4. Click on individual subjects for detailed grade breakdowns

Parents can view their children's academic records through the parent portal by selecting their student first.
                ''',
                'category_slug': 'academic-records',
                'order': 1
            },
            {
                'question': 'How do I register for classes?',
                'answer': '''
Course registration process:

1. Log in during the registration period announced by your school
2. Go to "Academics" > "Course Registration"
3. Browse available courses by subject/department
4. Select your preferred courses (respecting prerequisites and schedule conflicts)
5. Submit your registration for approval

Check with your academic advisor for course recommendations.
                ''',
                'category_slug': 'academic-records',
                'order': 2
            },
            {
                'question': 'What is my class schedule and how can I view it?',
                'answer': '''
To view your class schedule:

1. Log in to your student portal
2. Go to "Schedule" or "Timetable"
3. Select the current term/academic year
4. Your schedule will show class times, locations, and instructors

You can also download or print your schedule for reference. Schedule changes will be reflected here automatically.
                ''',
                'category_slug': 'academic-records',
                'order': 3
            },
            {
                'question': 'How do I check my attendance records?',
                'answer': '''
To view attendance information:

1. Log in to your student portal
2. Navigate to "Attendance" section
3. Select the period you want to review (daily, weekly, monthly)
4. View detailed attendance records by subject

Parents can monitor their children's attendance through the parent portal. Contact your teachers or academic office if you notice any discrepancies.
                ''',
                'category_slug': 'academic-records',
                'order': 4
            },

            # Fees & Payments
            {
                'question': 'How can I view my fee statement and payment history?',
                'answer': '''
To access your financial information:

1. Log in to your account
2. Go to "Finance" or "Fees & Payments"
3. Select "Fee Statement" to see outstanding balances
4. Choose "Payment History" to view past transactions

All fees, payments, discounts, and outstanding balances are displayed here.
                ''',
                'category_slug': 'fees-payments',
                'order': 1
            },
            {
                'question': 'What payment methods are accepted?',
                'answer': '''
We accept the following payment methods:

**Online Payments**:
- Credit/Debit cards (Visa, MasterCard, American Express)
- Bank transfers
- Mobile money (M-Pesa, Airtel Money, etc.)
- Online banking

**Offline Payments**:
- Cash payments at school bursar's office
- Bank deposits (provide reference number when submitting proof)
- Cheques

All payments should include your student ID or reference number.
                ''',
                'category_slug': 'fees-payments',
                'order': 2
            },
            {
                'question': 'How do I pay school fees online?',
                'answer': '''
Online payment process:

1. Log in to your account
2. Go to "Finance" > "Make Payment"
3. Select the fee type and amount
4. Choose your payment method
5. Review and confirm payment details
6. Complete the transaction

You'll receive a payment confirmation and receipt via email. Processing time is usually instant for cards and 1-2 business days for bank transfers.
                ''',
                'category_slug': 'fees-payments',
                'order': 3
            },
            {
                'question': 'What if I have a payment dispute or need a refund?',
                'answer': '''
For payment issues:

1. Contact the bursar's office with your payment reference
2. Provide supporting documentation
3. Submit a formal request through the system or email

Refunds are processed within 14-21 business days after approval. All refund requests are reviewed by the finance department.
                ''',
                'category_slug': 'fees-payments',
                'order': 4
            },

            # System Usage
            {
                'question': 'How do I update my contact information?',
                'answer': '''
To update your contact details:

1. Log in to your account
2. Go to "Profile" or "Account Settings"
3. Select "Contact Information"
4. Update phone number, email, or address as needed
5. Save changes

Important contact updates (like emergency contacts) may require verification. Always keep your information current for important school communications.
                ''',
                'category_slug': 'system-usage',
                'order': 1
            },
            {
                'question': 'How do I download documents like transcripts or certificates?',
                'answer': '''
To download official documents:

1. Log in to your account
2. Go to "Documents" or "Downloads" section
3. Select the document type you need (transcript, certificate, etc.)
4. Choose the academic year/period
5. Click "Generate" or "Download"

Some documents may require approval before they become available for download.
                ''',
                'category_slug': 'system-usage',
                'order': 2
            },
            {
                'question': 'How do I report a technical issue with the system?',
                'answer': '''
To report a technical problem:

1. Contact support through the "Support" section
2. Select "Technical Issue" as the category
3. Provide detailed description including:
   - What you were trying to do
   - Error messages received
   - Browser and device information
   - Steps to reproduce the issue

Include screenshots if possible. Our technical team will respond within 24 hours.
                ''',
                'category_slug': 'system-usage',
                'order': 3
            },

            # Support & Communication
            {
                'question': 'How do I contact my teachers or academic advisors?',
                'answer': '''
Communication methods:

**Through the System**:
1. Log in to your account
2. Go to "Messages" or "Communication"
3. Select your teacher/advisor from the directory
4. Send your message

**Direct Contact**: Use email addresses or phone numbers provided by your school.

**Office Hours**: Visit teachers during their posted office hours for in-person discussions.
                ''',
                'category_slug': 'support-communication',
                'order': 1
            },
            {
                'question': 'Who do I contact for different types of support?',
                'answer': '''
Support contacts by category:

**Academic Issues**: Academic advisor or department head
**Technical Problems**: IT Support (available 24/7 for critical issues)
**Financial Concerns**: Bursar's office
**Medical/Health Issues**: School nurse or health services
**Disciplinary Matters**: Student affairs office
**General Support**: Student services or reception

Use the support ticketing system for faster, tracked assistance.
                ''',
                'category_slug': 'support-communication',
                'order': 2
            }
        ]

        created_count = 0
        updated_count = 0

        for faq_data in faqs_data:
            # Get or create category
            category_slug = faq_data['category_slug']
            try:
                category = Category.objects.get(slug=category_slug)
            except Category.DoesNotExist:
                # Skip if category doesn't exist (shouldn't happen with our create_categories call)
                self.stdout.write(
                    self.style.WARNING(f'Category {category_slug} not found, skipping FAQ: {faq_data["question"][:50]}...')
                )
                continue

            # Check if FAQ already exists
            existing_faq = FAQ.objects.filter(
                question__iexact=faq_data['question'],
                category=category
            ).first()

            if existing_faq:
                # Update content if needed
                if existing_faq.answer.strip() != faq_data['answer'].strip():
                    existing_faq.answer = faq_data['answer'].strip()
                    existing_faq.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated FAQ: {faq_data["question"][:50]}...')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'FAQ already exists: {faq_data["question"][:50]}...')
                    )
            else:
                # Create new FAQ
                FAQ.objects.create(
                    question=faq_data['question'],
                    answer=faq_data['answer'].strip(),
                    category=category,
                    order=faq_data['order'],
                    is_published=True
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created FAQ: {faq_data["question"][:50]}...')
                )

        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} and updated {updated_count} FAQs.')
            )
            self.stdout.write(
                self.style.SUCCESS('You can now view the FAQs at /support/faq/')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All FAQs already exist and are up to date.')
            )

    def create_categories(self):
        """Create the necessary categories for FAQs."""
        categories_data = [
            {'name': 'Account & Login', 'slug': 'account-login', 'description': 'Questions about user accounts, login, and authentication'},
            {'name': 'Academic Records', 'slug': 'academic-records', 'description': 'Questions about grades, courses, and academic information'},
            {'name': 'Fees & Payments', 'slug': 'fees-payments', 'description': 'Questions about school fees, payments, and financial matters'},
            {'name': 'System Usage', 'slug': 'system-usage', 'description': 'Questions about using the school management system'},
            {'name': 'Support & Communication', 'slug': 'support-communication', 'description': 'Questions about getting help and contacting school staff'},
        ]

        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {cat_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {cat_data["name"]}')
                )
