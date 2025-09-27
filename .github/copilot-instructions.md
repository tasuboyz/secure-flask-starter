# Piano: Miglioramento Interfaccia Login e Sezioni di Accesso

Questo documento descrive un piano pratico e mobile-first per migliorare l'interfaccia di login e le pagine di accesso correlate (registrazione, recupero password, gestione sessione, integrazione SSO/MFA) per l'app "Calendar AI Dashboard".

Obiettivi principali

- Migliorare l'usabilità su mobile (mobile-first), accessibilità e sicurezza dell'esperienza di autenticazione.
- Ridurre i punti di attrito (login, registrazione, reset password) e aumentare il tasso di conversione utente.
- Mantenere compatibilità con le attuali protezioni server-side (CSRF, rate-limiting) e integrare SSO/2FA come opzioni progressive.

Contesto e principi guida

- Mobile-first: progettare layout e flussi a partire da viewport strette (3600-420px). Utilizzare pattern di input grandi per il touch, etichette chiare, e posizionare le azioni primarie in basso o al centro per facile accesso con il pollice.
- Accessibilità: rispettare WCAG 2.1 AA per colori, contrasto, focus states, etichette aria e navigazione via tastiera.
- Sicurezza: conservare CSRF token nelle form (gi

# Project tree for C:\Temp\secure-flask-starter
Generated: 2025-09-27 17:43:36

```
|- .github
|  |- copilot-instructions.md
|  - copilot-new-objective.md
|- app
|  |- auth
|  |  |- templates
|  |  |  |- forgot_password.html
|  |  |  |- login.html
|  |  |  |- register.html
|  |  |  - reset_password.html
|  |  |- __init__.py
|  |  |- email_utils.py
|  |  |- forms.py
|  |  - routes.py
|  |- calendar
|  |  - __init__.py
|  |- scripts
|  |  |- create_admin.py
|  |  - generate_secrets.py
|  |- services
|  |  |- calendar_service.py
|  |  |- google_client.py
|  |  - google_token.py
|  |- settings
|  |  |- templates
|  |  |  - settings
|  |  |      |- ai_assistant.html
|  |  |      |- index.html
|  |  |      - profile.html
|  |  |- __init__.py
|  |  |- forms.py
|  |  - routes.py
|  |- static
|  |  - css
|  |      - style.css
|  |- templates
|  |  |- base.html
|  |  |- dashboard.html
|  |  - index.html
|  |- __init__.py
|  |- ai_assistant.py
|  |- config.py
|  |- extensions.py
|  |- google_calendar.py
|  |- models.py
|  |- routes.py
|  - supabase.py
|- deploy
|  |- gunicorn.service
|  - nginx.conf
|- docs
|  |- calendar_ui_mission.md
|  |- google_auth_setup.md
|  |- google_calendar_assistant.md
|  |- gunicorn.md
|  |- login_ui_mission.md
|  |- production_setup.md
|  |- project_ideas.md
|  - project_structure.md
|- instance
|  - app.db
|- migrations
|  |- versions
|  |  |- 4d53b6a79454_add_ai_assistant_settings_fields.py
|  |  |- 5c69053ed761_add_ai_assistant_settings_with_defaults.py
|  |  |- 6a1b2c3d4e5f_add_google_permission_mode.py
|  |  - cabd280c39d5_initial_migration_sqlite.py
|  |- alembic.ini
|  |- env.py
|  |- README
|  - script.py.mako
|- scripts
|  |- generate_project_tree.ps1
|  |- sanity_tz_test.py
|  |- simulate_create_event.py
|  - tz_behavior_test.py
|- tests
|  |- conftest.py
|  |- test_ai_assistant.py
|  |- test_ai_tool_calls.py
|  |- test_auth.py
|  |- test_chat.py
|  |- test_google_auth.py
|  |- test_google_calendar.py
|  |- test_models.py
|  - test_services_token_and_client.py
|- .env
|- .env.example
|- .gitignore
|- client_secret_2_561100162372-ht8ckkdi5le51ptf235lbi1rulu36kd0.apps.googleusercontent.com.json
|- docker-compose.prod.yml
|- docker-compose.yml
|- Dockerfile
|- Dockerfile.prod
|- gunicorn_config.py
|- PROJECT_TREE.md
|- pytest.ini
|- README.md
|- requirements.txt
|- run.py
- run_dev.py
```
