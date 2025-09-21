# Missione: Dashboard Calendar AI – UI e Flussi

Questa missione descrive come progettare e realizzare la UI del "Dashboard Calendar AI" che integra Google Calendar e un Assistente AI. È pensata per un team (o un agente) che deve capire cosa esiste già nel repo, cosa manca e quali passi concreti servono per arrivare a un risultato completo e testato.

## 1) Obiettivo e risultati attesi

- Un'unica dashboard con 3 aree:
  - Sidebar (navigazione)
  - Calendario centrale (vista mensile con eventi + azioni rapide)
  - Pannello destro (AI Assistant + riepiloghi eventi/tasks)
- Integrazione completa con Google Calendar:
  - Collegamento/ri-autorizzazione account Google
  - Lista eventi
  - Creazione evento
  - Ricerca slot liberi
- Chat con Assistente AI basata su OpenAI Responses API e tool-calling per creare eventi
- UX robusta: stati vuoti, errori (incluse mancanze di permessi), caricamenti, logging client
- Test minimi end-to-end sul flusso UI↔API (già molti test backend sono presenti)

## 2) Mappatura componenti già esistenti (repo)

- Template base e dashboard
  - `app/templates/base.html`: layout + meta CSRF
  - `app/templates/dashboard.html`: UI della dashboard (tabs: Panoramica, Calendario, AI Assistant, Settings)
  - `app/static/css/style.css`: stile moderno e responsive
- Backend Calendar (Blueprint)
  - `app/calendar/__init__.py` endpoint principali:
    - GET `/calendar/events` (per data singola) → `{ events: [...], date: ISO }`
    - GET `/calendar/events/range` → `{ events: [...], start_date, end_date }`
    - GET `/calendar/slots` → `{ slots: [...], start_date, end_date, duration_minutes }`
    - POST `/calendar/events` → `{ event: {...} }` (crea evento)
    - POST `/calendar/chat` → `{ response: str, timestamp: ISO }` (AI Assistant)
- Integrazione Google OAuth
  - `app/auth/routes.py`
    - `google_calendar_connect` → richiede scope calendar.events
    - `google_calendar_callback` → salva token/refresh
    - NUOVO: `google_calendar_reauthorize` → forza re-consent per risolvere ACCESS_TOKEN_SCOPE_INSUFFICIENT
- Integrazione Google Calendar
  - `app/google_calendar.py`
    - `get_events`, `create_event`, `find_available_slots`, `get_events_for_date`
    - `get_primary_calendar_timezone()` con gestione errori di permesso e fallback
- Assistente AI
  - `app/ai_assistant.py` → Responses API con tool-calling; usa timezone del calendario quando disponibile
- Settings
  - `app/settings/` (blueprint, forms, templates) → profilo, AI Assistant (API key, modello, lingua)
- Test
  - `tests/` copertura ampia: auth, calendar, AI tool calls, chat endpoint (CSRF bypass per test), ecc.

## 3) Gap da colmare (UI/API)

- Endpoint availability nel JS: il template usa `/calendar/availability` in alcune funzioni, mentre il backend espone `/calendar/slots` con parametri `start_date`, `end_date`, `duration`.
  - Azione: uniformare. Opzioni:
    1) Aggiornare il JS per chiamare `/calendar/slots?start_date=...&end_date=...&duration=...`
    2) Aggiungere alias backend `/calendar/availability` che proxy a `get_available_slots`
- Vista calendario mensile: in `dashboard.html` oggi mostriamo una lista eventi; manca una vera griglia mensile interattiva.
  - Azione: integrare una libreria (es. FullCalendar) o costruire una semplice griglia custom.
- Surfacing errori permesso Google (403 / scope insufficiente) nel frontend:
  - Azione: quando il backend rileva `permission_error`, includere nel JSON un hint e `reauthorize_url: /auth/google/calendar/reauthorize`, per mostrare un CTA lato UI.
- Modale "New Event": il pulsante è previsto nel design, ma serve una modale con form e validazione che colpisca `POST /calendar/events`.
- Tasks demo: la colonna destra mostra una checklist di esempio; se non si integra ancora una vera sorgente dati, mantenere dummy state locale con salvataggio in `localStorage` o dietro feature flag.

## 3b) Mobile-first e integrazione Telegram

- Mobile-first requirement:
  - Progetta e implementa i componenti UI a partire da una viewport stretta (36020-420px). Prioritizza i contenuti essenziali (calendario e chat rapida), pulsanti con target touch ampi e tipografia leggibile.
  - Il layout a tre colonne deve collassare su mobile in questo ordine: Sidebar (top o slide-in), Calendar (contenuto principale), AI panel (bottom/drawer). Usare drawer o off-canvas per sidebar/AI panel su mobile.
  - Acceptance: su viewport 375px larghezza le azioni principali (Nuovo evento, Invia messaggio) sono accessibili senza scroll orizzontale; elementi touch >=44px.

- Telegram integration (high-level):
  - Obiettivo: permettere agli utenti di chattare con l'assistente AI tramite Telegram e riutilizzare lo stesso backend `/calendar/chat`.
  - Componenti suggeriti:
    1. `app/integrations/telegram.py` (o `app/telegram.py`): gestisce webhook, verifica, mapping tra telegram_id e user_id, invio reply via Telegram Bot API.
    2. Webhook endpoint protetto: `/integrations/telegram/webhook/<secret>` (secret configurabile via env var `TELEGRAM_WEBHOOK_SECRET`) o valida il token nel body.
    3. Link/unlink UI: in Settings creare `/settings/integrations/telegram/link` che genera un OTP o deep-link (t.me/<bot>?start=LINK_TOKEN). L'utente completa il linking in Telegram che invia il token e riceve conferma.
    4. Message flow: quando arriva un update sul webhook, il server risolve il `telegram_id` -> `user` e chiama internamente il handler per `POST /calendar/chat` con il contesto utente; la risposta viene inoltrata al chat_id Telegram.
  - Env variables richieste:
    - `TELEGRAM_BOT_TOKEN` (obbligatorio)
    - `TELEGRAM_WEBHOOK_SECRET` (consigliato)
    - `TELEGRAM_HOST_URL` (per registrare webhook)
  - Security notes:
    - Conservare `TELEGRAM_BOT_TOKEN` come secret (env); non loggare il token.
    - Webhook endpoint deve validare HMAC/secret o il token incluso nella route.
    - Linking token/OTP deve scadere (es. 10 minuti) e limitare tentativi.
  - Acceptance criteria:
    - L'utente genera un link in Settings e completa il linking in Telegram; il backend associa `telegram_id` all'utente.
    - Messaggi inviati dal Telegram account linkato raggiungono `/calendar/chat` e le risposte tornano su Telegram.
    - I token sensibili non compaiono in log e le rotte webhook sono protette.

## 4) Contratti API minimi (per la UI)

- GET `/calendar/events?date=YYYY-MM-DD` → 200 `{ events: [ { id, summary, description?, start: {dateTime|date}, end: {dateTime|date} } ], date: ISO }`
- GET `/calendar/events/range?start_date=ISO&end_date=ISO` → 200 `{ events: [...], start_date, end_date }`
- GET `/calendar/slots?start_date=ISO&end_date=ISO&duration=30` → 200 `{ slots: [ { start: ISO, end: ISO } ], ... }`
- POST `/calendar/events` body `{ title, start_time: ISO, end_time: ISO, description?, attendees?: [email...] }` → 200 `{ event: {...} }`
- POST `/calendar/chat` body `{ message }` → 200 `{ response: string, timestamp: ISO }` | 4xx/5xx `{ error: string, calendar_permission_error?: bool, reauthorize_url?: str }`

Errori standardizzati: `{ error: string }` e quando possibile campi helper per UI (es. `reauthorize_url`).

## 5) Piano di implementazione (step-by-step)

Fase A – Allineamento backend/UI
1. Uniformare Availability
   - Aggiornare JS in `dashboard.html` per usare `/calendar/slots` con parametri `start_date`, `end_date`, `duration` (ISO). Oppure creare alias `/calendar/availability` nel blueprint.
   - Accettazione: click su "Verifica Disponibilità" mostra i primi slot con orario locale.
2. Surfacing permessi insufficienti
   - In `app/calendar/__init__.py` e/o in `app/google_calendar.py`, quando si individua `permission_error`, ritornare `{ error: 'Permessi insufficienti', calendar_permission_error: true, reauthorize_url: url_for('auth.google_calendar_reauthorize') }`.
   - Accettazione: il frontend mostra un messaggio con pulsante "Reautorizza" che porta alla route.

Fase B – UI Calendario mensile
3. Integrare FullCalendar (consigliato) o griglia custom
   - Aggiungere asset (CSS/JS) e un contenitore nel tab "Calendario".
   - Configurare "event source" puntando a `/calendar/events/range` per il periodo visualizzato.
   - Accettazione: navigazione mese, click su evento → tooltip/dettagli; oggi evidenziato; colori base.
4. Azioni rapide e modale "Nuovo evento"
   - Pulsante ➕ apre modale con form (titolo, data/ora inizio-fine, descrizione, invitati).
   - Submit → `POST /calendar/events`; alla risposta, chiudere modale e refresh eventi/calendario.
   - Accettazione: evento appare nel calendario; errori validati client-side e server-side.

Fase C – Pannello destro (AI + Riepilogo)
5. Chat AI robusta
   - Già esistente: invia a `/calendar/chat`; nel client loggiamo la risposta.
   - Aggiungere gestione di `calendar_permission_error` con CTA reauthorize.
   - Accettazione: prompt tipo "Cosa ho oggi?" restituisce testo coerente; in caso 403, UI guida alla reautorizzazione.
6. Today’s Events & Upcoming Tasks
   - Today’s Events: chiamare `/calendar/events?date=today` e mostrare elenco sintetico.
   - Upcoming Tasks: per ora, mock locale (toggle, persistenza in localStorage) o feature flag.
   - Accettazione: lista giornaliera leggibile; tasks spuntabili e persistenti localmente.

Fase D – Settings e stati
7. Settings
   - Confermare link e pagine: `settings/profile`, `settings/ai_assistant` (già presenti).
   - Aggiungere info stato Google Calendar: collegato/non collegato + link a `google_calendar_connect`/`google_calendar_reauthorize`.
   - Accettazione: lo stato riflette `user.google_calendar_connected`; la pagina AI mostra modello/lingua correnti.
8. Stati vuoti, loading, errori
   - Inserire skeleton/placeholder nelle liste.
   - Standardizzare alert/toast per errori.
   - Accettazione: nessun errore JS; tutti i percorsi mostrano uno stato gestito.

## 6) Design/UX note
- Colori evento suggestivi (verde/arancione/viola) per categorie; opzionale, mappare a `event.color` se disponibile.
- Evidenziare il giorno corrente.
- Accessibilità: contrasti, focus state, tasti rapidi per modale.

## 7) Test e verifica
- Lato backend: suite `pytest` già copre auth, calendar e AI; aggiungere test per la nuova risposta con `calendar_permission_error` se implementata.
- Lato frontend: smoke test manuale su
  - Carica eventi
  - Verifica disponibilità
  - Crea evento
  - Chat (risposte e errori)
  - Reautorizzazione

## 8) Accettazione (checklist)
- [ ] Calendario mensile interattivo con eventi caricati dal backend
- [ ] Modale "Nuovo evento" funzionante
- [ ] Ricerca slot liberi funzionante e coerente con parametri/endpoint
- [ ] Chat AI operativa, con gestione errori/scopes e CTA reauthorize
- [ ] Settings mostrano stato Google/AI e link corretti
- [ ] Nessun errore JS in console; API risposte JSON consistenti

## 9) Riferimenti rapidi (file utili)
- UI: `app/templates/dashboard.html`, `app/templates/base.html`, `app/static/css/style.css`
- Calendar API: `app/calendar/__init__.py`, `app/google_calendar.py`
- Auth/OAuth: `app/auth/routes.py`
- Settings: `app/settings/*`
- AI: `app/ai_assistant.py`

---
Suggerimento: se vuoi la griglia mensile in tempi rapidi, integra FullCalendar. In alternativa, puoi iniziare con la lista eventi come in `dashboard.html` e iterare verso la griglia.
