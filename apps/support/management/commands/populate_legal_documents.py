from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.support.models import LegalDocument


class Command(BaseCommand):
    help = 'Populate the database with initial legal documents for the support app'

    def handle(self, *args, **options):
        # Define the legal document data
        documents_data = [
            {
                'document_type': 'privacy_policy',
                'title': 'Privacy Policy',
                'slug': 'privacy-policy',
                'content': '''
# Privacy Policy

## Introduction
This Privacy Policy describes how we collect, use, and protect your personal information when you use our school management system.

## Information We Collect
We may collect the following types of information:
- Personal identification information (name, email, phone number)
- Academic records and performance data
- Attendance records
- Financial information (fees, payments)
- Communication logs

## How We Use Your Information
We use collected information to:
- Manage student enrollment and academic records
- Process payments and financial transactions
- Communicate important school information
- Ensure safety and security on campus
- Comply with legal and regulatory requirements

## Data Security
We implement appropriate technical and organizational measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction.

## Contact Us
If you have any questions about this Privacy Policy, please contact us through the support system.

---
*This is placeholder content. Please replace with your actual privacy policy content.*
                '''
            },
            {
                'document_type': 'terms_of_service',
                'title': 'Terms of Service',
                'slug': 'terms-of-service',
                'content': '''
# Terms of Service

## Acceptance of Terms
By accessing and using our school management system, you accept and agree to be bound by these Terms of Service.

## User Accounts
Users are responsible for maintaining the confidentiality of their account credentials and for all activities that occur under their account.

## Acceptable Use
You agree to use the system only for lawful purposes and in accordance with these terms:
- Respect academic integrity
- Protect student privacy
- Follow school policies and procedures
- Report any security concerns

## Prohibited Activities
You may not:
- Attempt to gain unauthorized access
- Share account credentials
- Upload malicious content
- Violate intellectual property rights
- Disrupt system operations

## Limitation of Liability
The system is provided "as is" without warranties. We shall not be liable for any damages arising from system use.

---
*This is placeholder content. Please replace with your actual terms of service.*
                '''
            },
            {
                'document_type': 'data_protection',
                'title': 'Data Protection Policy',
                'slug': 'data-protection',
                'content': '''
# Data Protection Policy

## Purpose
This policy outlines our commitment to protecting personal data and complying with data protection regulations.

## Data Controller
Our school acts as the data controller for all personal data processed within the system.

## Legal Basis for Processing
We process personal data based on:
- Consent from data subjects
- Legitimate interests of the school
- Legal obligations (education regulations)
- Contractual necessities

## Data Subject Rights
You have the right to:
- Access your personal data
- Rectify inaccurate data
- Erase your data (where applicable)
- Restrict or object to processing
- Data portability

## Data Retention
Personal data is retained only as long as necessary for the purposes outlined in this policy or as required by law.

## Security Measures
We implement comprehensive security controls including:
- Encryption of sensitive data
- Access controls and authentication
- Regular security audits
- Incident response procedures

## Data Breach Procedures
In the event of a data breach, we will:
- Assess the risk to affected individuals
- Notify required authorities within 72 hours
- Inform affected data subjects without undue delay

---
*This is placeholder content. Please replace with your actual data protection policy.*
                '''
            },
            {
                'document_type': 'cookie_policy',
                'title': 'Cookie Policy',
                'slug': 'cookie-policy',
                'content': '''
# Cookie Policy

## What Are Cookies
Cookies are small text files that are placed on your device when you visit our website to enhance your browsing experience.

## How We Use Cookies
Our school management system uses cookies for:
- User authentication and session management
- Remembering user preferences
- Analytics and performance monitoring
- Security purposes

## Types of Cookies We Use

### Essential Cookies
Required for the system to function properly:
- Session cookies
- Authentication tokens
- Security cookies

### Performance Cookies
Help us understand how users interact with the system:
- Google Analytics (if implemented)
- Performance monitoring tools

### Functional Cookies
Enhance user experience:
- Language preferences
- Theme settings
- Form data preservation

## Managing Cookies
Most web browsers allow you to control cookies through their settings. You can:
- Block all cookies
- Delete existing cookies
- Receive notifications about new cookies

## Third-Party Cookies
We may use third-party services that set their own cookies:
- Payment processors
- Analytics services
- Content delivery networks

## Updates to This Policy
We may update this Cookie Policy periodically to reflect changes in our practices or for legal compliance.

---
*This is placeholder content. Please replace with your actual cookie policy.*
                '''
            },
            {
                'document_type': 'accessibility_statement',
                'title': 'Accessibility Statement',
                'slug': 'accessibility-statement',
                'content': '''
# Accessibility Statement

## Our Commitment
We are committed to ensuring our school management system is accessible to all users, including those with disabilities, in accordance with accessibility standards and guidelines.

## Accessibility Standards
Our system aims to comply with:
- Web Content Accessibility Guidelines (WCAG) 2.1 Level AA
- Section 508 of the Rehabilitation Act
- European Accessibility Act requirements

## Accessibility Features
Our platform includes:
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode options
- Adjustable text sizes
- Alternative text for images

## Assistive Technologies Support
We support commonly used assistive technologies including:
- Screen readers (NVDA, JAWS, VoiceOver)
- Magnification software
- Voice control systems
- Alternative input devices

## Known Limitations
While we strive for full accessibility, some legacy features may have limitations. We are actively working to improve accessibility across all functions.

## Feedback
If you encounter accessibility barriers, please contact our support team. We welcome feedback on how we can improve accessibility.

## Contact Information
For accessibility-related questions or issues:
- Email: [accessibility contact email]
- Support portal: [support system URL]

## Regular Audits
We conduct regular accessibility audits and usability testing with users who have disabilities to ensure ongoing compliance.

---
*This is placeholder content. Please replace with your actual accessibility statement.*
                '''
            }
        ]

        created_count = 0
        updated_count = 0

        for doc_data in documents_data:
            document_type = doc_data['document_type']

            # Check if document already exists
            existing_doc = LegalDocument.objects.filter(document_type=document_type).first()

            if existing_doc:
                # Update if inactive
                if not existing_doc.is_active:
                    existing_doc.is_active = True
                    existing_doc.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Activated existing {document_type} document')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'{document_type} document already exists and is active')
                    )
            else:
                # Create new document
                LegalDocument.objects.create(
                    title=doc_data['title'],
                    slug=doc_data['slug'],
                    content=doc_data['content'].strip(),
                    document_type=document_type,
                    is_active=True
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created {document_type} document')
                )

        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} and updated {updated_count} legal documents.')
            )
            self.stdout.write(
                self.style.SUCCESS('You can now access legal document URLs like /support/privacy-policy/')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All legal documents already exist and are active.')
            )
