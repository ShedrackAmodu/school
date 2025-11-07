#!/usr/bin/env python
"""
PythonAnywhere Setup Helper Script

This script helps with initial setup on PythonAnywhere.
Run this after uploading your code to PythonAnywhere.
"""

import os
import sys
import subprocess
import argparse
import platform

def run_command(command, description):
    """Run a command and print status."""
    print(f"\n🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        if e.stderr:
            print(f"Error: {e.stderr.strip()}")
        return False

def main():
    print("🚀 PythonAnywhere Setup Helper")
    print("=" * 50)

    # Check if we're on PythonAnywhere
    if 'pythonanywhere' not in os.environ.get('HOME', '').lower():
        print("⚠️  Warning: This doesn't appear to be running on PythonAnywhere")
        print("This script is designed for PythonAnywhere deployment")
        # In dry-run mode, automatically continue for testing
        if not (len(sys.argv) > 1 and '--dry-run' in sys.argv):
            if input("Continue anyway? (y/N): ").lower() != 'y':
                return

    # Platform-specific commands
    if platform.system() == "Windows":
        python_cmd = "python"
        venv_activate = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
        python_exec = "venv\\Scripts\\python"
    else:
        python_cmd = "python3"
        venv_activate = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
        python_exec = "venv/bin/python"

    # Setup steps
    steps = [
        (f"Creating virtual environment", f"{python_cmd} -m venv venv"),
        (f"Activating virtual environment", venv_activate),
        (f"Installing requirements", f"{pip_cmd} install -r setup/requirements/production.txt"),
        (f"Running database migrations", f"{python_exec} manage.py migrate"),
        (f"Collecting static files", f"{python_exec} manage.py collectstatic --noinput"),
    ]

    success_count = 0
    for description, command in steps:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"\n❌ Setup failed at: {description}")
            break

    print(f"\n📊 Setup completed: {success_count}/{len(steps)} steps successful")

    if success_count == len(steps):
        print("\n🎉 Basic setup complete!")
        print("Next steps:")
        print("1. Create your superuser: python manage.py createsuperuser")
        print("2. Configure your web app in PythonAnywhere dashboard")
        print("3. Set up WSGI file: cp setup/pythonanywhere_wsgi.py /home/nordalms/pythonanywhere_wsgi.py")
        print("4. Reload your web app")
    else:
        print("\n❌ Setup had issues. Please check the errors above.")

if __name__ == "__main__":
    main()
