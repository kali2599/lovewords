# Lovewords — brief del prodotto MVP

## Obiettivo
Aiutare le persone ad arricchire il proprio vocabolario italiano con brevi giochi logici basati su parole e significati. Il sito e tutti i contenuti sono in italiano: non si usano traduzioni né un'altra lingua come supporto.

## Utenti e ipotesi iniziali
- Persone che vogliono imparare e usare nuove parole italiane, da computer o telefono.
- La prima versione è utilizzabile senza account e non salva i progressi tra sessioni.
- Parole, definizioni, frasi e indizi sono scritti in italiano.

## Esperienza principale
1. L'utente sceglie uno dei tre livelli: **Facile**, **Medio** o **Difficile**.
2. Sceglie uno dei quattro giochi disponibili.
3. Risolve tre brevi esercizi e riceve un riscontro immediato, con una definizione o un esempio quando utile.
4. Alla fine vede il punteggio della sessione.

## Giochi
- **Componi la frase:** riordina le tessere per formare una frase sensata che usa la parola proposta.
- **Cruciverba lampo:** indovina una parola italiana a partire da una definizione e inserisci le lettere. Nella demo è una parola per turno, senza incroci tra righe.
- **Sinonimi:** scegli la parola più vicina per significato alla parola proposta.
- **Completa la parola:** completa una parola italiana con lettere mancanti, usando una definizione come indizio.

## Progressione della difficoltà
- **Facile:** parole comuni, frasi brevi e indizi diretti.
- **Medio:** parole meno frequenti e indizi che richiedono di ragionare sul contesto.
- **Difficile:** parole più ricercate, frasi articolate e definizioni più sfumate.
- Ogni livello ha contenuti propri e non cambia lingua o modalità di gioco.

## Perimetro del prototipo
- Applicazione web responsive Flask, con quattro attività e tre livelli.
- Contenuti iniziali scritti a mano e feedback immediato.
- Registrazione con username univoco, email e password; accesso e gestione delle sessioni.
- Salvataggio SQL di punteggio, livello, attività, durata e data di ogni partita completata.
- Pagina personale con riepilogo e storico; account admin creati via script, con accesso ai dati degli utenti e reset password forzato al successivo accesso.

## Da verificare dopo il prototipo
- Adeguatezza delle parole e delle definizioni ai diversi livelli.
- Chiarezza e varietà degli esercizi, utilità degli esempi e motivazione a continuare.
- Necessità di ripasso dilazionato, gestione dei contenuti e politiche di conservazione/cancellazione dei dati.

## Segnali di successo
- Una persona riesce a scegliere il livello, capire i giochi e completare una sessione senza aiuto.
- Dopo aver giocato, ricorda il significato di alcune parole nuove e vuole continuare.
