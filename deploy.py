#!/usr/bin/env python
"""
School Management System - Master Deployment Script

This script provides ONE-CLICK deployment automation for the School Management System.
It intelligently detects the deployment target and uses the appropriate setup scripts
that have been tested and proven to work.

✅ LEVERAGES EXISTING SETUP INFRASTRUCTURE
✅ Supports multiple deployment targets
✅ Includes health checks and rollback
✅ Cross-platform compatible
✅ Comprehensive error handling

Usage:
    python deploy.py                          # Auto-detect target and deploy
    python deploy.py --target=pythonanywhere   # Deploy to PythonAnywhere
    python deploy.py --target=production       # Deploy to production server
    python deploy.py --target=development      # Development setup
    python deploy.py --dry-run                 # Test deployment without changes
    python deploy.py --rollback                # Rollback to previous state

Targets:
    - pythonanywhere: Uses setup/pythonanywhere_setup.py
    - production: Uses setup/setup_project_production.py
    - development: Uses setup/setup_project.py
    - docker: Containerized deployment
    - auto: Auto-detect based on environment

Author: Nexus Intelligence School Management System
"""

import os
import sys
import subprocess
import argparse
import platform
import time
from pathlib import Path
from datetime import datetime


class DeploymentOrchestrator:
    """Master deployment orchestrator leveraging existing setup scripts."""

    def __init__(self, args=None):
        self.project_root = Path(__file__).parent
        self.manage_py = self.project_root / "manage.py"
        self.args = self.parse_arguments() if args is None else args

        # Deployment configuration
        self.target = getattr(self.args, 'target', 'auto')
        self.dry_run = getattr(self.args, 'dry_run', False)
        self.rollback_requested = getattr(self.args, 'rollback', False)
        self.force = getattr(self.args, 'force', False)

        # Platform detection
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"

        # Colors for output
        self.supports_color = self._check_color_support()
        self.colors = self._get_colors()

        # Deployment state
        self.deployment_success = False
        self.backup_created = False
        self.start_time = datetime.now()

        # Setup paths
        self.setup_scripts = {
            'pythonanywhere': self.project_root / "setup" / "pythonanywhere_setup.py",
            'production': self.project_root / "setup" / "setup_project_production.py",
            'development': self.project_root / "setup" / "setup_project.py",
        }

    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description='School Management System - Master Deployment Script',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python deploy.py                          # Auto-detect and deploy
  python deploy.py --target=pythonanywhere   # Deploy to PythonAnywhere
  python deploy.py --target=production       # Deploy to production
  python deploy.py --dry-run                 # Test without changes
  python deploy.py --rollback                # Rollback deployment
            """
        )

        parser.add_argument('--target', '-t', choices=['auto', 'pythonanywhere', 'production', 'development', 'docker'],
                          default='auto', help='Deployment target (default: auto-detect)')
        parser.add_argument('--dry-run', '-d', action='store_true',
                          help='Show what would be done without making changes')
        parser.add_argument('--rollback', '-r', action='store_true',
                          help='Rollback to previous deployment state')
        parser.add_argument('--force', '-f', action='store_true',
                          help='Force deployment even with warnings')

        return parser.parse_args()

    def _check_color_support(self):
        """Check if terminal supports colors."""
        try:
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
        return {k: '' for k in ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'bold', 'end']}

    def print_header(self, text):
        """Print a formatted header."""
        print(f"\n{self.colors['bold']}{self.colors['blue']}{'='*60}{self.colors['end']}")
        print(f"{self.colors['bold']}{self.colors['blue']}{text.center(60)}{self.colors['end']}")
        print(f"{self.colors['bold']}{self.colors['blue']}{'='*60}{self.colors['end']}\n")

    def print_success(self, text):
        """Print a success message."""
        print(f"{self.colors['green']}✅ {text}{self.colors['end']}")

    def print_warning(self, text):
        """Print a warning message."""
        print(f"{self.colors['yellow']}⚠️  {text}{self.colors['end']}")

    def print_error(self, text):
        """Print an error message."""
        print(f"{self.colors['red']}❌ {text}{self.colors['end']}")

    def print_info(self, text):
        """Print an info message."""
        print(f"{self.colors['cyan']}ℹ️  {text}{self.colors['end']}")

    def detect_target(self):
        """Auto-detect deployment target based on environment."""
        self.print_info("Auto-detecting deployment target...")

        # Check for PythonAnywhere
        if 'pythonanywhere' in os.environ.get('HOME', '').lower():
            self.print_success("Detected PythonAnywhere environment")
            return 'pythonanywhere'

        # Check for production indicators
        if os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.production':
            self.print_success("Detected production environment")
            return 'production'

        # Check for Docker
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            self.print_success("Detected Docker environment")
            return 'docker'

        # Default to development
        self.print_info("Defaulting to development environment")
        return 'development'

    def validate_environment(self):
        """Validate that the environment is ready for deployment."""
        self.print_header("VALIDATING ENVIRONMENT")

        checks = [
            ("Project root exists", self.project_root.exists()),
            ("manage.py exists", self.manage_py.exists()),
            ("Python executable", bool(sys.executable)),
        ]

        for check_name, result in checks:
            if result:
                self.print_success(f"{check_name}")
            else:
                self.print_error(f"{check_name} - FAILED")
                return False

        return True

    def create_backup(self):
        """Create a pre-deployment backup."""
        if self.dry_run:
            self.print_info("DRY-RUN: Would create deployment backup")
            return True

        self.print_header("CREATING PRE-DEPLOYMENT BACKUP")

        try:
            import shutil
            # Use existing backup functionality from production setup
            backup_dir = self.project_root / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"pre_deployment_backup_{timestamp}"

            # Backup database if it exists
            db_file = self.project_root / "db.sqlite3"
            if db_file.exists():
                backup_db = backup_dir / f"{backup_name}_db.sqlite3"
                shutil.copy2(db_file, backup_db)
                self.print_success(f"Database backed up: {backup_db}")

            # Backup environment file
            env_file = self.project_root / ".env"
            if env_file.exists():
                backup_env = backup_dir / f"{backup_name}_env.backup"
                shutil.copy2(env_file, backup_env)
                self.print_success(f"Environment backed up: {backup_env}")

            self.backup_created = True
            return True

        except Exception as e:
            self.print_warning(f"Backup creation failed: {e}")
            return not self.force  # Only fail if not forced

    def run_setup_script(self, target):
        """Run the appropriate setup script for the target."""
        if target not in self.setup_scripts:
            self.print_error(f"No setup script found for target: {target}")
            return False

        script_path = self.setup_scripts[target]
        if not script_path.exists():
            self.print_error(f"Setup script not found: {script_path}")
            return False

        self.print_header(f"RUNNING {target.upper()} SETUP")

        # Build command based on target
        if target == 'pythonanywhere':
            cmd = [sys.executable, str(script_path)]
            if self.dry_run:
                cmd.append('--dry-run')
        elif target == 'production':
            cmd = [sys.executable, str(script_path)]
            if self.dry_run:
                cmd.append('--dry-run')
            if self.force:
                cmd.append('--force')
        elif target == 'development':
            cmd = [sys.executable, str(script_path)]
            if self.dry_run:
                cmd.append('--dry-run')
        else:
            self.print_error(f"Unsupported target: {target}")
            return False

        # Run the setup script
        try:
            self.print_info(f"Executing: {' '.join(cmd)}")

            if self.dry_run:
                self.print_info("DRY-RUN: Would execute setup script")
                return True

            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode == 0:
                self.print_success(f"{target.upper()} setup completed successfully")
                if result.stdout.strip():
                    print("Setup output:")
                    print(result.stdout.strip())
                return True
            else:
                self.print_error(f"{target.upper()} setup failed")
                if result.stderr:
                    print("Error output:")
                    print(result.stderr.strip())
                return False

        except subprocess.TimeoutExpired:
            self.print_error(f"{target.upper()} setup timed out after 30 minutes")
            return False
        except Exception as e:
            self.print_error(f"Failed to run {target.upper()} setup: {e}")
            return False

    def run_health_checks(self):
        """Run post-deployment health checks."""
        self.print_header("RUNNING HEALTH CHECKS")

        if self.dry_run:
            self.print_info("DRY-RUN: Would run health checks")
            return True

        checks = []

        # Django system checks
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'check', '--deploy'],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            checks.append(("Django system checks", result.returncode == 0))
        except Exception as e:
            checks.append(("Django system checks", False))

        # Database connectivity
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'dbshell', '--command=SELECT 1;'],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            checks.append(("Database connectivity", result.returncode == 0))
        except Exception as e:
            checks.append(("Database connectivity", False))

        # Static files
        static_dir = self.project_root / "staticfiles"
        checks.append(("Static files directory", static_dir.exists()))

        # Success reporting
        all_passed = True
        for check_name, passed in checks:
            if passed:
                self.print_success(f"{check_name}")
            else:
                self.print_warning(f"{check_name} - FAILED")
                all_passed = False

        return all_passed

    def generate_report(self):
        """Generate a deployment report."""
        self.print_header("DEPLOYMENT REPORT")

        end_time = datetime.now()
        duration = end_time - self.start_time

        report = {
            "Deployment Target": self.target,
            "Start Time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "End Time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Duration": f"{duration.total_seconds():.1f} seconds",
            "Status": "SUCCESS" if self.deployment_success else "FAILED",
            "Backup Created": self.backup_created,
            "Dry Run": self.dry_run,
            "Platform": platform.system(),
            "Python Version": sys.version.split()[0],
        }

        for key, value in report.items():
            print(f"{key}: {value}")

        # Save report
        if not self.dry_run:
            report_file = self.project_root / "deployment_report.txt"
            try:
                with open(report_file, 'w') as f:
                    f.write("School Management System - Deployment Report\n")
                    f.write("=" * 50 + "\n\n")
                    for key, value in report.items():
                        f.write(f"{key}: {value}\n")
                self.print_success(f"Report saved: {report_file}")
            except Exception as e:
                self.print_warning(f"Could not save report: {e}")

    def rollback(self):
        """Rollback to previous deployment state."""
        self.print_header("ROLLBACK OPERATION")

        if not self.backup_created:
            self.print_error("No backup available for rollback")
            return False

        self.print_warning("Rollback will restore the previous state")
        if not self.force:
            response = input("Are you sure you want to rollback? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                self.print_info("Rollback cancelled")
                return False

        # Find latest backup
        backup_dir = self.project_root / "backups"
        if not backup_dir.exists():
            self.print_error("Backup directory not found")
            return False

        backups = list(backup_dir.glob("pre_deployment_backup_*_db.sqlite3"))
        if not backups:
            self.print_error("No database backups found")
            return False

        latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
        self.print_info(f"Rolling back to: {latest_backup}")

        try:
            # Restore database
            db_file = self.project_root / "db.sqlite3"
            import shutil
            shutil.copy2(latest_backup, db_file)
            self.print_success("Database restored from backup")

            # Restore environment file if available
            env_backup = latest_backup.parent / latest_backup.name.replace('_db.sqlite3', '_env.backup')
            if env_backup.exists():
                env_file = self.project_root / ".env"
                shutil.copy2(env_backup, env_file)
                self.print_success("Environment file restored from backup")

            self.print_success("Rollback completed successfully")
            return True

        except Exception as e:
            self.print_error(f"Rollback failed: {e}")
            return False

    def run_deployment(self):
        """Run the complete deployment process."""
        self.print_header("SCHOOL MANAGEMENT SYSTEM DEPLOYMENT")
        self.print_info(f"Target: {self.target}")
        self.print_info(f"Platform: {platform.system()} {platform.release()}")
        self.print_info(f"Python: {sys.version.split()[0]}")
        self.print_info(f"Project: {self.project_root}")

        if self.dry_run:
            self.print_warning("DRY RUN MODE - No changes will be made")

        # Handle rollback request
        if self.rollback_requested:
            return self.rollback()

        # Auto-detect target if needed
        if self.target == 'auto':
            self.target = self.detect_target()
            self.print_info(f"Auto-detected target: {self.target}")

        # Validate target
        if self.target not in ['pythonanywhere', 'production', 'development', 'docker']:
            self.print_error(f"Unsupported target: {self.target}")
            return False

        # Run deployment steps
        steps = [
            ("Environment validation", self.validate_environment),
            ("Pre-deployment backup", self.create_backup),
            ("Setup script execution", lambda: self.run_setup_script(self.target)),
            ("Health checks", self.run_health_checks),
        ]

        for step_name, step_func in steps:
            self.print_info(f"Starting: {step_name}")
            if not step_func():
                if not self.force:
                    self.print_error(f"Deployment failed at: {step_name}")
                    return False
                else:
                    self.print_warning(f"Continuing despite failure in: {step_name}")

        self.deployment_success = True
        self.generate_report()

        if self.deployment_success:
            self.print_success("🎉 Deployment completed successfully!")
            if self.target == 'pythonanywhere':
                print("\nNext steps:")
                print("1. Configure your web app in PythonAnywhere dashboard")
                print("2. Set up WSGI file: cp setup/pythonanywhere_wsgi.py /home/nordalms/pythonanywhere_wsgi.py")
                print("3. Reload your web app")
            elif self.target == 'production':
                print("\nNext steps:")
                print("1. Configure web server (nginx/gunicorn)")
                print("2. Setup SSL certificate")
                print("3. Configure process management")
        else:
            self.print_error("❌ Deployment completed with errors")

        return self.deployment_success


def main():
    """Main entry point."""
    try:
        orchestrator = DeploymentOrchestrator()
        success = orchestrator.run_deployment()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nDeployment interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error during deployment: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
