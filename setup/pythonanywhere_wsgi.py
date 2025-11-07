"""
WSGI configuration for PythonAnywhere deployment.

This file is required by PythonAnywhere for Django deployment.
Copy this file to your PythonAnywhere project root and update the path.
"""

import os
import sys

# Add your project directory to the Python path
# Use environment variable or default to current directory parent
project_home = os.environ.get('PROJECT_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production')

# Configure Django
import django
django.setup()

# Import the WSGI application
from config.wsgi import application
