# Servizio di Mailing — spec per integrazione

Questo documento descrive come integrare un servizio di mailing nel progetto `secure-flask-starter`.
Lo scopo è fornire una soluzione sicura, testabile in sviluppo e facilmente portabile in produzione.

Contenuti:
- Scelte architetturali (SMTP vs provider API)
- Contratto minimo/API della utility di invio
- Variabili d'ambiente richieste
- Implementazione suggerita (sincrona + asincrona)
- Worker background (RQ/Celery) — raccomandazioni
- Template email e test
- Produzione: deliverability, DKIM/SPF, rate-limiting
- Esempi rapidi di codice

---

## 1) Scelta architetturale (SMTP vs provider API)

Opzioni principali:
- SMTP diretto (Flask-Mail, smtplib): semplice, testabile in locale usando mailcatcher/SMTP debug server, ma meno robusto per deliverability.
- Provider API (SendGrid, Mailgun, Amazon SES, Postmark): migliore deliverability, tracking, gestione bounce; richiede integrazione HTTP/SDK e segreti API.

Raccomandazione:
- Supportare entrambi i metodi tramite una singola abstraction: `MAIL_PROVIDER = smtp|sendgrid|mailgun|ses`.
- In sviluppo preferire `smtp` con un SMTP di debug o `console` per evitare invii reali.

## 2) Contratto API (utility email)

Creare una utility con interfaccia minima e pulita: `app/email.py` o `app/utils/email.py`.

Funzioni principali:
- send_email(to, subject, template_name, context=None, html=None, cc=None, bcc=None, from_name=None)
  - Input: `to` (str o list), `subject` (str), `template_name` (per jinja2), `context` (dict) opzionale.
  - Output: booleano o oggetto risultato (provider response) — sollevare eccezione su errori critici.
  - Modalità: sincrona (default) + `send_email_async()` per invii in background.

- enqueue_email(...) — wrapper che mette il payload su una queue (RQ/Celery) per invio asincrono.

Error handling:
- Ritorna/logga errori non-blocking; per errori critici solleva exception configurabili.
- Ritenta automaticamente in worker (exponential backoff) per errori transitori.

Audit/logging:
- Log delle email inviate (livello debug/info). In produzione, evita di loggare contenuti sensibili.

## 3) Variabili d'ambiente richieste

Minimo (`.env`):

- MAIL_PROVIDER=smtp
- MAIL_SERVER=smtp.example.com
- MAIL_PORT=587
- MAIL_USE_TLS=True
- MAIL_USE_SSL=False
- MAIL_USERNAME=you@example.com
- MAIL_PASSWORD=super-secret
- MAIL_DEFAULT_SENDER=you@example.com
- MAIL_FROM_NAME="My App"

Per provider API (SendGrid/SES/Mailgun):
- MAIL_PROVIDER=sendgrid
- MAIL_API_KEY=SG.xxxxx
- MAIL_DEFAULT_SENDER=... (email)

Opzionali:
- MAIL_RATE_LIMIT=10/minute
- MAIL_QUEUE=redis://localhost:6379/0

## 4) Implementazione suggerita

File proposti:
- `app/email.py` — wrapper sync/async
- `app/extensions.py` — aggiungere eventuale client provider (es. sendgrid client) o lasciare lazy-init
- `scripts/worker.py` — worker RQ/Celery
- `tests/test_email.py` — unit tests

Esempio behavior in `app/email.py` (concetto):
- `render_template('emails/reset_password.html', **context)` per html body
- Se `MAIL_PROVIDER == 'smtp'`: usa `smtplib` o `flask-mail` per inviare
- Se `MAIL_PROVIDER == 'sendgrid'`: invoca l'API HTTP

Async options:
- A) RQ (semplice): usare Redis + rq; enqueue payload e worker con `rq worker`.
- B) Celery (più completo): usare Celery + Redis/RabbitMQ per retry/priority.
- C) Background thread (dev/low-volume): `threading.Thread(target=send_email, args=(...)).start()` — non consigliato in produzione.

Raccomandazione rapida: iniziare con RQ (facile da integrare, semplice da eseguire in container con Redis).

## 5) Template email e test

- Mettere template in `app/templates/emails/` (es. `reset_password.html`, `reset_password.txt`)
- Test: mockare provider/SMTP e verificare che `send_email()` sia chiamato con i parametri corretti.
- Test di integrazione con un SMTP debug server (es. Python `smtpd` o `mailtrap` sandbox).

## 6) Produzione: deliverability

- Usare provider dedicato per grandi volumi.
- Configurare SPF/DKIM/DMARC per il dominio mandante.
- Gestire bounce e complaint (webhook del provider).
- Rate limiting e retry.

## 7) Esempio rapido: `app/email.py` (bozza)

```python
# sketch (non nel file, qui per chiarezza)
from flask import current_app, render_template
from app.extensions import mail_client  # opzionale

def send_email(to, subject, template_name=None, context=None, html=None):
    # render body
    if template_name:
        html = render_template(f'emails/{template_name}.html', **(context or {}))
    # provider dispatch
    provider = current_app.config.get('MAIL_PROVIDER', 'smtp')
    if provider == 'smtp':
        # use smtplib or Flask-Mail
        pass
    elif provider == 'sendgrid':
        # call HTTP API
        pass

    return True
```

## 8) Runbook rapido (sviluppo)

- Dev: impostare `MAIL_PROVIDER=console` o `MAIL_PROVIDER=smtp` con `MAIL_SERVER=localhost` e usare `python -m smtpd -n -c DebuggingServer localhost:1025` per catturare le email.
- Worker dev: `rq worker default` (con REDIS_URL configurato).

## 9) Checklist di sicurezza

- Non loggare i messaggi/email in produzione.
- Proteggi le API keys in secret manager (Vault, Azure KeyVault, AWS Secrets Manager) in prod.
- Limita i destinatari per ambienti di test/dev.

---

Se vuoi, procedo ora a implementare la versione minima nel repository:
- `app/email.py` con supporto smtp + console
- Aggiornare `app/config.py` e `.env.example`
- Aggiungere un test base `tests/test_email.py`

Dimmi se procedo con l'implementazione automatica. Buono?