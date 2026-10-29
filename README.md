# Parolario

Applicazione web Flask per arricchire il vocabolario italiano attraverso giochi di parole. L'interfaccia e tutti gli esercizi sono in italiano.

## Avvio in locale

Serve Python 3.10 o superiore. Dalla cartella del progetto crea un ambiente virtuale, installa Flask e avvia l'applicazione:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Apri quindi `http://127.0.0.1:5000` nel browser.

Al primo avvio vengono creati automaticamente il database e una chiave di sessione locale nella cartella `instance/`.

## Account e progressi

- Gli utenti si registrano da **Registrati** con username, email e password. Lo username è univoco, viene mostrato nell’interfaccia e si usa per accedere.
- Le password vengono memorizzate come hash; le sessioni usano cookie `HttpOnly` e protezione CSRF sui moduli.
- Le partite completate vengono salvate in SQLite. Ogni utente vede solo il proprio riepilogo e tutto il proprio storico.
- Vengono salvati gioco, livello, punteggio, durata e data, non le risposte inserite. Il punteggio è calcolato dal browser e serve come riepilogo personale; non è un risultato certificato contro manomissioni.
- Il database predefinito è `instance/parolario.sqlite3`. Per cambiarlo, imposta `PAROLARIO_DATABASE` prima di avviare l'app.

## Creare un amministratore

Non esiste una registrazione admin pubblica. Avvia lo script dalla cartella del progetto; username ed email sono richiesti nel terminale, mentre la password viene richiesta in modo nascosto e non va passata come argomento:

```sh
.venv/bin/python scripts/create_admin.py
```

L'amministratore accede dalla normale pagina di accesso e trova **Amministrazione** nel menu. Può consultare gli account normali e le loro partite, e impostare una password temporanea. La password temporanea va comunicata all'utente in modo sicuro; al successivo accesso l'utente deve cambiarla.

## Pubblicazione

Per un ambiente esposto in rete, configura una chiave segreta forte tramite `PAROLARIO_SECRET_KEY` e imposta `PAROLARIO_COOKIE_SECURE=1` dietro HTTPS. Il server integrato di Flask è destinato allo sviluppo: in produzione usa un server WSGI e un database/backup adeguati al volume e ai requisiti di conservazione.

## Contenuti della demo

- Tre livelli: facile, medio e difficile.
- Quattro giochi: componi la frase, cruciverba lampo, trova il sinonimo e completa la parola.
- Tre esercizi per ogni sessione, feedback e punteggio finale.
- In “Componi la frase” si può annullare l’ultima tessera inserita; in “Completa la parola” si inseriscono più lettere mancanti in sequenza.
- Parole, definizioni, frasi e indizi in italiano; nessuna traduzione.

## Struttura

- `app.py`: applicazione, autenticazione, API di salvataggio e route admin.
- `database.py`: schema SQLite e connessioni al database.
- `templates/index.html`: pagina HTML.
- `templates/auth.html`, `templates/progress.html`, `templates/admin_users.html`: account, storico e gestione utenti.
- `static/css/app.css`: stili.
- `static/js/app.js`: logica dei giochi e contenuti dimostrativi.
- `scripts/create_admin.py`: creazione protetta di un account amministratore.
- `requirements.txt`: dipendenze Python.
- `requirements.md`: requisiti e perimetro dell'MVP.

Flask gestisce gli account e salva nel database i riepiloghi delle partite; i giochi e i contenuti demo vengono gestiti nel browser. Lo storico registra gioco, livello, punteggio, durata e data, senza memorizzare le risposte inserite.
