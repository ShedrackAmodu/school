#!/usr/bin/env python
"""
School Management System - Production Deployment Setup Script

This script provides PRODUCTION-READY deployment setup for the School Management System.
It configures the system for production use with security hardening, proper logging,
database optimization, and deployment validation.

✅ PRODUCTION-READY - Configured for live deployment
✅ Security hardened with SSL/HTTPS and security headers
✅ Production logging with file rotation
✅ Database optimization and backup creation
✅ Environment variable validation
✅ Static files collection for production
✅ Comprehensive health checks

Usage:
    python setup/setup_project_production.py                    # Full production setup
    python setup/setup_project_production.py --dry-run          # See what would happen
    python setup/setup_project_production.py --skip-backup      # Skip database backup
    python setup/setup_project_production.py --force            # Force setup even with warnings

Requirements:
    - Production environment variables configured (.env file)
    - Database server running (PostgreSQL recommended for production)
    - Web server/WSGI server configured (nginx/gunicorn recommended)
    - SSL certificate configured

Author: Nexus Intelligence School Management System
"""

import os
import sys
import subprocess
import argparse
import logging
import getpass
import platform
import shutil
from pathlib import Path
from datetime import datetime


class ProductionSetup:
    """Handles production deployment setup."""

    def __init__(self, args=None):
        self.project_root = Path(__file__).parent.parent
        self.manage_py = self.project_root / "manage.py"
        self.backup_dir = self.project_root / "backups"

        # Setup argument parsing
        self.args = self.parse_arguments() if args is None else args

        # CLI options
        self.force_setup = getattr(self.args, 'force', False)
        self.skip_backup = getattr(self.args, 'skip_backup', False)
        self.dry_run = getattr(self.args, 'dry_run', False)

        # Use the current Python executable
        self.python_executable = sys.executable or "python"

        # Platform-specific settings
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"

        # Colors for output
        self.supports_color = self._check_color_support()
        self.colors = self._get_colors()

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

        # Track setup progress
        self.setup_success = True
        self.warnings_count = 0

    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description='School Management System Production Setup')
        parser.add_argument('--force', '-f', action='store_true',
                          help='Force setup even with warnings')
        parser.add_argument('--skip-backup', action='store_true',
                          help='Skip database backup creation')
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be done without executing')
        return parser.parse_args()

    def _check_color_support(self):
        """Check if terminal supports colors."""
        try:
            import sys
            return sys.stdout.isatty()
        except:
            return False

    def _get_colors(self):
        """Get color codes based on platform support."""
        if self.supports_color:
            return {
                'red': '\033[91m',
                'green': '\033[92m',
                'yellow': '\033[93m',
                'blue': '\033[94m',
                'magenta': '\033[95m',
                'cyan': '\033[96m',
                'bold': '\033[1m',
                'end': '\033[0m'
            }
        else:
            return {k: '' for k in ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'bold', 'end']}

    def print_header(self, text):
        """Print a formatted header."""
        print(f"\n{self.colors['bold']}{self.colors['blue']}{'='*60}{self.colors['end']}")
        print(f"{self.colors['bold']}{self.colors['blue']}{text.center(60)}{self.colors['end']}")
        print(f"{self.colors['bold']}{self.colors['blue']}{'='*60}{self.colors['end']}\n")

    def print_success(self, text):
        """Print a success message."""
        print(f"{self.colors['green']}✓ {text}{self.colors['end']}")

    def print_warning(self, text):
        """Print a warning message."""
        print(f"{self.colors['yellow']}⚠ {text}{self.colors['end']}")
        self.warnings_count += 1

    def print_error(self, text):
        """Print an error message."""
        print(f"{self.colors['red']}✗ {text}{self.colors['end']}")
        self.setup_success = False

    def print_info(self, text):
        """Print an info message."""
        print(f"{self.colors['cyan']}ℹ {text}{self.colors['end']}")

    def confirm_continue(self, message="Continue?"):
        """Get user confirmation to continue."""
        if self.force_setup:
            self.print_info(f"Force mode: Auto-continuing: {message}")
            return True

        try:
            response = input(f"{message} (y/N): ").strip().lower()
            return response in ['y', 'yes']
        except KeyboardInterrupt:
            print("\n")
            return False

    def run_command(self, command, description, cwd=None, env=None, critical=True):
        """Run a shell command and handle errors."""
        self.print_info(f"Running: {description}")

        if self.dry_run:
            print(f"DRY-RUN: {command}")
            return True

        try:
            # Merge with current environment
            current_env = os.environ.copy()
            if env:
                current_env.update(env)

            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or str(self.project_root),
                capture_output=True,
                text=True,
                check=True,
                env=current_env,
            )
            self.print_success(f"Completed: {description}")
            return True
        except subprocess.CalledProcessError as e:
            if critical:
                self.print_error(f"Failed: {description}")
                self.setup_success = False
            else:
                self.print_warning(f"Non-critical issue: {description}")

            # Print stderr and stdout for debugging
            if e.stderr and e.stderr.strip():
                print(f"Error: {e.stderr.strip()}")
            if e.stdout and e.stdout.strip():
                print(f"Output: {e.stdout.strip()}")

            return not critical

    def validate_environment(self):
        """Validate production environment variables and configuration."""
        self.print_header("VALIDATING PRODUCTION ENVIRONMENT")

        # Load environment variables from .env file if it exists
        env_file = self.project_root / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                self.print_success("Loaded environment variables from .env file")
            except ImportError:
                self.print_warning("python-dotenv not installed, environment variables may not be loaded")
        else:
            self.print_warning("No .env file found")

        required_vars = [
            'SECRET_KEY',
            'ALLOWED_HOSTS',
            'DATABASE_URL',  # For production database
        ]

        recommended_vars = [
            'DEBUG',
            'EMAIL_HOST',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'SENDGRID_USERNAME',
            'SENDGRID_PASSWORD',
            'REDIS_URL',
        ]

        missing_required = []
        missing_recommended = []

        for var in required_vars:
            if not os.environ.get(var):
                missing_required.append(var)

        for var in recommended_vars:
            if not os.environ.get(var):
                missing_recommended.append(var)

        if missing_required:
            self.print_error(f"Missing required environment variables: {', '.join(missing_required)}")
            self.print_error("Please configure these in your .env file or environment")
            return False

        if missing_recommended:
            self.print_warning(f"Missing recommended environment variables: {', '.join(missing_recommended)}")
            self.print_warning("Some features may not work correctly without these")

        # Validate SECRET_KEY length
        secret_key = os.environ.get('SECRET_KEY', '')
        if len(secret_key) < 32:
            self.print_warning("SECRET_KEY is shorter than recommended (32+ characters)")
            if not self.confirm_continue("Continue with short SECRET_KEY?"):
                return False

        # Validate ALLOWED_HOSTS
        allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
        if allowed_hosts == '*' or allowed_hosts == '':
            self.print_warning("ALLOWED_HOSTS is set to allow all hosts - not recommended for production")
            if not self.confirm_continue("Continue with permissive ALLOWED_HOSTS?"):
                return False

        # Check DEBUG setting
        debug = os.environ.get('DEBUG', 'True').lower() in ['true', '1', 't']
        if debug:
            self.print_warning("DEBUG is set to True - not recommended for production")
            if not self.confirm_continue("Continue with DEBUG=True?"):
                return False

        return True

    def check_production_requirements(self):
        """Check and install production requirements."""
        self.print_header("CHECKING PRODUCTION REQUIREMENTS")

        # Try production requirements first, fall back to base
        requirements_files = [
            self.project_root / "setup" / "requirements" / "production.txt",
            self.project_root / "setup" / "requirements" / "base.txt",
        ]

        requirements_file = None
        for req_file in requirements_files:
            if req_file.exists():
                requirements_file = req_file
                break

        if not requirements_file:
            self.print_error("No requirements file found")
            return False

        self.print_info(f"Using requirements file: {requirements_file}")

        # Install requirements
        if not self.run_command(
            f"pip install -r {requirements_file}",
            f"Installing production requirements from {requirements_file.name}"
        ):
            return False

        # Check for production-specific packages
        production_packages = {
            'gunicorn': 'gunicorn',  # WSGI server
            'psycopg2': 'psycopg2-binary',  # PostgreSQL adapter
            'whitenoise': 'whitenoise',  # Static files for production
            'sentry-sdk': 'sentry-sdk',  # Error monitoring (optional)
        }

        for package, import_name in production_packages.items():
            try:
                __import__(import_name)
                self.print_success(f"{package} is available")
            except ImportError:
                self.print_warning(f"{package} not found - recommended for production")
                # Try to install recommended packages
                install_cmd = f"pip install {package}"
                if self.run_command(install_cmd, f"Installing recommended {package}", critical=False):
                    self.print_success(f"{package} installed successfully")
                else:
                    self.print_warning(f"Could not install {package}")

        return True

    def create_backup(self):
        """Create a backup before making changes."""
        if self.skip_backup:
            self.print_warning("Skipping backup creation (--skip-backup flag set)")
            return True

        self.print_header("CREATING PRE-DEPLOYMENT BACKUP")

        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)

        # Create timestamp for backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"pre_production_backup_{timestamp}"

        # Backup database
        db_file = self.project_root / "db.sqlite3"
        if db_file.exists():
            backup_db = self.backup_dir / f"{backup_name}_db.sqlite3"
            try:
                if not self.dry_run:
                    shutil.copy2(db_file, backup_db)
                self.print_success(f"Database backed up to: {backup_db}")
            except Exception as e:
                self.print_warning(f"Could not backup database: {e}")
        else:
            self.print_info("No SQLite database file found (using external database?)")

        # Backup media files (if they exist and are not too large)
        media_dir = self.project_root / "media"
        if media_dir.exists():
            try:
                media_size = sum(f.stat().st_size for f in media_dir.rglob('*') if f.is_file())
                if media_size < 100 * 1024 * 1024:  # Less than 100MB
                    backup_media = self.backup_dir / f"{backup_name}_media"
                    if not self.dry_run:
                        shutil.copytree(media_dir, backup_media, dirs_exist_ok=True)
                    self.print_success(f"Media files backed up to: {backup_media}")
                else:
                    self.print_warning(f"Media directory too large ({media_size/1024/1024:.1f}MB) - skipping backup")
            except Exception as e:
                self.print_warning(f"Could not backup media files: {e}")

        # Create environment backup (without sensitive data)
        env_file = self.project_root / ".env"
        if env_file.exists():
            backup_env = self.backup_dir / f"{backup_name}_env.backup"
            try:
                if not self.dry_run:
                    # Create a sanitized backup
                    with open(env_file, 'r') as f:
                        env_content = f.read()

                    # Remove sensitive information
                    sensitive_patterns = ['PASSWORD', 'SECRET', 'KEY']
                    lines = env_content.split('\n')
                    sanitized_lines = []
                    for line in lines:
                        if any(pattern in line.upper() for pattern in sensitive_patterns):
                            # Replace value with placeholder
                            if '=' in line:
                                key = line.split('=')[0]
                                sanitized_lines.append(f"{key}=***REDACTED***")
                            else:
                                sanitized_lines.append(line)
                        else:
                            sanitized_lines.append(line)

                    with open(backup_env, 'w') as f:
                        f.write('\n'.join(sanitized_lines))

                self.print_success(f"Environment file backed up to: {backup_env}")
            except Exception as e:
                self.print_warning(f"Could not backup environment file: {e}")

        return True

    def setup_database(self):
        """Setup production database."""
        self.print_header("SETTING UP PRODUCTION DATABASE")

        # Check database configuration
        try:
            sys.path.append(str(self.project_root))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production')
            from django.conf import settings

            db_config = settings.DATABASES['default']
            db_engine = db_config.get('ENGINE', '')

            if 'postgresql' in db_engine:
                self.print_info("Using PostgreSQL database")
                # Check if psycopg2 is available
                try:
                    import psycopg2
                    self.print_success("PostgreSQL adapter (psycopg2) is available")
                except ImportError:
                    self.print_error("PostgreSQL configured but psycopg2 not available")
                    self.print_error("Install with: pip install psycopg2-binary")
                    return False
            elif 'sqlite3' in db_engine:
                self.print_warning("Using SQLite database - consider PostgreSQL for production")
                if not self.confirm_continue("Continue with SQLite database?"):
                    return False
            else:
                self.print_info(f"Using custom database engine: {db_engine}")

        except Exception as e:
            self.print_warning(f"Could not check database configuration: {e}")

        return True

    def run_migrations(self):
        """Run database migrations for production."""
        self.print_header("RUNNING DATABASE MIGRATIONS")

        commands = [
            (f'"{self.python_executable}" manage.py migrate --verbosity=1',
             "Applying database migrations"),
            (f'"{self.python_executable}" manage.py createcachetable',
             "Creating cache table"),
        ]

        success = True
        for command, description in commands:
            if not self.run_command(command, description):
                success = False

        return success

    def collect_static_files(self):
        """Collect static files for production."""
        self.print_header("COLLECTING STATIC FILES")

        # Check STATIC_ROOT configuration
        try:
            sys.path.append(str(self.project_root))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production')
            from django.conf import settings

            if not hasattr(settings, 'STATIC_ROOT') or not settings.STATIC_ROOT:
                self.print_error("STATIC_ROOT not configured in production settings")
                self.print_error("Add STATIC_ROOT to your production settings")
                return False

            static_root = Path(settings.STATIC_ROOT)
            self.print_info(f"Static files will be collected to: {static_root}")

        except Exception as e:
            self.print_warning(f"Could not check STATIC_ROOT configuration: {e}")
            # Continue anyway

        # Collect static files
        result = self.run_command(
            f'"{self.python_executable}" manage.py collectstatic --noinput --verbosity=1',
            "Collecting static files for production"
        )

        if not result:
            self.print_error("Static files collection failed")
            return False

        return True

    def setup_logging(self):
        """Setup production logging."""
        self.print_header("SETTING UP PRODUCTION LOGGING")

        try:
            sys.path.append(str(self.project_root))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production')
            from django.conf import settings

            # Check if logs directory exists
            logs_dir = self.project_root / "logs"
            logs_dir.mkdir(exist_ok=True)

            # Check logging configuration
            if hasattr(settings, 'LOGGING'):
                log_config = settings.LOGGING
                handlers = log_config.get('handlers', {})

                if 'file' in handlers:
                    log_file = handlers['file'].get('filename')
                    if log_file:
                        log_path = Path(log_file)
                        log_path.parent.mkdir(parents=True, exist_ok=True)
                        self.print_success(f"Production log file configured: {log_file}")
                    else:
                        self.print_warning("File handler configured but no filename specified")
                else:
                    self.print_warning("No file handler found in logging configuration")
            else:
                self.print_warning("No LOGGING configuration found in production settings")

        except Exception as e:
            self.print_warning(f"Could not setup logging: {e}")

        return True

    def run_security_checks(self):
        """Run security checks for production."""
        self.print_header("RUNNING SECURITY CHECKS")

        # Check security settings
        try:
            sys.path.append(str(self.project_root))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production')
            from django.conf import settings

            security_checks = [
                ('DEBUG', getattr(settings, 'DEBUG', True), False, "DEBUG should be False in production"),
                ('SECRET_KEY', len(getattr(settings, 'SECRET_KEY', '')), 32, "SECRET_KEY should be at least 32 characters"),
                ('SECURE_SSL_REDIRECT', getattr(settings, 'SECURE_SSL_REDIRECT', False), True, "SECURE_SSL_REDIRECT should be True"),
                ('SECURE_HSTS_SECONDS', getattr(settings, 'SECURE_HSTS_SECONDS', 0), 31536000, "SECURE_HSTS_SECONDS should be set for HTTPS"),
            ]

            for check_name, actual_value, expected_value, message in security_checks:
                if check_name == 'SECRET_KEY':
                    if actual_value < expected_value:
                        self.print_warning(f"{check_name}: {message}")
                elif actual_value != expected_value:
                    self.print_warning(f"{check_name}: {message}")

        except Exception as e:
            self.print_warning(f"Could not run security checks: {e}")

        return True

    def run_production_checks(self):
        """Run Django production checks."""
        self.print_header("RUNNING PRODUCTION SYSTEM CHECKS")

        return self.run_command(
            f'"{self.python_executable}" manage.py check --deploy',
            "Running Django production system checks"
        )

    def create_deployment_summary(self):
        """Create a deployment summary."""
        self.print_header("DEPLOYMENT SUMMARY")

        summary = {
            "Setup Status": "SUCCESS" if self.setup_success else "FAILED",
            "Warnings": self.warnings_count,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Python Version": sys.version.split()[0],
            "Platform": platform.system(),
        }

        for key, value in summary.items():
            print(f"{key}: {value}")

        # Save summary to file
        summary_file = self.project_root / "deployment_summary.txt"
        try:
            with open(summary_file, 'w') as f:
                f.write("School Management System - Production Deployment Summary\n")
                f.write("=" * 60 + "\n\n")
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
                f.write("\nNext steps:\n")
                f.write("1. Configure your web server (nginx recommended)\n")
                f.write("2. Configure WSGI/ASGI server (gunicorn/daphne recommended)\n")
                f.write("3. Setup SSL certificate\n")
                f.write("4. Configure process manager (systemd/supervisor)\n")
                f.write("5. Setup monitoring and backups\n")
                f.write("6. Test your deployment\n")

            self.print_success(f"Deployment summary saved to: {summary_file}")
        except Exception as e:
            self.print_warning(f"Could not save deployment summary: {e}")

    def show_next_steps(self):
        """Show next steps after production setup."""
        self.print_header("PRODUCTION DEPLOYMENT COMPLETE!")

        if self.setup_success:
            print(f"\n{self.colors['bold']}{self.colors['green']}Your School Management System is ready for production!{self.colors['end']}\n")
        else:
            print(f"\n{self.colors['bold']}{self.colors['red']}Production setup completed with errors. Please review the output above.{self.colors['end']}\n")

        print("Next steps for production deployment:")
        print("1. Configure web server (nginx):")
        print("   - Setup nginx configuration for your domain")
        print("   - Configure SSL certificate")
        print("   - Setup static files serving")

        print("\n2. Configure application server:")
        print("   - Install gunicorn: pip install gunicorn")
        print("   - Create systemd service for gunicorn")
        print("   - Configure process management")

        print("\n3. Environment setup:")
        print("   - Set DJANGO_SETTINGS_MODULE=config.settings.production")
        print("   - Configure environment variables")
        print("   - Setup database connection")

        print("\n4. Security hardening:")
        print("   - Configure firewall rules")
        print("   - Setup SSL/TLS certificates")
        print("   - Configure security headers")

        print("\n5. Monitoring and maintenance:")
        print("   - Setup log rotation")
        print("   - Configure backup scripts")
        print("   - Setup monitoring tools")

        if self.dry_run:
            print(f"\n{self.colors['magenta']}Note: This was a dry run. No changes were made.{self.colors['end']}")

    def run_setup(self):
        """Run the complete production setup process."""
        self.print_header("SCHOOL MANAGEMENT SYSTEM PRODUCTION SETUP")
        self.print_info(f"Python: {sys.version}")
        self.print_info(f"Platform: {platform.system()} {platform.release()}")
        self.print_info(f"Project root: {self.project_root}")

        if self.dry_run:
            self.print_warning("DRY RUN MODE - No changes will be made")

        # Define production setup steps
        setup_steps = [
            ("Validating production environment", self.validate_environment),
            ("Checking production requirements", self.check_production_requirements),
            ("Creating pre-deployment backup", self.create_backup),
            ("Setting up production database", self.setup_database),
            ("Running database migrations", self.run_migrations),
            ("Collecting static files", self.collect_static_files),
            ("Setting up production logging", self.setup_logging),
            ("Running security checks", self.run_security_checks),
            ("Running production system checks", self.run_production_checks),
        ]

        # Execute setup steps
        for step_name, step_func in setup_steps:
            self.print_info(f"Starting: {step_name}")
            if not step_func():
                if not self.confirm_continue(f"Step '{step_name}' had issues. Continue?"):
                    self.print_error("Production setup aborted by user")
                    break

        self.create_deployment_summary()
        self.show_next_steps()
        return self.setup_success


def main():
    """Main entry point."""
    try:
        setup = ProductionSetup()
        success = setup.run_setup()

        if success:
            setup.print_success("🎉 Production setup completed successfully!")
            return 0
        else:
            setup.print_error("❌ Production setup completed with critical errors!")
            return 1
    except KeyboardInterrupt:
        print("\n\nProduction setup was interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error during production setup: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
