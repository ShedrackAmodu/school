# School Management System - Setup Guide

## 🚀 Quick Setup After Database Deletion

If you've deleted your database (`db.sqlite3`) and need to restore your School Management System, use the automated setup script.

## 🏭 Production Deployment Setup

For production deployment, use the dedicated production setup script:

```bash
python setup/setup_project_production.py
```

This script provides:
- ✅ Production-ready environment validation
- ✅ Automatic `.env` file loading
- ✅ Database backup creation
- ✅ Security checks and hardening
- ✅ Comprehensive deployment validation

**Options:**
- `--dry-run`: Test setup without making changes
- `--force`: Skip confirmations
- `--skip-backup`: Skip database backup creation

## 📋 Prerequisites

1. **Python Virtual Environment**: Make sure your virtual environment is activated
2. **Dependencies**: Install all required packages:
   ```bash
   pip install -r setup/requirements/base.txt
   ```
3. **Environment Variables**: Ensure your `.env` file is configured (if using one)

## 🛠️ Automated Setup

Run the setup script from your project root:

```bash
python setup/setup_project.py
```

## 📝 What the Setup Script Does

The setup script automatically performs these steps:

### 1. **Requirements Check**
- ✅ Verifies virtual environment is activated
- ✅ Checks Django installation
- ✅ Validates psutil availability

### 2. **Database Setup**
- ✅ Runs all Django migrations
- ✅ Creates database cache table

### 3. **Initial Data Creation**
- ✅ **System Performance KPIs**: Creates 10 system monitoring metrics
  - CPU Usage, Memory Usage, Disk Usage
  - Database Connections, Response Time, Error Rate
  - Active Sessions, Query Performance, Uptime, Backup Status
- ✅ **System Report Types**: Creates capacity planning reports
  - System Performance Report
  - Capacity Planning Report
  - System Health Check
- ✅ **Legal Documents**: Populates support app with legal pages

### 4. **Static Files** (Optional)
- ⚠️ Attempts to collect static files (may skip if STATIC_ROOT not configured)

### 5. **Superuser Creation**
- 🔐 Interactive superuser account creation
- 📧 Prompts for username, email, and password

### 6. **System Metrics Collection**
- 📊 Collects initial system performance data
- 🔄 Populates KPI measurements with current values

### 7. **System Validation**
- ✅ Runs Django system checks for deployment readiness

## 🎯 Manual Setup Commands

If you prefer to run commands individually:

```bash
# 1. Run migrations
python manage.py migrate
python manage.py createcachetable

# 2. Create initial data
python manage.py create_system_kpis
python manage.py create_system_reports
python manage.py populate_legal_documents

# 3. Collect static files (if STATIC_ROOT configured)
python manage.py collectstatic --noinput

# 4. Create superuser
python manage.py createsuperuser

# 5. Collect initial metrics
python manage.py collect_system_metrics

# 6. Run checks
python manage.py check --deploy
```

## 📊 System Performance Analytics Features

After setup, your system includes:

### **Real-time Monitoring**
- CPU, Memory, Disk usage tracking
- Database connection monitoring
- Application response time metrics
- Error rate analysis

### **Analytics Dashboard**
- Super admin system performance widgets
- Trend analysis and change indicators
- "Collect Now" button for immediate updates
- Role-based dashboard views

### **Capacity Planning**
- Automated report generation
- System health monitoring
- Performance trend analysis
- Data export capabilities

## 🚀 Post-Setup Steps

1. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```

2. **Access Admin Panel**:
   - URL: `http://localhost:8000/admin/`
   - Login with superuser credentials

3. **Access Analytics Dashboard**:
   - URL: `http://localhost:8000/analytics/`
   - View system performance metrics

## 🔧 Useful Management Commands

```bash
# Collect fresh system metrics
python manage.py collect_system_metrics

# Create database backup
python manage.py dumpdata > backup.json

# Restore from backup
python manage.py loaddata backup.json

# Run system checks
python manage.py check --deploy
```

## ⚠️ Troubleshooting

### Static Files Issues
If static files collection fails:
1. Configure `STATIC_ROOT` in your Django settings
2. Run: `python manage.py collectstatic --noinput`

### Database Issues
If migrations fail:
1. Delete `db.sqlite3` file
2. Run: `python manage.py migrate --run-syncdb`

### Permission Issues
If superuser creation fails:
1. Run: `python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'password')"`

## 📞 Support

For issues with the setup script, check:
1. Virtual environment is activated
2. All dependencies are installed
3. You're running from project root directory
4. Database file permissions (if applicable)

---

**🎓 Your School Management System is now ready with full System Performance Analytics!**
