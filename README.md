# ScoutConnect (BoyScout Registration System)

This repo contains a Django application for managing Boy Scout registrations, payments, announcements, events, and notifications.

## Quick Start
- Create a virtual environment and install requirements.
- Copy `.env.example` to `.env` and fill in values.
- Run migrations and start the server.

## Security
- All secrets must be provided via environment variables (see `.env.example`).
- Test helper scripts read recipients/credentials from environment.

## Notable Folders
 
 ## Changes
 - Consolidated duplicate payment verification template: use `payments/templates/payments/payment_verify.html` across the app.
 - Added tests placeholder documentation note.
- `test_notifications.py` – sends a test email/SMS using configured backends.
- `test_twilio_api.py` – direct Twilio API checks. Use env vars, do not commit secrets.

## Development
- Use Django Channels ASGI for realtime notifications. For production, configure Redis channel layer.

## License
MIT