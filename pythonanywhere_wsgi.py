"""
Example WSGI file content for PythonAnywhere.

Copy/paste the contents of this file into the PythonAnywhere WSGI configuration file editor
or use it as a reference. Do NOT commit production secrets into source code.

This file assumes the project package is `boyscout_system` and the WSGI application is
`boyscout_system.wsgi.application` (this repo already contains `boyscout_system/wsgi.py`).
"""

import os
import sys

# Add the project directory to the sys.path
project_home = '/home/yourusername/boyscout_system'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# If you use a virtualenv, uncomment and set the path to the virtualenv's site-packages
#venv_path = '/home/yourusername/.virtualenvs/boyscout_system'
#site_packages = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages')
#if site_packages not in sys.path:
#    sys.path.insert(0, site_packages)

# Set the Django settings module (this project uses environment-overridable settings)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
