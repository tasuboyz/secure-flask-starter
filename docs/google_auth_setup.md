# Integrazione Google Sign-In (server-side) - Guida passo-passo

Questa guida spiega come integrare Google Sign‑In (OAuth2 / OpenID Connect) nella tua app `secure-flask-starter`, usando la porta 5000 per lo sviluppo. Copre sia il backend (Flask + Authlib) sia le modifiche frontend/template necessarie.

Indice
- Prerequisiti
- Config e variabili d'ambiente
- Backend: dipendenze e modifiche (estensioni, config, modello, migrazione, routes)
- Frontend / templates: pulsante login e redirect
- Test e verifiche
- Sicurezza e pulizia (rimuovere file di credenziali dal repo)

---

Prerequisiti
- Avere un progetto Google Cloud con un OAuth client (tipo "Web application").
- Redirect URI da registrare: `http://127.0.0.1:5000/auth/google/callback` e `http://localhost:5000/auth/google/callback`.
- Ambiente virtuale attivo e repository clonato.

Installare dipendenze

Esegui (PowerShell):

```powershell
.venv\Scripts\pip install authlib
```

Config e variabili d'ambiente

- Aggiungi le seguenti variabili nel file `.env` (non committare) o nel tuo environment:

```
GOOGLE_CLIENT_ID=561100162372-...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

- Assicurati che `app/config.py` legga queste variabili (il progetto carica già dotenv). Aggiungi se non presente:

```python
# app/config.py
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
```

Backend: modifiche richieste

1) Estensioni: aggiungi Authlib

- Modifica `app/extensions.py` per esporre l'oggetto OAuth:

```python
from authlib.integrations.flask_client import OAuth

# ... esistenti ...
oauth = OAuth()
```

2) Inizializzazione: registra il provider Google

- In `app/__init__.py`, subito dopo `mail.init_app(app)` inizializza `oauth` e registra Google:

```python
from app.extensions import oauth

oauth.init_app(app)
oauth.register(
    name='google',
    client_id=app.config.get('GOOGLE_CLIENT_ID'),
    client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)
```

3) Modifica `User` model

- Aggiungi `google_id` per collegare l'account Google al record utente:

```python
# app/models.py
google_id = Column(String(255), unique=True, index=True, nullable=True)
```

- Genera migrazione e applicala (preferibile) oppure in dev usare `db.create_all()`:

```powershell
set FLASK_APP=run.py
set FLASK_ENV=development
.venv\Scripts\flask db migrate -m "Add google_id to user"
.venv\Scripts\flask db upgrade
```

4) Routes OAuth

- Aggiungi due route nel blueprint `app/auth/routes.py` (o crea un file `oauth.py` nello stesso blueprint). Esempio di implementazione:

```python
from flask import url_for, redirect, flash
from app.extensions import oauth, db
from app.models import User
from flask_login import login_user
import secrets
from datetime import datetime

@bp.route('/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@bp.route('/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    try:
        userinfo = oauth.google.parse_id_token(token)
    except Exception:
        resp = oauth.google.get('oauth2/v2/userinfo')
        userinfo = resp.json()

    if not userinfo.get('email') or not userinfo.get('email_verified'):
        flash('Google account email non verificata', 'danger')
        return redirect(url_for('auth.login'))

    email = userinfo['email'].lower()
    google_sub = userinfo.get('sub')

    user = None
    if google_sub:
        user = User.query.filter_by(google_id=google_sub).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            # associa l'account locale
            user.google_id = google_sub
        else:
            # crea nuovo utente
            user = User(email=email, google_id=google_sub)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    login_user(user)
    flash('Accesso con Google eseguito', 'success')
    return redirect(url_for('dashboard.index'))
```

5) Agganciare il pulsante di login nel template

- Nel template di login (`app/auth/templates/login.html`) aggiungi un pulsante/link che punti a `/auth/google`:

```html
<a class="btn btn-outline-primary" href="{{ url_for('auth.google_login') }}">
  Accedi con Google
</a>
```

Frontend: dettagli UX e redirect

- Comportamento atteso:
  - Utente clicca "Accedi con Google" → viene rediretto alla pagina di consenso Google.
  - Dopo consenso Google redirige a `/auth/google/callback` con il codice.
  - Server scambia il codice per token, ottiene id_token/userinfo e autentica/crea utente.

- Se vuoi una UX SPA, puoi aprire il flusso in una popup e chiudere la popup alla fine; per ora il redirect full-page è il più semplice.

Test e verifiche

- Test unitari: patchare `oauth.google.authorize_access_token()` e `oauth.google.get()` per simulare userinfo e verificare i seguenti casi:
  - Nuovo utente creato correttamente
  - Utente esistente con stesso email associato a google_id
  - Email non verificata → rifiuto

- Test manuale (dev):
  1. Imposta env vars nel `.env`.
  2. Avvia l'app: `python run_dev.py` (porta 5000).
  3. Apri `http://127.0.0.1:5000/auth/google`.

Sicurezza e operazioni post-setup

- Rimuovi il file JSON di credenziali dal repo (se presente). Se è già pubblico, rigenera il `client_secret` nella Google Console.
- Non salvare client secret in repo. Usa `.env` ignorato da git.
- Verifica `email_verified` prima di creare account in automatico.
- Non impostare `is_admin=True` per account OAuth creati automaticamente.

Pulizia del repo (passi consigliati)

```powershell
# rimuove il file dal controllo versione (ma lo lascia localmente)
 git rm --cached client_secret_*.json
 # aggiungi pattern al .gitignore
 Add-Content .gitignore "client_secret_*.json"
 git commit -m "Remove oauth client secret json from repo and ignore"
```

Domande opzionali da decidere
- Vuoi che un utente locale possa collegare/disconnettere il suo Google account da `Account settings`?
- Vuoi salvare access/refresh token per chiamate Google API? (se sì, cifrarli in DB o usare secret store)

---

Se vuoi, posso applicare io le modifiche: aggiungere `oauth` in `app/extensions.py`, registrare provider in `app/__init__.py`, aggiungere `google_id` al modello e creare una migrazione + implementare le route nell'`auth` blueprint e modificare il template di login. Dimmi se procedo con la patch completa.

## Troubleshooting

### Errore "Missing jwks_uri in metadata"

Se vedi questo errore nei log:
```
ERROR in routes: Google OAuth error: Missing "jwks_uri" in metadata
```

Assicurati di usare `server_metadata_url` invece di specificare manualmente gli endpoint:
```python
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    # ... altri parametri
)
```

### Redirect URI non registrato

Se vedi errore "redirect_uri_mismatch", verifica che nel Google Cloud Console:
1. Vai a Credentials → OAuth 2.0 Client IDs → [Il tuo client]
2. Authorized redirect URIs include esattamente:
   - `http://127.0.0.1:5000/auth/google/callback`
   - `http://localhost:5000/auth/google/callback`

### Database "no such column: google_id"

Se l'app si lamenta della colonna mancante:
1. Elimina `instance/app.db` 
2. Riavvia `run_dev.py` (ricrea il DB automaticamente)
3. Oppure usa migration: `flask db migrate && flask db upgrade`
