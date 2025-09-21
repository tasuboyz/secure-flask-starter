# Pro Project

Un'applicazione Flask sicura con autenticazione pronta per la produzione.

## Caratteristiche

- 🔒 **Sicurezza avanzata**: Hash delle password con Argon2, protezione CSRF, rate limiting
- ⚡ **Performance**: Ottimizzato per la produzione con PostgreSQL e Redis
- 🧪 **Testing**: Suite di test completa con pytest
- 🐳 **Docker**: Configurazione Docker per sviluppo e produzione
- 📧 **Email**: Sistema di reset password con Flask-Mail

## Architettura

- **Backend**: Python 3.11+ con Flask (application factory pattern)
- **Database**: SQLAlchemy con Flask-SQLAlchemy ORM, Alembic migrations
- **Autenticazione**: Flask-Login + supporto opzionale OAuth
- **Sicurezza**: Argon2 password hashing, Flask-WTF CSRF protection, flask-limiter
- **Email**: Flask-Mail per reset password
- **Testing**: pytest con fixture per app/database

## Setup Rapido

### 1. Clona e installa dipendenze

```bash
git clone <repository-url>
cd pro-project
pip install -r requirements.txt
```

### 2. Genera chiavi segrete

```bash
python app/scripts/generate_secrets.py
```

Copia l'output nel file `.env`:

```bash
cp .env.example .env
# Modifica .env con le chiavi generate
```

### 3. Setup Database

```bash
# Con Docker (raccomandato)
docker-compose up -d db redis

# Oppure installa PostgreSQL localmente
# Assicurati che DATABASE_URL in .env punti al tuo database
```

### 4. Inizializza Database

```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

#### Nota specifica per sviluppo (SQLite) vs produzione (Postgres)

- Per comodità in sviluppo il progetto usa SQLite quando `DATABASE_URL` non è impostata o punta a una stringa `sqlite:///...`.
- Se in `.env` hai una `DATABASE_URL` che punta a PostgreSQL (es. `postgresql://postgres:password@localhost:5432/proproject`) e il server Postgres non è attivo, i comandi `flask db migrate` e `flask db upgrade` falliranno con un errore di "connection refused" come visto durante la prima esecuzione.
- Per generare/applcare migrazioni usando SQLite (sviluppo locale) puoi impostare temporaneamente la variabile d'ambiente `DATABASE_URL` nella sessione PowerShell e poi lanciare i comandi di migration:

```powershell
# nella stessa sessione PowerShell (Windows)
set FLASK_APP=run.py
set DATABASE_URL=sqlite:///instance/app.db
flask db migrate -m "Initial migration (sqlite)"
flask db upgrade

# Il database SQLite verrà creato in `instance/app.db` (pattern Flask)
```

- Se preferisci usare Postgres (consigliato per produzione), avvia Postgres prima (locale o tramite `docker-compose up -d db`) e imposta `DATABASE_URL` correttamente. Poi esegui le migrazioni:

```powershell
# esempio con Postgres in esecuzione
set FLASK_APP=run.py
set DATABASE_URL=postgresql://postgres:password@localhost:5432/proproject
flask db migrate -m "Initial migration (postgres)"
flask db upgrade
```

- Dove si trova la migration generata? Alembic salva i file in `migrations/versions/` (es. `migrations/versions/cabd280c39d5_initial_migration_sqlite.py`). Controlla questo file se vuoi rivedere le tabelle create automaticamente.

- Suggerimento: per sviluppo rapido non è necessario Docker; basta usare SQLite come sopra. Per testare la migrazione verso Postgres, avvia Postgres (localmente o con Docker) prima di eseguire `flask db migrate`.

### 5. Crea utente admin

```bash
python app/scripts/create_admin.py
```

### 6. Avvia l'applicazione

```bash
# Sviluppo
set FLASK_ENV=development
python run.py

# Con Docker
docker-compose up

# L'app sarà disponibile su http://localhost:5000
```

## Sviluppo

### Struttura del progetto

```
app/
├── __init__.py          # Application factory
├── config.py           # Configurazioni per ambiente
├── extensions.py       # Estensioni globali
├── models.py          # Model User con sicurezza
├── routes.py          # Route principali
├── auth/              # Blueprint autenticazione
│   ├── routes.py      # Login/logout/password reset
│   ├── forms.py       # Form con validazione
│   ├── email_utils.py # Utilità email
│   └── templates/     # Template auth
├── templates/         # Template Jinja2
├── static/           # CSS/JS/immagini
└── scripts/          # Script di utilità
```

### Comandi utili

```bash
# Migrazioni database
flask db migrate -m "Descrizione"
flask db upgrade

# Test
pytest
pytest -v                    # Output verboso
pytest tests/test_auth.py    # Test specifici

# Genera nuove chiavi segrete
python app/scripts/generate_secrets.py

# Crea utente admin
python app/scripts/create_admin.py
```

### Variabili d'ambiente

Crea un file `.env` basato su `.env.example`:

```bash
# Sicurezza (OBBLIGATORIO CAMBIARE)
SECRET_KEY=your-32-byte-hex-key
SECURITY_PASSWORD_SALT=your-32-byte-hex-salt

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/proproject

# Email (per reset password)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Redis (opzionale per rate limiting)
REDIS_URL=redis://localhost:6379/0
```

## Sicurezza

### Features implementate

- **Password hashing**: Argon2 (primario) con fallback a PBKDF2
- **Tracking sicurezza**: `last_login_at`, `last_login_ip`, `last_password_change_at`
- **Gestione sessioni**: Flask-Login con cookie sicuri in produzione
- **Protezione CSRF**: Abilitata su tutte le form POST
- **Rate limiting**: Su route sensibili (login, reset password)
- **Token reset password**: Scadenza 1 ora con `itsdangerous`

### Configurazioni produzione

In produzione, assicurati di:

1. **Usare HTTPS**: Imposta `PREFERRED_URL_SCHEME=https`
2. **Cookie sicuri**: Automaticamente attivati in `ProductionConfig`
3. **Secret management**: Usa servizi come AWS Secrets Manager
4. **Database sicuro**: PostgreSQL con connessioni SSL
5. **Monitoring**: Integra Sentry per error tracking

## Testing

```bash
# Esegui tutti i test
pytest

# Test con coverage
pytest --cov=app

# Test specifici
pytest tests/test_models.py::test_user_password_hashing
```

### Test principali

- `test_models.py`: Test model User e sicurezza password
- `test_auth.py`: Test flussi di autenticazione completi
- `conftest.py`: Fixture per test con database temporaneo

## Deploy

### Docker

```bash
# Build immagine
docker build -t pro-project .

# Deploy con docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Variabili per produzione

```bash
FLASK_ENV=production
SECRET_KEY=<strong-secret-key>
DATABASE_URL=postgresql://...
MAIL_SERVER=...
```

### Running with Gunicorn (production)

For production deployments we recommend running the app with Gunicorn on a Linux host/container and put it behind a reverse proxy (Nginx). See `docs/gunicorn.md` for detailed instructions: systemd unit, Nginx example, Docker Compose snippet and recommended Gunicorn flags.


## Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/amazing-feature`)
3. Commit delle modifiche (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

## Licenza

Questo progetto è under MIT License - vedi il file [LICENSE](LICENSE) per dettagli.

## Supporto

Per domande o problemi:

1. Controlla la documentazione esistente
2. Cerca negli Issues GitHub
3. Apri un nuovo Issue con dettagli del problema

---

**⚠️ Importante**: Prima di andare in produzione, cambia tutte le chiavi segrete e configura un sistema di secret management appropriato!

## Google Calendar (opzionale)

Per collegare Google Calendar è necessario creare un OAuth Client nel
Google Cloud Console e abilitare le Google Calendar API per il progetto.

1. Vai su https://console.cloud.google.com/apis/credentials
2. Crea un "OAuth 2.0 Client ID" (Application type: Web application)
3. Aggiungi i Redirect URI usati dall'app, ad esempio:
	 - https://yourdomain/auth/google/callback
	 - https://yourdomain/auth/google/calendar/callback
	 (quando sviluppi in locale usa `http://127.0.0.1:5000` con run_dev/run.py)
4. Abilita l'API Google Calendar dal Library (https://console.cloud.google.com/apis/library)

Imposta le variabili d'ambiente (esempio `.env`):

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Uso in-app:

- Per login OAuth standard l'app richiede scope `openid email profile`.
- Per collegare il Google Calendar (per es. creare eventi) visita
	`/auth/google/calendar` mentre sei loggato: questo avvierà il flusso OAuth
	richiedendo il permesso `https://www.googleapis.com/auth/calendar.events`.

Note di sicurezza:
- I token di accesso e refresh vengono memorizzati nel database nel modello
	`User` (campi: `google_access_token`, `google_refresh_token`,
	`google_token_expires_at`). Proteggi il DB e non esporre questi campi nei log.