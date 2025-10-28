## ScoutConnect — Quick AI instructions for contributors

This file gives focused, actionable guidance for an AI coding agent to be productive in this repository. Keep suggestions specific to files and patterns actually present in the codebase.

- Repository type: Django web app (Django 5.x) with Channels for realtime notifications. Key entrypoints: `manage.py`, `boyscout_system/settings.example.py`, `boyscout_system/asgi.py`.

- Major apps and responsibilities:
  - `accounts/` — custom user model and registration flows (see `accounts/models.py`; AUTH_USER_MODEL is `accounts.User`).
  - `payments/` — QR PH / PayMongo payment models and webhook logging (`payments/models.py`, `payments/templates/`). Webhook payloads are archived to `WebhookLog` for replay/debug.
  - `events/`, `announcements/`, `notifications/`, `analytics/` — feature modules; notifications use a context processor at `notifications.context_processors.notifications_unread`.

- Important conventions and patterns to follow (not generic advice — these are repo specifics):
  - The project uses a custom `User` (see `accounts/models.py`). Assume `email` is the `USERNAME_FIELD`. Any user-related changes must respect `AUTH_USER_MODEL`.
  - Batch registration flows exist: `BatchRegistration` and `BatchStudentData` store staged student info before user creation — modifications must preserve `batch_id` and indexing patterns used for queries.
  - Payments modeling: payments store both QR PH fields and PayMongo identifiers (`paymongo_payment_id`, `paymongo_source_id`) and a `gateway_response` JSON field — treat these fields as canonical traces of gateway activity.
  - Webhooks: raw webhook payloads are saved in `payments.models.WebhookLog`. Use those records to debug processing and to avoid re-fetching external payloads.
  - Model `save()` overrides are used for business logic (e.g., auto-calculation of totals in `BatchRegistration.save()` and `User.save()` username auto-generation). Avoid duplicating logic; prefer calling model methods or signals where present.

- Environment / config details to reference when editing or running code:
  - Use `boyscout_system/settings.example.py` as the config reference. Secrets and gateway keys are read from environment variables (e.g. `PAYMONGO_SECRET_KEY`, `TWILIO_AUTH_TOKEN`).
  - Default dev channel layer is `InMemoryChannelLayer` (good for tests/dev). For production, the README and settings suggest configuring Redis.
  - Static/media paths are configured: `STATICFILES_DIRS`, `STATIC_ROOT`, `MEDIA_ROOT` — use these paths when writing file-handling code or tests.

- Developer workflows (how to run/build/test locally):
  - Create a virtualenv and install dependencies: `pip install -r requirements.txt` (requirements file at repo root).
  - Copy environment template and set secrets: copy `.env.example` -> `.env` and set `SECRET_KEY`, `EMAIL_*`, `PAYMONGO_*`, `TWILIO_*` as needed.
  - Run migrations: `python manage.py migrate`. A VS Code task exists named "Django makemigrations and migrate" (workspace task) if you prefer a task runner.
  - Run dev server (HTTP): `python manage.py runserver` (Channels-aware ASGI server is wired; for production or websocket testing use an ASGI server such as Daphne and configure `CHANNEL_LAYERS`).
  - Tests: there are many top-level `test_*.py` files and per-app `tests.py`. You can run tests with `python manage.py test` or `pytest` if installed. NOTE: some tests interact with email/SMS providers — set env vars to safe values or skip network tests when running in CI.

- Files you should inspect for behavioral examples or to follow existing code style:
  - `accounts/models.py` — custom user behavior, registration fee defaults (500.00), username auto-generation.
  - `payments/models.py` — Payment, PaymentQRCode, WebhookLog fields and save() behavior.
  - `payments/templates/payments/payment_verify.html` — canonical admin UI for marking payments verified/rejected.
  - `boyscout_system/settings.example.py` — provides env var names and default dev config (channels, email, twilio, paymongo).
  - `manage.py` — standard Django entrypoint.

- Safety notes for automated edits or tests:
  - Tests and helper scripts may send emails or SMS (see `test_notifications.py`, `test_twilio_api.py`). Avoid committing changes that would run against production credentials. Prefer mocking external calls or set env vars to interceptors.
  - When changing models, always add migration files (use `python manage.py makemigrations`) and keep migrations simple and reversible.

- Example-guided tasks (how to implement common changes):
  - To add a new payment gateway field: add the field to `payments/models.py` and include it in `Payment`'s `gateway_response` if possible; run `makemigrations` and `migrate`. Update any webhook processing that writes to `WebhookLog`.
  - To extend user registration logic: update `accounts/models.py` methods like `update_registration_status()` or `save()` to preserve existing behavior (admins always active; `registration_total_paid` semantics are used widely).

If anything here is unclear or you'd like additional examples (for instance, a walkthrough of the PayMongo webhook flow or the batch-registration import flow), tell me which area to expand and I will iterate.
