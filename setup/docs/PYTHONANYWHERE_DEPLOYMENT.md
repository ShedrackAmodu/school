# PythonAnywhere Deployment Guide - nordalms Account

Complete deployment guide for School Management System on PythonAnywhere.

## 📋 Prerequisites

- PythonAnywhere account: `nordalms` (password: `shedrack.1995`)
- Domain: `nordalms.pythonanywhere.com`
- GitHub repository with your code

## 🗄️ Step 1: Create PostgreSQL Database

1. **Login to PythonAnywhere**: https://www.pythonanywhere.com/
   - Username: `nordalms`
   - Password: `shedrack.1995`

2. **Go to Databases Tab**:
   - Click **"Databases"** in the top menu

3. **Create PostgreSQL Database**:
   - Scroll to **"PostgreSQL"** section
   - Click **"Create a database"**
   - Database name: `nordalms$school_db` (or similar)
   - Click **"Create"**

4. **Note Database Details**:
   After creation, you'll see:
   ```
   Host: nordalms-XXXX.postgres.pythonanywhere-services.com
   Database: nordalms$school_db
   Username: nordalms
   Password: [generated-password]
   ```
   **Save these details - you'll need them!**

## 📁 Step 2: Upload Code to PythonAnywhere

### Option A: Upload via Git (Recommended)

1. **Open Bash Console**:
   - Go to **"Consoles"** tab
   - Click **"Bash"** to open a console

2. **Clone Your Repository**:
   ```bash
   git clone https://github.com/your-username/school-management.git
   cd school-management
   ```

### Option B: Upload Files Manually

1. **Go to Files Tab**:
   - Click **"Files"** in the top menu

2. **Upload Files**:
   - Click **"Upload a file"**
   - Upload your entire project folder
   - Or use **"Open bash console here"** and upload via scp/rsync

## 📦 Step 3: Install Requirements

### Option A: Automated Setup (Recommended)

1. **Run the automated setup script**:
   ```bash
   python setup/pythonanywhere_setup.py
   ```

   This script will automatically:
   - Create and activate a virtual environment
   - Install all production requirements
   - Run database migrations
   - Collect static files

### Option B: Manual Setup

1. **Open Bash Console** in your project directory**

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Requirements**:
   ```bash
   pip install -r setup/requirements/production.txt
   ```

## ⚙️ Step 4: Configure Environment Variables

1. **Create .env file**:
   ```bash
   nano .env
   ```

2. **Add production settings**:
   ```bash
   DEBUG=False
   SECRET_KEY=your-50-character-secret-key-here-make-it-very-long-and-random
   ALLOWED_HOSTS=nordalms.pythonanywhere.com

   # Database connection (use your actual database details)
   DATABASE_URL=postgresql://nordalms:[password]@nordalms-XXXX.postgres.pythonanywhere-services.com/nordalms$school_db

   # Email settings (configure as needed)
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   ```

## 🏗️ Step 5: Setup WSGI Configuration

1. **Copy WSGI file**:
   ```bash
   cp setup/pythonanywhere_wsgi.py /home/nordalms/pythonanywhere_wsgi.py
   ```

2. **Configure project path** (optional):
   - The WSGI file automatically detects the project path
   - If needed, you can set the `PROJECT_HOME` environment variable:
   ```bash
   export PROJECT_HOME=/home/nordalms/school-management
   ```

## 🌐 Step 6: Create Web Application

1. **Go to Web Tab**:
   - Click **"Web"** in the top menu

2. **Add New Web App**:
   - Click **"Add a new web app"**
   - Choose **"Manual configuration"**
   - Select **Python 3.10** (or latest available)
   - Choose **"Django"**

3. **Configure Web App**:
   - **Python version**: 3.10
   - **Source code**: `/home/nordalms/school-management`
   - **Working directory**: `/home/nordalms/school-management`
   - **WSGI configuration file**: `/home/nordalms/pythonanywhere_wsgi.py`
   - **Virtualenv**: `/home/nordalms/school-management/venv`

4. **Static Files Configuration**:
   - URL: `/static/`
   - Directory: `/home/nordalms/school-management/staticfiles`

## 🗃️ Step 7: Run Database Migrations

1. **Open Bash Console** in project directory

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Collect static files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

## 👤 Step 8: Create Superuser

1. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```
   Or use environment variables:
   ```bash
   export DJANGO_SUPERUSER_USERNAME=admin
   export DJANGO_SUPERUSER_EMAIL=admin@nordalms.pythonanywhere.com
   export DJANGO_SUPERUSER_PASSWORD=your_secure_password
   python manage.py createsuperuser --noinput
   ```

## 🔄 Step 9: Reload Web Application

1. **Go back to Web Tab**

2. **Reload the web app**:
   - Click the **green reload button** next to your web app

3. **Check the site**:
   - Visit: https://nordalms.pythonanywhere.com
   - Admin: https://nordalms.pythonanywhere.com/admin/

## 🔧 Troubleshooting

### Automated Setup Issues
- The `pythonanywhere_setup.py` script is cross-platform compatible
- If running on non-PythonAnywhere systems, use `--dry-run` flag for testing
- Check that all dependencies are installed before running setup

### Environment Variable Issues
- Ensure `SECRET_KEY` has no quotes in the `.env` file
- `ALLOWED_HOSTS` should be comma-separated without spaces
- The production setup script automatically loads `.env` file

### Database Connection Issues
- Double-check your `DATABASE_URL` in `.env`
- Make sure PostgreSQL database is created and running
- Check database credentials in PythonAnywhere Databases tab

### Import Errors
- Ensure all requirements are installed: `pip install -r setup/requirements/production.txt`
- Check that virtual environment is activated
- Verify WSGI file paths are correct (automatically configured)

### Static Files Not Loading
- Run: `python manage.py collectstatic --noinput`
- Check static files configuration in Web tab
- Ensure STATIC_ROOT is set in production settings

### 500 Internal Server Error
- Check error logs in Web tab → "Error log"
- Verify Django settings are correct
- Check WSGI configuration (PROJECT_HOME is auto-detected)

### Migration Issues
- Ensure database is accessible
- Check database permissions
- Try: `python manage.py migrate --run-syncdb` if needed

### SSL/Security Configuration
- SSL redirect is configurable via `SECURE_SSL_REDIRECT` environment variable
- HSTS settings are configurable via `SECURE_HSTS_SECONDS` environment variable
- Set to `False`/`0` respectively for initial deployment without SSL

## 📊 Monitoring

### View Logs
- **Web Tab** → "Error log" for application errors
- **Web Tab** → "Server log" for server issues
- **Consoles Tab** → Bash console for manual debugging

### Performance
- PythonAnywhere provides basic monitoring
- Check "CPU" and "Memory" usage in dashboard
- Upgrade plan if needed for more resources

## 🔒 Security Notes

- Change default passwords immediately
- Use strong SECRET_KEY (50+ characters)
- Keep DEBUG=False in production
- Regularly update requirements
- Monitor logs for suspicious activity

## 🎉 Success Checklist

- [ ] PostgreSQL database created
- [ ] Code uploaded to PythonAnywhere
- [ ] Virtual environment created and activated
- [ ] Requirements installed
- [ ] Environment variables configured
- [ ] WSGI file configured
- [ ] Web app created in PythonAnywhere
- [ ] Database migrations run
- [ ] Static files collected
- [ ] Superuser created
- [ ] Web app reloaded
- [ ] Site accessible at https://nordalms.pythonanywhere.com

## 📞 Support

If you encounter issues:
1. Check the error logs in PythonAnywhere Web tab
2. Verify all steps in this guide
3. Test locally first with `python manage.py runserver`
4. Contact PythonAnywhere support if needed

**Your application should now be live at: https://nordalms.pythonanywhere.com**
