PythonAnywhere — Web tab quick checklist

Paste this checklist into the PythonAnywhere Web tab when configuring the web app.

1) Working directory

   Set to the project root on PythonAnywhere, for example:

   /home/yourusername/boyscout_system

2) Virtualenv

   Create a virtualenv on PythonAnywhere and set the path here, for example:

   /home/yourusername/.virtualenvs/boyscout_system

   Then in a Bash console on PA:

   source /home/yourusername/.virtualenvs/boyscout_system/bin/activate
   pip install -r /home/yourusername/boyscout_system/requirements.txt

3) WSGI configuration (WSGI file editor)

   - Open the WSGI configuration editor in the Web tab and replace its contents with the example below (or copy the contents of `pythonanywhere_wsgi.py` in this repo). Update `yourusername` and Python version paths as needed.

   Example (copy/paste and edit):

   import os
   import sys

   project_home = '/home/yourusername/boyscout_system'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   # Optional: add virtualenv site-packages (adjust python version)
   # venv_path = '/home/yourusername/.virtualenvs/boyscout_system'
   # site_packages = os.path.join(venv_path, 'lib', 'python3.11', 'site-packages')
   # if site_packages not in sys.path:
   #     sys.path.insert(0, site_packages)

   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boyscout_system.settings')

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()

4) Static files mapping (Web tab -> Static files)

   URL: /static/    => /home/yourusername/boyscout_system/staticfiles/
   URL: /media/     => /home/yourusername/boyscout_system/media/

   Notes:
   - `STATIC_ROOT` in the project is `BASE_DIR / 'staticfiles'` (see `settings.example.py`).
   - Run `collectstatic` after deploying so `staticfiles/` is populated.

5) Environment variables (Web tab -> Environment variables)

   Set values here instead of committing secrets. Minimum recommended variables:

   SECRET_KEY        = <a secure random string>
   DEBUG             = False
   ALLOWED_HOSTS     = yourusername.pythonanywhere.com

   Optional/required depending on features used in this project:
   PAYMONGO_PUBLIC_KEY
   PAYMONGO_SECRET_KEY
   PAYMONGO_WEBHOOK_SECRET
   TWILIO_ACCOUNT_SID
   TWILIO_AUTH_TOKEN
   TWILIO_PHONE_NUMBER
   EMAIL_HOST
   EMAIL_PORT
   EMAIL_HOST_USER
   EMAIL_HOST_PASSWORD
   DEFAULT_FROM_EMAIL

   Tip: `ALLOWED_HOSTS` is read from the environment in `boyscout_system/settings.example.py` (comma-separated).

6) Console commands to run (after virtualenv activated)

   cd /home/yourusername/boyscout_system
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput

7) Reload

   After configuring WSGI, env vars and static mapping, click "Reload" on the Web tab.

8) Channels / ASGI note

   - This project uses `channels` (ASGI). PythonAnywhere does not provide native long-running ASGI/Daphne processes or WebSocket support on the standard WSGI web app.
   - If you need real WebSocket/ASGI support in production, consider running Daphne/ASGI on a different host (e.g. a VPS, or a Platform-as-a-Service that supports ASGI) and use Redis or another channel layer there.
   - For many use-cases this site will still function on PythonAnywhere with only the WSGI app (notifications may be degraded).

9) Troubleshooting quick hits

   - ImportError on PA: ensure virtualenv path is set and `pip install -r requirements.txt` completed.
   - 500 errors: open the error log in the Web tab to see tracebacks. Missing env var? Check the Environment variables section.
   - Static 404: confirm `collectstatic` ran and static mapping points to `/staticfiles/`.

Keep this checklist short and paste the relevant snippets into the PythonAnywhere Web UI.
