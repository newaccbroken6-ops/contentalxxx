# SpammerX — Dashboard & API Server (Standalone Hosting)

Pacchetto completo, indipendente e pronto per essere hostato ovunque (VPS, Render, Railway, Vercel, Docker, o PC locale).

---

## 📁 File Inclusi
- `app.py`: Server Flask completo con tutte le API, database locale e ponte verso Auth esterno.
- `index.html`: Dashboard moderna, responsive e dark-mode con:
  - Login 3-Factor (Username, Password, License Key).
  - Salvataggio automatico delle credenziali nel browser.
  - Gestione target isolata per account con pulsante **Stop / Avvia** e **Elimina**.
  - Monitoraggio in tempo reale, logs terminale e gestione licenze admin.
- `database.json`: Database locale persistente JSON per account e target.
- `requirements.txt`: Dipendenze Python (`Flask`, `requests`, `gunicorn`).
- `Procfile`: Configurazione pronta per Render / Railway / Heroku.
- `Dockerfile`: Per eseguire o hostare in container Docker.
- `vercel.json`: Per deploy istantaneo su Vercel.

---

## 🚀 Come Hostare

### Opzione 1: Su PC Locale / VPS (Linux, Windows, Mac)
1. Installa i requisiti:
   ```bash
   pip install -r requirements.txt
   ```
2. Avvia il server:
   ```bash
   python app.py
   ```
3. Apri il browser su:
   ```
   http://localhost:5986
   ```

---

### Opzione 2: Su Render (Gratis 24/7)
1. Crea un repository GitHub con i file di questa cartella (`HOST_DASHBOARD`).
2. Vai su [Render.com](https://render.com) e crea un **New Web Service**.
3. Collega il repo GitHub.
4. Render rileva automaticamente il file `Procfile` e `requirements.txt`.
5. Clicca su **Deploy**!

---

### Opzione 3: Su Vercel
1. Installa Vercel CLI:
   ```bash
   npm i -g vercel
   ```
2. Dalla cartella `HOST_DASHBOARD`, esegui:
   ```bash
   vercel --prod
   ```

---

### Opzione 4: Con Docker
1. Costruisci l'immagine:
   ```bash
   docker build -t spammerx-dashboard .
   ```
2. Avvia il container:
   ```bash
   docker run -d -p 5986:5986 -v $(pwd)/database.json:/app/database.json --name spammerx spammerx-dashboard
   ```

---

## 🔑 Credenziali Master Admin Predefinite
- **Username**: `Linux X Mrx`
- **Password**: `Linux X Mrx`
- **License Key**: `LINUX-MRX-LIFETIME`
