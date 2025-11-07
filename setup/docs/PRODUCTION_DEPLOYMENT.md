# Production Deployment Guide

This guide covers deploying the School Management System to production with PostgreSQL.

## Prerequisites

- Ubuntu/Debian server or Docker environment
- PostgreSQL database server
- Redis server (for Channels)
- Domain name with SSL certificate
- SMTP email service

## 1. Server Setup

### Install Required System Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Redis
sudo apt install redis-server -y

# Install Nginx (web server)
sudo apt install nginx -y

# Install SSL certificate tools
sudo apt install certbot python3-certbot-nginx -y
```

### Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE school_db;
CREATE USER school_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE school_db TO school_user;
ALTER USER school_user CREATEDB;
\q
```

## 2. Application Deployment

### Clone and Setup Application

```bash
# Clone your repository
git clone https://github.com/your-repo/school-management.git
cd school-management

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install production requirements
pip install -r setup/requirements/production.txt

# Copy environment template
cp setup/.env.production.example .env

# Edit environment variables
nano .env
```

### Configure Environment Variables

Update `.env` with your production values:

```bash
DEBUG=False
SECRET_KEY=your-50-character-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://school_user:your_password@localhost:5432/school_db
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_HOST_USER=your-email@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password
REDIS_URL=redis://localhost:6379/0

# SSL/Security settings (configurable)
SECURE_SSL_REDIRECT=False  # Set to True when SSL is configured
SECURE_HSTS_SECONDS=0      # Set to 31536000 (1 year) when SSL is configured
```

**Important Notes:**
- `SECRET_KEY` should have no quotes
- `ALLOWED_HOSTS` should be comma-separated without spaces
- SSL settings are configurable for flexible deployment

### Run Production Setup Script

```bash
# Run the production setup script
python setup/setup_project_production.py

# Or run with options
python setup/setup_project_production.py --force  # Skip confirmations
```

## 3. Create Superuser

```bash
# Create superuser account
python manage.py createsuperuser

# Or use environment variables
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
export DJANGO_SUPERUSER_PASSWORD=your_secure_password
python manage.py createsuperuser --noinput
```

## 4. Setup Gunicorn (WSGI Server)

### Create Gunicorn Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/school.service
```

Add this content:

```ini
[Unit]
Description=School Management System
After=network.target

[Service]
User=your-user
Group=your-group
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/project/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/path/to/your/project/venv/bin/gunicorn --workers 3 --bind unix:/tmp/school.sock config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

### Start Gunicorn Service

```bash
# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl start school
sudo systemctl enable school

# Check status
sudo systemctl status school
```

## 5. Setup Daphne (ASGI Server for Channels)

### Create Daphne Service

```bash
sudo nano /etc/systemd/system/school-daphne.service
```

Add this content:

```ini
[Unit]
Description=School Management System Daphne
After=network.target

[Service]
User=your-user
Group=your-group
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/project/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/path/to/your/project/venv/bin/daphne -u /tmp/school-daphne.sock config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

### Start Daphne Service

```bash
sudo systemctl daemon-reload
sudo systemctl start school-daphne
sudo systemctl enable school-daphne
```

## 6. Setup Nginx

### Configure Nginx Site

```bash
# Create nginx site configuration
sudo nano /etc/nginx/sites-available/school
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /path/to/your/project/staticfiles/;
    }

    location /media/ {
        alias /path/to/your/project/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/school.sock;
    }

    # WebSocket support for Channels
    location /ws/ {
        proxy_pass http://unix:/tmp/school-daphne.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Enable Site and Restart Nginx

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/school /etc/nginx/sites-enabled

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

## 7. Setup SSL Certificate

```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test certificate renewal
sudo certbot renew --dry-run
```

## 8. Setup Redis

```bash
# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping
```

## 9. Final Checks

### Test Application

```bash
# Test Django application
python manage.py check --deploy

# Test database connection
python manage.py dbshell

# Test static files
python manage.py collectstatic --noinput
```

### Check Services Status

```bash
# Check all services
sudo systemctl status school
sudo systemctl status school-daphne
sudo systemctl status nginx
sudo systemctl status redis-server
sudo systemctl status postgresql
```

### Access Application

- Main application: https://yourdomain.com
- Admin panel: https://yourdomain.com/admin/

## 10. Monitoring and Maintenance

### Log Files

```bash
# Application logs
tail -f /path/to/your/project/logs/production.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# System logs
journalctl -u school -f
journalctl -u school-daphne -f
```

### Backup Strategy

```bash
# Database backup
pg_dump school_db > school_backup_$(date +%Y%m%d_%H%M%S).sql

# File backup
tar -czf school_files_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/your/project

# Automated backups (add to crontab)
crontab -e
# Add: 0 2 * * * pg_dump school_db > /backups/school_db_$(date +\%Y\%m\%d).sql
```

### Security Hardening

```bash
# Update system regularly
sudo apt update && sudo apt upgrade

# Configure firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Secure PostgreSQL (update pg_hba.conf)
sudo nano /etc/postgresql/12/main/pg_hba.conf
# Add: host school_db school_user 127.0.0.1/32 md5
sudo systemctl restart postgresql
```

## Troubleshooting

### Setup Script Issues

- **Environment variables not loading**: The production setup script automatically loads `.env` files using python-dotenv
- **SSL warnings**: `SECURE_SSL_REDIRECT` and `SECURE_HSTS_SECONDS` are configurable via environment variables
- **Cross-platform issues**: Setup scripts work on both Windows and Linux

### Common Issues

1. **502 Bad Gateway**: Check if Gunicorn/Daphne services are running
2. **500 Internal Server Error**: Check application logs
3. **Database connection failed**: Verify DATABASE_URL and PostgreSQL service
4. **Static files not loading**: Run `collectstatic` and check Nginx configuration
5. **Environment variable format**: Ensure `SECRET_KEY` has no quotes and `ALLOWED_HOSTS` is comma-separated

### Debug Commands

```bash
# Test production setup script
python setup/setup_project_production.py --dry-run

# Test Gunicorn directly
gunicorn --bind 0.0.0.0:8000 config.wsgi:application

# Test Daphne directly
daphne config.asgi:application

# Test database connection
python manage.py dbshell

# Check environment variables
python -c "import os; print(os.environ.get('DATABASE_URL'))"

# Run production checks
python manage.py check --deploy --settings=config.production
```

## Support

For deployment issues, check:
1. Application logs in `logs/production.log`
2. Nginx error logs in `/var/log/nginx/error.log`
3. System logs with `journalctl`
4. Django check command: `python manage.py check --deploy`
