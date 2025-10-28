PythonAnywhere deployment notes for BoyScout-Registration-System

This file contains minimal, repeatable steps to deploy the Django project to PythonAnywhere.

Prerequisites
- A PythonAnywhere account
- A virtualenv on PythonAnywhere using a Python version that satisfies `requirements.txt` (e.g. 3.11+)

Quick steps

1. Pull the repository on PythonAnywhere (or push from your local machine):

   git clone <your-repo-url> ~/boyscout_system

2. Create and activate a virtualenv on PythonAnywhere (adjust pythonX.Y):

   python3.11 -m venv ~/.virtualenvs/boyscout_system
   source ~/.virtualenvs/boyscout_system/bin/activate

3. Install requirements:

   pip install -r requirements.txt

4. In the PythonAnywhere Web tab, set the working directory to the project path, for example:

   /home/yourusername/boyscout_system

   Set the virtualenv path to: /home/yourusername/.virtualenvs/boyscout_system

5. Environment variables (use the 'Web' > 'Environment variables' section):

   - SECRET_KEY: (set a secure secret key)
   - DEBUG: False
   - ALLOWED_HOSTS: yourusername.pythonanywhere.com
   - Any other gateway keys used by your project (PAYMONGO_*, TWILIO_*, EMAIL_* etc.)

   Note: `ALLOWED_HOSTS` is read from environment in `boyscout_system/settings.example.py`.

6. Static files mapping (Web tab -> Static files):

   URL: /static/  ->  /home/yourusername/boyscout_system/staticfiles/
   URL: /media/   ->  /home/yourusername/boyscout_system/media/

7. Run migrations and collectstatic (either in Bash console or via a virtualenv):

   source ~/.virtualenvs/boyscout_system/bin/activate
   cd ~/boyscout_system
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput

8. Make sure the WSGI configuration file on PythonAnywhere points to the project WSGI application. Example content is provided in `pythonanywhere_wsgi.py` in this repo — you can copy/paste into the PythonAnywhere WSGI file editor.

9. Reload the web app from the PythonAnywhere Web tab.

Troubleshooting notes
- If you get import errors, double-check the virtualenv path and that `pip install -r requirements.txt` completed successfully.
- If static files are 404, verify `collectstatic` ran and the Static files mapping is correct.
- Keep sensitive keys out of version control; use the PythonAnywhere environment variables.

Security
- Ensure `DEBUG=False` in production and `SECRET_KEY` is set to a secure value.

Optional local steps before upload
- Run tests locally and ensure migrations are committed. (Note: some tests in this repo may touch external services; run selectively.)

This README is intentionally minimal — the repo already supports environment-driven configuration (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`).
