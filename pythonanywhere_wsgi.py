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
# Before setting DJANGO_SETTINGS_MODULE, attempt to load a local .env file so
# environment variables are available early (this helps when you configure
# variables via a file in the PythonAnywhere console).
env_path = os.path.join(project_home, '.env')
if os.path.exists(env_path):
    # Try using python-dotenv if available, otherwise do a minimal parse.
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        try:
            with open(env_path, 'r') as _f:
                for _raw in _f:
                    _line = _raw.strip()
                    if not _line or _line.startswith('#') or '=' not in _line:
                        continue
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('\"\'')
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
        except Exception:
            pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
