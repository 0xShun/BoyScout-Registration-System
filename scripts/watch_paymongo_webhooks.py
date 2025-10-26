#!/usr/bin/env python3
"""
Lightweight watcher to monitor ngrok HTTP requests and local sqlite DB registration payments.
Run while you replay a PayMongo checkout; it will print new incoming webhook requests and recent
RegistrationPayment rows so we can confirm webhook arrival and DB updates.
"""
import requests
import sqlite3
import time
import json
import datetime
import os

NGROK_API = os.environ.get('NGROK_API', 'http://127.0.0.1:4040/api/requests/http')
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3'))
POLL_INTERVAL = 2.0

seen = set()
print(f"Starting watcher: ngrok_api={NGROK_API}, db={DB_PATH}")
print("Press Ctrl-C to stop")

while True:
    now = datetime.datetime.now().isoformat(timespec='seconds')
    try:
        resp = requests.get(NGROK_API, timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('requests', [])
            new_items = [it for it in items if it.get('id') not in seen]
            if new_items:
                print('\n' + '='*60)
                print(f"[{now}] New ngrok requests: {len(new_items)}")
            for it in reversed(new_items):
                rid = it.get('id')
                seen.add(rid)
                started = it.get('start_time')
                req = it.get('request', {})
                res = it.get('response', {})
                uri = req.get('url') or req.get('uri') or ''
                method = req.get('method')
                print('\n--- NGROK REQUEST')
                print(f"id={rid}  method={method}  uri={uri}  status={res.get('status')}")
                # try show content-type
                headers = req.get('headers') or {}
                if headers:
                    ct = headers.get('Content-Type') or headers.get('content-type')
                    if ct:
                        print(f"content-type: {ct}")
                body = req.get('body')
                if body:
                    b = body
                    # truncated
                    if isinstance(b, str) and len(b) > 1000:
                        b = b[:1000] + '...'
                    print('body:', b)
                    # try to parse JSON and show event type
                    try:
                        pj = json.loads(body)
                        typ = pj.get('data', {}).get('attributes', {}).get('type')
                        if typ:
                            print('-> event.type =', typ)
                        # attempt to show payment source id
                        pid = pj.get('data', {}).get('attributes', {}).get('data', {}).get('attributes', {}).get('source', {}).get('id')
                        if pid:
                            print('-> payment.source.id =', pid)
                    except Exception:
                        pass
        else:
            print(f"ngrok API returned status {resp.status_code}")
    except Exception as exc:
        print(f"ngrok poll error: {exc}")

    # Print recent RegistrationPayment rows
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, user_id, paymongo_source_id, paymongo_payment_id, status, created_at, updated_at FROM accounts_registrationpayment ORDER BY updated_at DESC LIMIT 10")
        rows = cur.fetchall()
        if rows:
            print('\nRecent RegistrationPayment rows:')
            for r in rows:
                print(f" id={r[0]} user_id={r[1]} source={r[2]} payment_id={r[3]} status={r[4]} updated_at={r[6]}")
        conn.close()
    except Exception as exc:
        print(f"DB query error: {exc}")

    time.sleep(POLL_INTERVAL)
