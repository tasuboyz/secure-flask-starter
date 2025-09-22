# Nuovo Obiettivo Copilot: Reautorizzazione Google Calendar (Full) + Modularizzazione

Obiettivo sintetico
- Implementare un flusso di reautorizzazione che permetta all'utente di concedere "Accesso completo" (`https://www.googleapis.com/auth/calendar`) al Calendar, risolvendo i problemi `ACCESS_TOKEN_SCOPE_INSUFFICIENT`, e avviare una prima fase di modularizzazione del codice Google Calendar per separare token management, HTTP client e logica di dominio.

Perché è importante
- Risolve il problema ricorrente di `PERMISSION_DENIED / ACCESS_TOKEN_SCOPE_INSUFFICIENT` emerso nei log.
- Migliora testabilità e manutenzione isolando la logica OAuth/HTTP dal dominio calendar e dall'assistente AI.

Ambito minimo richiesto (MVP)
1. Forzare e rendere facilmente accessibile una reautorizzazione in modalità `full`:
   - Backend: route `auth.google_calendar_reauthorize` già esistente deve garantire `scope=https://www.googleapis.com/auth/calendar`, `access_type=offline`, `prompt=consent`, `include_granted_scopes=true` e revocare il refresh token precedente prima del redirect.
   - Frontend: nel template Dashboard aggiungere pulsante chiaro "Riautorizza (Full)" che apre la route con `?mode=full`.
2. Introdurre moduli di servizio separati (PoC):
   - `app/services/google_token.py` (TokenManager: refresh/revoke/ensure)
   - `app/services/google_client.py` (GoogleCalendarClient: request/raise-permission-error)
   - Aggiornare `app/google_calendar.py` per usare i nuovi servizi (ad interim import shim è accettabile).
3. Documentazione e test:
   - Aggiungere test unitari per TokenManager (mock `requests.post`) e per GoogleCalendarClient (mock `requests.request` e scenari 200/403).
   - Aggiornare `.github/copilot-instructions.md` con l'obiettivo e la checklist.

Criteri di accettazione (Done quando)
- L'azione "Riautorizza (Full)" apre la schermata consent di Google e dopo la conferma l'utente ha `google_permission_mode == 'full'` in DB.
- Dopo la reautorizzazione, una chiamata che prima dava `ACCESS_TOKEN_SCOPE_INSUFFICIENT` (es. creare evento o leggere `calendars/primary`) non ritorna più 403 se l'utente ha concesso i permessi.
- Esistono test unitari per TokenManager e GoogleCalendarClient con coverage sul percorso di refresh e sul 403 handling.
- Non ci sono regressioni: test di integrazione esistenti rimangono verdi (o sono aggiornati con nuovi mocks).

Passi tecnici dettagliati (checklist eseguibile)
- [ ] Aggiungere file `app/services/google_token.py` con classe `TokenManager`:
  - `ensure_valid_token(user)`, `refresh(refresh_token)`, `revoke(token)`.
  - Usare `requests` con timeout e log.
- [ ] Aggiungere file `app/services/google_client.py` con classe `GoogleCalendarClient`:
  - `request(method, endpoint, access_token, params=None, json=None)` che costruisce `https://www.googleapis.com/calendar/v3/{endpoint}` e solleva `CalendarPermissionError` per 403 con `ACCESS_TOKEN_SCOPE_INSUFFICIENT`.
- [ ] Integrare i servizi nel codice esistente:
  - Sostituire chiamate dirette a `ensure_valid_token` e `make_calendar_request` con l'uso dei nuovi servizi (PoC: mantenere wrapper in `app/google_calendar.py` fino alla migrazione completa).
- [ ] Aggiornare `auth.routes` per default a `mode=full` e aggiungere pulsante "Riautorizza (Full)" nel template `dashboard.html`.
- [ ] Aggiungere migration Alembic se necessario per campi utente (già presente `google_permission_mode`).
- [ ] Scrivere unit tests in `tests/services/` e integrarli nella CI.

Test minimalmente richiesti
- TokenManager: refresh success, refresh failure, missing refresh token.
- GoogleCalendarClient: 200 OK passthrough, 403 raises CalendarPermissionError with parsed body.
- Integration smoke: simulate AI tool call that triggers CalendarPermissionError and verify response contains `calendar_permission_error` and `reauthorize_url`.

Rollout e rollback
- Rollout progressivo: aprire PR per TokenManager (PoC) che include i test; dopo approvazione, aprire PR per GoogleCalendarClient; infine aggiornare `app/google_calendar.py` e i blueprint.
- Rollback: ogni PR include un shim che re-esporta la vecchia API e non rompe i consumer fino al merge finale.

Stima tempi (indicativa)
- PoC TokenManager + tests: 3–6 ore
- GoogleCalendarClient + tests: 3–6 ore
- CalendarService extract + wiring blueprint: 1–2 giorni

Snippet da inserire in `.github/copilot-instructions.md`
> Nuovo obiettivo: Implementare reautorizzazione "full" per Google Calendar e avviare modularizzazione del client Google.
> - Acceptance: consent screen forzato + DB persisted `google_permission_mode='full'` + tests per TokenManager/Client.

Note operative per il reviewer
- Verificare che i test mockino `requests` e che non siano eseguite chiamate di rete reali nel job CI.
- Assicurarsi che i moduli estratti esportino interfacce semplici (consumabili anche dai vecchi wrapper) per facilitare la migrazione in più PR.

-----

File di output suggerito per copia/incolla in `.github/copilot-instructions.md`:

```md
### Obiettivo prioritario: Reautorizzazione Google Calendar (Full) + Modularizzazione
- Scopo: forzare la re-consent per `https://www.googleapis.com/auth/calendar` e separare token management / HTTP client / business logic del calendario in servizi testabili.
- Acceptance: consent screen shown, `google_permission_mode='full'` persisted, 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT` risolto dopo reauth; unit tests per TokenManager e GoogleClient.
```

---

Se vuoi, procedo ora con l'implementazione del PoC `TokenManager` (opzione A). Dimmi se procedo e lo creo direttamente in `app/services/` con i test di base.