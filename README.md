# 🏫 Excellent Academy - School Management System

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2+-092009?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Redis-5.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>A comprehensive School Management System for Excellent Academy</strong><br>
  Manage academics, finance, attendance, and more with ease
</p>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [👥 User Roles](#-user-roles)
- [🛠️ Technology Stack](#️-technology-stack)
- [📦 Module Overview](#-module-overview)
- [🚀 Getting Started](#-getting-started)
- [⚙️ Configuration](#️-configuration)
- [📱 API Documentation](#-api-documentation)
- [💳 Payment Integration](#-payment-integration)
- [📱 SMS Integration](#-sms-integration)
- [📸 Screenshots](#-screenshots)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Features

### 🔐 Single-Tenant Architecture
- **Excellent Academy Focus**: Dedicated system for Excellent Academy
- **Data Security**: Secure data storage and user authentication
- **Scalable Design**: Built to handle growing student and staff base
- **Simplified Administration**: No multi-institution complexity

### 👑 Administrator
- System-wide configuration management
- Dashboard and analytics
- User role hierarchy management
- Global audit logging and compliance
- Staff and student management

### 🏫 School Administration
- **Staff Management**: Complete recruitment workflow from application to employee ID
- **Student Enrollment**: Online applications, approval workflow, student profiles
- **Financial Management**: Fee structures, invoicing, payment tracking
- **Academic Setup**: Classes, subjects, sections, academic sessions
- **Reporting**: Comprehensive analytics and reporting dashboards

### 📚 Academics
- Class and section management
- Subject and teacher assignment
- Timetable generation and management
- Academic session and term configuration
- Department management

### 📝 Assessment & Grading
- Customizable grading systems
- Assignment and exam management
- Mark entry with validation
- Automated grade calculation
- **Report Card Generation** with PDF export
- Student performance analytics

### ✅ Attendance
- Daily attendance tracking
- Period-wise attendance
- Automated attendance summaries
- Late arrival tracking
- Attendance reports and analytics

### 💰 Finance
- **Fee Structure Management**: Create flexible fee structures per class/level
- **Invoice Generation**: Automatic and manual invoice creation
- **Payment Processing**: Online payments via Paystack
- **Payment Tracking**: Payment history, receipts generation
- **Fee Waivers and Discounts**: Flexible discount management
- **Financial Reports**: Revenue, outstanding payments, collections

### 📖 Library Management
- Book catalog management
- ISBN-based book entries
- Book copy tracking
- Circulation management (borrow/return)
- Member management
- Overdue tracking and fines
- Reservation system

### 🚌 Transport Management
- Fleet management (vehicles, drivers)
- Route planning with multiple stops
- Student transport allocation
- Vehicle maintenance tracking
- Transport fee integration

### 🏠 Hostel Management
- Hostel and room management
- Bed allocation system
- Student hostel assignments
- Maintenance request tracking
- Room inventory management

### 📱 Communication
- **SMS Notifications** via Termii (Nigerian provider)
- Email notifications
- In-app notifications
- Bulk messaging capabilities
- Parent-student communication
- Announcement system

### 📊 Analytics & Reporting
- Academic performance dashboards
- Attendance analytics
- Financial reports
- Student enrollment trends
- RESTful API for data export

###  Extracurricular Activities
- Activity creation and scheduling
- Student enrollment management
- Coach assignment
- Activity capacity management
- Performance tracking

### 🏥 Health Management
- Student health records
- Medical history tracking
- Vaccination records
- Health alerts and notifications

### 🛟 Support System
- Help desk ticketing system
- Knowledge base articles
- FAQ management
- User support workflows

### 🔒 Security & Audit
- Comprehensive audit logging
- User activity tracking
- Login history
- Permission-based access control
- Session management

---

## 🏗️ Architecture

```
Excellent Academy SMS/
├── apps/                    # Django applications
│   ├── academics/          # Academic management
│   ├── activities/         # Extracurricular activities
│   ├── analytics/         # Reporting & analytics
│   ├── assessment/        # Exams, grades, report cards
│   ├── attendance/        # Attendance tracking
│   ├── audit/             # Audit logging
│   ├── communication/     # SMS, email, notifications
│   ├── core/             # Core models, system configuration
│   ├── finance/          # Fees, payments, invoicing
│   ├── health/           # Health records
│   ├── hostels/          # Hostel management
│   ├── library/          # Library management
│   ├── support/          # Help desk
│   ├── transport/        # Transport management
│   └── users/            # Authentication, roles
├── config/               # Django project settings
├── templates/            # HTML templates
├── static/              # CSS, JS, images
└── setup/               # Project setup scripts
```

### Database Schema Highlights
- **Single Tenant**: All data belongs to Excellent Academy
- **UUID Primary Keys**: All models use UUID for global uniqueness
- **Soft Deletes**: All core models support soft delete functionality
- **Timestamp Tracking**: Created/updated/status change timestamps
- **Audit Trail**: Comprehensive logging of all data changes

---

## 👥 User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| 🦸 **Super Administrator** | System-wide admin | Full system access |
| 👨‍💼 **Administrator** | School admin | Full school management |
| 🎓 **Principal** | School head | Academic oversight, reporting |
| 👨‍🏫 **Teacher** | Teaching staff | Classes, attendance, grades |
| 🎒 **Student** | Student users | Own records, grades, schedule |
| 👨‍👩‍👧 **Parent** | Guardian | Child monitoring, payments |
| 💼 **Accountant** | Finance staff | Financial management |
| 📚 **Librarian** | Library staff | Library operations |
| 🚌 **Transport Manager** | Transport admin | Fleet and routes |
| 🏠 **Hostel Warden** | Hostel admin | Hostel management |
| 🛟 **Support Staff** | Help desk | Support tickets |
| 🚗 **Driver** | Transport driver | Vehicle operations |

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 5.2+
- **Python**: 3.10+
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **ORM**: Django ORM with multi-tenancy support

### Frontend
- **Template Engine**: Django Templates
- **CSS Framework**: Bootstrap 5 with crispy-forms
- **JavaScript**: Vanilla JS + Django Channels

### Real-time
- **WebSockets**: Django Channels
- **Message Broker**: Redis (production)

### Integrations
- **Payments**: Paystack (Nigeria)
- **SMS**: Termii (Nigeria)
- **Email**: SMTP (Gmail, SendGrid, etc.)
- **PDF Generation**: WeasyPrint
- **Excel Export**: openpyxl

---

## 📦 Module Overview

### Core Modules

| Module | Purpose | Key Models |
|--------|---------|------------|
| `core` | Multi-institution, config | Institution, SystemConfig, SequenceGenerator |
| `users` | Authentication, roles | User, Role, UserProfile, UserRole |
| `academics` | Academic structure | Class, Section, Subject, Timetable |
| `attendance` | Attendance tracking | DailyAttendance, PeriodAttendance |
| `assessment` | Grades & assessments | Exam, Assignment, Result, ReportCard |

### Functional Modules

| Module | Purpose | Key Models |
|--------|---------|------------|
| `finance` | Fees & payments | FeeStructure, Invoice, Payment |
| `library` | Library operations | Book, BookCopy, BorrowRecord |
| `transport` | Transport management | Vehicle, Route, TransportAllocation |
| `hostels` | Hostel management | Hostel, Room, HostelAllocation |
| `health` | Health records | HealthRecord, Vaccination |
| `activities` | Extracurricular | Activity, ActivityEnrollment |
| `communication` | Notifications | Notification, SMSLog, EmailTemplate |
| `analytics` | Reporting | (Aggregated data views) |
| `audit` | Audit logging | AuditLog |
| `support` | Help desk | SupportTicket, HelpArticle |

---

## 🚀 Getting Started

### Prerequisites

```
Python 3.10+
PostgreSQL (production)
Redis (production)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ShedrackAmodu/NexusSMS.git
cd NexusSMS
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Setup**

Create a `.env` file in the `setup/` directory:

```bash
# Create setup directory if not exists
mkdir -p setup

# Create .env file
touch setup/.env
```

Edit `setup/.env` with your configuration (see Configuration section below)

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run development server**
```bash
python manage.py runserver
```

8. **Access the application**
```
http://127.0.0.1:8000/
```

### Additional Commands

```bash
# Load sample data (optional)
python manage.py loaddata sample_data.json

# Generate report cards
python manage.py generate_report_cards

# Create initial data
python manage.py setup_initial_data
```

---

## ⚙️ Configuration

### Environment Variables

Create `setup/.env` with the following variables:

```env
# ============================================
# DJANGO SETTINGS
# ============================================
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ============================================
# DATABASE (PostgreSQL - Production)
# ============================================
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=nexussms
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# ============================================
# EMAIL SETTINGS
# ============================================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=NexusSMS <noreply@nexussms.com>

# ============================================
# PAYSTACK PAYMENT GATEWAY
# ============================================
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxxx
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxx
PAYSTACK_PAYMENT_URL=https://api.paystack.co
PAYSTACK_TEST_MODE=True
PAYSTACK_CALLBACK_URL=/finance/payment/callback/
PAYSTACK_CANCEL_URL=/finance/payment/cancel/

# ============================================
# SMS SETTINGS (Termii)
# ============================================
TERMII_API_KEY=your-termii-api-key
TERMII_SENDER_ID=NEXUS
TERMII_BASE_URL=https://api.ng.termii.com
SMS_NOTIFY_PARENTS_ON_PAYMENT=True
SMS_NOTIFY_STUDENT_ON_REPORT=True

# ============================================
# REDIS (Production for Channels)
# ============================================
REDIS_URL=redis://localhost:6379/0
```

### Production Setup

For production deployment, update `config/production.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']

# Use PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nexussms',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Use Redis for channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

---

## 📱 API Documentation

### REST API Endpoints

The system includes RESTful APIs for integration:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/students/` | GET | Student analytics data |
| `/api/library/books/` | GET/POST | Book catalog |
| `/api/library/borrow/` | POST | Borrow book |
| `/api/attendance/records/` | GET | Attendance records |
| `/api/assessment/results/` | GET | Student results |

### Authentication

API endpoints use token-based authentication:

```bash
# Get token
curl -X POST /api/auth/token/ -d "username=user&password=pass"

# Use token
curl -H "Authorization: Token YOUR_TOKEN" /api/endpoint/
```

---

## 💳 Payment Integration

### Paystack Setup

1. Create a Paystack account at https://paystack.com
2. Get your API keys from the dashboard
3. Add keys to environment variables
4. Configure webhook URL in Paystack dashboard:
   ```
   https://yourdomain.com/finance/payment/webhook/
   ```

### Payment Flow

```
Student/Parent → View Invoice → Initiate Payment 
    → Paystack Checkout → Payment Verification 
    → Invoice Update → Confirmation Notification
```

---

## 📱 SMS Integration

### Termii Configuration

1. Register at https://termii.com
2. Get your API key from the dashboard
3. Configure sender ID (max 11 characters)
4. Add to environment variables

### SMS Features

- Payment confirmation notifications
- Report card availability alerts
- Attendance alerts
- Announcements
- Bulk messaging

---

## 📸 Screenshots

> Screenshots coming soon! This section will include:
> - Dashboard views for each role
> - Student enrollment flow
> - Fee payment process
> - Report card generation
> - Library management interface
> - Transport tracking
> - Analytics dashboards

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Coding Standards

- Follow PEP 8 style guide
- Use Django best practices
- Write tests for new features
- Update documentation

---

## 📄 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

```
MIT License

Copyright (c) 2024 NexusSMS

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- Django Community
- Bootstrap Team
- Paystack for payment integration
- Termii for SMS services
- All contributors and testers

---

<p align="center">
  <strong>🚀 Built with ❤️ using Django</strong><br>
  <a href="https://github.com/ShedrackAmodu/NexusSMS">GitHub Repository</a> • 
  <a href="#">Documentation</a> • 
  <a href="#">Support</a>
</p>

---

<!--
📝 Notes for developers:
- Add actual screenshots to static/images/ and update links
- Consider adding a CHANGELOG.md
- Add CONTRIBUTING.md guidelines
- Set up CI/CD with GitHub Actions
- Add more detailed API documentation
-->
