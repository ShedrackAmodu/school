#!/usr/bin/env python
"""
School Management System - Complete Project Setup Script

This script provides FULLY AUTOMATED setup for the School Management System.
It automatically installs missing dependencies, deletes databases/migrations/caches,
creates fresh migrations, runs all migrations at once, and creates a superuser.

✅ FULLY AUTOMATED - No manual input required!
✅ Auto-installs missing Python packages
✅ Deletes database & clears cache before setup
✅ Runs all migrations simultaneously
✅ Creates superuser: admin/admin123/shedy@gmail.com

Usage:
    python setup/setup_project.py                    # Fully automated setup
    python setup/setup_project.py --dry-run          # See what would happen
    python setup/setup_project.py --skip-superuser   # Skip superuser creation
    python setup/setup_project.py --skip-collectstatic  # Skip static files

Requirements:
    - Python virtual environment (recommended but not required)
    - Environment variables configured (.env file)

Author: Nexus Intelligence School Management System
"""

import os
import sys
import subprocess
import argparse
import logging
import getpass
import platform
from pathlib import Path


class ProjectSetup:
    """Handles complete project setup after database deletion."""

    def __init__(self, args=None):
        self.project_root = Path(__file__).parent.parent
        self.manage_py = self.project_root / "manage.py"

        # Setup argument parsing
        self.args = self.parse_arguments() if args is None else args

        # CLI options - default to fully automated mode
        self.auto_yes = getattr(self.args, 'yes', True)  # Default to True for full automation
        self.skip_collectstatic_flag = getattr(self.args, 'skip_collectstatic', False)
        self.dry_run = getattr(self.args, 'dry_run', False)
        self.skip_superuser = getattr(self.args, 'skip_superuser', False)

        # Use the current Python executable for cross-platform compatibility
        self.python_executable = sys.executable or "python"
        
        # Platform-specific settings
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"

        # Colors for output (only use if terminal supports it)
        self.supports_color = self._check_color_support()
        self.colors = self._get_colors()

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
        
        # Track setup progress
        self.setup_success = True

    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description='School Management System Setup Script')
        parser.add_argument('--yes', '-y', action='store_true', 
                          help='Auto-confirm all prompts')
        parser.add_argument('--skip-collectstatic', action='store_true', 
                          help='Skip collecting static files')
        parser.add_argument('--skip-superuser', action='store_true',
                          help='Skip superuser creation')
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
            # Return empty strings if no color support
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

    def print_error(self, text):
        """Print an error message."""
        print(f"{self.colors['red']}✗ {text}{self.colors['end']}")
        self.setup_success = False

    def print_info(self, text):
        """Print an info message."""
        print(f"{self.colors['cyan']}ℹ {text}{self.colors['end']}")

    def confirm_continue(self, message="Continue?"):
        """Automatically continue (fully automated mode)."""
        self.print_info(f"Auto-continuing: {message}")
        return True

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
            if result.stdout and result.stdout.strip():
                # Only show output if it's not empty
                output_lines = result.stdout.strip().split('\n')
                if len(output_lines) > 0 and output_lines[0].strip():
                    print(f"Output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            if critical:
                self.print_error(f"Failed: {description}")
                self.setup_success = False  # Only set failure for critical errors
            else:
                self.print_warning(f"Non-critical issue: {description}")

            # Print both stderr and stdout to help debugging
            if e.stderr and e.stderr.strip():
                print(f"Error: {e.stderr.strip()}")
            if e.stdout and e.stdout.strip():
                print(f"Output: {e.stdout.strip()}")

            return not critical  # Return True for non-critical failures

    def check_requirements(self):
        """Check if all requirements are met."""
        self.print_header("CHECKING REQUIREMENTS")

        # Check if virtual environment is activated
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
        if not in_venv:
            self.print_warning("Virtual environment not detected.")
            if not self.confirm_continue("Continue without virtual environment?"):
                return False

        # Check if manage.py exists
        if not self.manage_py.exists():
            self.print_error("manage.py not found. Are you in the project root?")
            return False

        # Check for required Python packages
        required_packages = {
            'django': 'Django',
            'psutil': 'psutil',
            'dotenv': 'python-dotenv',  # For .env handling
            'rest_framework': 'djangorestframework',
            'channels': 'channels',
            'channels_redis': 'channels-redis',  # Added missing package
            'templated_email': 'django-templated-mail',  # Fixed import name
            'PIL': 'Pillow',
            'crispy_forms': 'django-crispy-forms',
            'crispy_bootstrap5': 'crispy-bootstrap5',
            'pandas': 'pandas',
            'openpyxl': 'openpyxl',
            'django_extensions': 'django-extensions',  # Added missing package
        }

        for package, import_name in required_packages.items():
            if self.dry_run:
                # In dry-run mode, just show what would be checked
                self.print_info(f"Would check {package} availability")
                continue

            try:
                __import__(import_name)
                self.print_success(f"{package} is available")
            except ImportError:
                self.print_info(f"{package} not found, installing automatically...")
                # Try to install the package automatically
                install_cmd = f"pip install {package}"
                if not self.run_command(install_cmd, f"Installing {package}"):
                    self.print_error(f"Failed to install {package}")
                    return False
                else:
                    # Verify installation
                    try:
                        __import__(import_name)
                        self.print_success(f"{package} installed successfully")
                    except ImportError:
                        self.print_error(f"Failed to import {package} after installation")
                        return False

        # Check for .env file
        env_files = list(self.project_root.glob('*.env')) + list(self.project_root.glob('.env*')) + list((self.project_root / 'setup').glob('*.env')) + list((self.project_root / 'setup').glob('.env*'))
        if not env_files:
            self.print_warning("No .env file found. Please ensure environment variables are configured.")
        else:
            self.print_success(f"Found environment file: {env_files[0].name}")

        return True

    def delete_database_and_cache(self):
        """Delete database file and clear caches before setup."""
        self.print_header("DELETING DATABASE AND CLEARING CACHE")

        # Delete database file
        db_file = self.project_root / "db.sqlite3"
        if db_file.exists():
            try:
                if not self.dry_run:
                    db_file.unlink()
                self.print_success("Deleted database file")
            except Exception as e:
                self.print_warning(f"Could not delete database file: {e}")
        else:
            self.print_info("No database file found")

        # Clear Django cache (if possible)
        try:
            result = self.run_command(
                f'"{self.python_executable}" manage.py shell -c "from django.core.cache import cache; cache.clear(); print(\'Cache cleared\')"',
                "Clearing Django cache",
                critical=False
            )
            if result:
                self.print_success("Django cache cleared")
        except:
            self.print_info("Could not clear Django cache (may not be configured)")

        return True

    def cleanup_migrations(self):
        """Clean up migration files before creating new ones."""
        self.print_header("CLEANING UP MIGRATIONS")

        # Find migration directories in all apps
        apps_dir = self.project_root / "apps"
        if not apps_dir.exists():
            self.print_info("No apps directory found")
            return True

        # Also check for Django's contrib migrations
        migration_dirs = list(apps_dir.rglob("*/migrations"))
        # Add Django's built-in migrations if they exist
        django_migrations = self.project_root / "venv" / "Lib" / "site-packages" / "django" / "contrib" / "**" / "migrations"
        if django_migrations.exists():
            migration_dirs.extend(list(django_migrations.glob("*")))

        if not migration_dirs:
            self.print_info("No migration directories found")
            return True

        total_files_removed = 0
        for migration_dir in migration_dirs:
            if migration_dir.is_dir() and migration_dir.name == "migrations":
                # Keep __init__.py, remove other .py files
                py_files = list(migration_dir.glob("*.py"))
                files_removed = 0
                for py_file in py_files:
                    if py_file.name != "__init__.py":
                        try:
                            if not self.dry_run:
                                py_file.unlink()
                            files_removed += 1
                            total_files_removed += 1
                        except Exception as e:
                            self.print_warning(f"Could not remove {py_file}: {e}")

                if files_removed > 0:
                    self.print_success(f"Cleaned {files_removed} files from {migration_dir.relative_to(self.project_root)}")

        if total_files_removed > 0:
            self.print_success(f"Total migration files cleaned: {total_files_removed}")
        else:
            self.print_info("No migration files to clean")

        return True

    def make_migrations(self):
        """Create new migrations."""
        self.print_header("CREATING MIGRATIONS")
        
        return self.run_command(
            f'"{self.python_executable}" manage.py makemigrations --verbosity=1',
            "Creating database migrations"
        )

    def run_migrations(self):
        """Run Django migrations."""
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

    def setup_initial_data(self):
        """Set up initial data using management commands."""
        self.print_header("SETTING UP INITIAL DATA")

        # Set site domain for local development
        site_shell_script = r"from django.contrib.sites.models import Site; site, created = Site.objects.get_or_create(id=1, defaults={'name': 'NexusSMS', 'domain': 'localhost:8000'}); site.name = 'NexusSMS'; site.domain = 'localhost:8000'; site.save(); print('Site domain set to localhost:8000 for development')"
        self.run_command(
            f'"{self.python_executable}" manage.py shell -c "{site_shell_script}"',
            "Configuring site domain for local development",
            critical=False
        )

        # List of potential setup commands (some might not exist in all projects)
        setup_commands = [
            (f'"{self.python_executable}" manage.py seed_staff_roles',
             "Creating default staff roles for user management"),
            (f'"{self.python_executable}" manage.py assign_role_permissions',
             "Assigning appropriate permissions to all staff roles"),
            (f'"{self.python_executable}" manage.py sync_permissions',
             "Synchronizing user permissions based on their roles"),
            (f'"{self.python_executable}" manage.py populate_exam_types',
             "Creating default exam types for assessment system"),
            (f'"{self.python_executable}" manage.py create_system_kpis',
             "Creating system performance KPIs"),
            (f'"{self.python_executable}" manage.py create_system_reports',
             "Creating system report types"),
            (f'"{self.python_executable}" manage.py populate_legal_documents',
             "Populating legal documents"),
        ]

        # Try each command, but don't fail the entire setup if some are missing
        for command, description in setup_commands:
            self.run_command(command, description, critical=False)

        return True

    def collect_static_files(self):
        """Collect static files."""
        self.print_header("COLLECTING STATIC FILES")

        if self.skip_collectstatic_flag:
            self.print_warning("Skipping collectstatic (--skip-collectstatic flag set)")
            return True

        # Check if STATIC_ROOT is configured
        try:
            # Import Django settings safely
            sys.path.append(str(self.project_root))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.development')
            from django.conf import settings
            if not hasattr(settings, 'STATIC_ROOT') or not settings.STATIC_ROOT:
                self.print_warning("STATIC_ROOT not configured. Skipping static files collection.")
                self.print_warning("Configure STATIC_ROOT in settings for production deployment.")
                return True
        except Exception as e:
            self.print_warning(f"Could not check STATIC_ROOT configuration: {e}")
            # Continue anyway - let Django handle the error

        result = self.run_command(
            f'"{self.python_executable}" manage.py collectstatic --noinput --verbosity=1',
            "Collecting static files",
            critical=False  # Don't fail setup for static files
        )

        if not result:
            self.print_warning("Static files collection had issues")
            self.print_warning("You may need to configure STATIC_ROOT and run collectstatic manually.")

        return True

    def create_superuser(self):
        """Create a superuser automatically with predefined credentials."""
        if self.skip_superuser:
            self.print_warning("Skipping superuser creation (--skip-superuser flag set)")
            return True

        self.print_header("CREATING SUPERUSER")

        # Set predefined superuser credentials
        env = os.environ.copy()
        env['DJANGO_SUPERUSER_USERNAME'] = 'admin'
        env['DJANGO_SUPERUSER_EMAIL'] = 'shedrackamodu5@gmail.com'
        env['DJANGO_SUPERUSER_PASSWORD'] = 'admin123'

        self.print_info("Creating superuser with predefined credentials")
        return self.run_command(
            f'"{self.python_executable}" manage.py createsuperuser --noinput',
            "Creating superuser account (admin/admin123/shedrackamodu5@gmail.com)",
            env=env,
        )

    def collect_initial_metrics(self):
        """Collect initial system metrics."""
        self.print_header("COLLECTING INITIAL SYSTEM METRICS")

        return self.run_command(
            f'"{self.python_executable}" manage.py collect_system_metrics',
            "Collecting initial system performance metrics",
            critical=False  # Don't fail setup for metrics collection
        )

    def run_system_checks(self):
        """Run Django system checks."""
        self.print_header("RUNNING SYSTEM CHECKS")

        return self.run_command(
            f'"{self.python_executable}" manage.py check --deploy',
            "Running Django system checks",
            critical=False  # Warnings are ok, just inform the user
        )

    def show_next_steps(self):
        """Show next steps after setup."""
        self.print_header("SETUP COMPLETE!")

        print(f"\n{self.colors['bold']}{self.colors['green']}Your School Management System is now ready!{self.colors['end']}\n")

        print("Next steps:")
        print("1. Start the development server:")
        print("   python manage.py runserver")
        print("\n2. Access the admin panel:")
        print("   http://localhost:8000/admin/")
        print("\n3. Access the analytics dashboard:")
        print("   http://localhost:8000/analytics/")
        print("\n4. Create additional users and configure the system")

        print(f"\n{self.colors['yellow']}Useful management commands:{self.colors['end']}")
        print("- Collect system metrics: python manage.py collect_system_metrics")
        print("- Create backup: python manage.py dumpdata > backup.json")
        print("- Restore backup: python manage.py loaddata backup.json")
        
        if self.dry_run:
            print(f"\n{self.colors['magenta']}Note: This was a dry run. No changes were made.{self.colors['end']}")

    def run_setup(self):
        """Run the complete setup process."""
        self.print_header("SCHOOL MANAGEMENT SYSTEM SETUP")
        self.print_info(f"Python: {sys.version}")
        self.print_info(f"Platform: {platform.system()} {platform.release()}")
        self.print_info(f"Project root: {self.project_root}")
        
        if self.dry_run:
            self.print_warning("DRY RUN MODE - No changes will be made")

        # Define setup steps
        setup_steps = [
            ("Checking requirements", self.check_requirements),
            ("Deleting database and clearing cache", self.delete_database_and_cache),
            ("Cleaning up migrations", self.cleanup_migrations),
            ("Creating migrations", self.make_migrations),
            ("Running migrations", self.run_migrations),
            ("Setting up initial data", self.setup_initial_data),
            ("Collecting static files", self.collect_static_files),
        ]
        
        if not self.skip_superuser:
            setup_steps.append(("Creating superuser", self.create_superuser))
            
        setup_steps.extend([
            ("Collecting initial metrics", self.collect_initial_metrics),
            ("Running system checks", self.run_system_checks),
        ])

        # Execute setup steps
        for step_name, step_func in setup_steps:
            self.print_info(f"Starting: {step_name}")
            if not step_func():
                if not self.confirm_continue(f"Step '{step_name}' had issues. Continue?"):
                    self.print_error("Setup aborted by user")
                    return False

        self.show_next_steps()
        return self.setup_success


def main():
    """Main entry point."""
    try:
        setup = ProjectSetup()
        success = setup.run_setup()

        if success:
            setup.print_success("🎉 Project setup completed successfully!")
            return 0
        else:
            setup.print_error("❌ Project setup completed with critical errors!")
            return 1
    except KeyboardInterrupt:
        print("\n\nSetup was interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
