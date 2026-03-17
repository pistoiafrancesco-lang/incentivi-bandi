# Incentivi.gov.it — Scraper Giornaliero

Scarica automaticamente ogni mattina il dataset open data ufficiale di [incentivi.gov.it](https://www.incentivi.gov.it) (MIMIT) e salva i bandi in formato **JSON** e **CSV**, pronti per essere importati in un database.

## Come funziona

- Ogni giorno alle **08:00 ora italiana** GitHub Actions esegue lo script
- Lo script scarica il file CSV open data da `incentivi.gov.it`
- I file `incentivi_YYYY-MM-DD.json` e `incentivi_YYYY-MM-DD.csv` vengono salvati nel repository
- Puoi scaricarli manualmente o agganciarli con una webhook

## Struttura file output

| Campo | Descrizione |
|---|---|
| `id` | ID univoco incentivo |
| `titolo` | Nome del bando |
| `descrizione` | Descrizione estesa |
| `data_apertura` | Data apertura sportello |
| `data_chiusura` | Data scadenza |
| `ente` | Soggetto concedente |
| `forma_agevolazione` | Contributo, prestito, credito d'imposta... |
| `regioni` | Regioni ammesse |
| `codici_ateco` | Settori ATECO ammessi |
| `stanziamento` | Dotazione finanziaria (€) |
| `link` | URL scheda ufficiale |

## Filtri configurabili

Nel file `incentivi_scraper.py`, sezione `FILTRI`:

```python
FILTRI = {
    "regioni": ["Sicilia"],              # solo Sicilia
    "forma_agevolazione": None,          # tutte le forme
    "aperto_oggi": True,                 # solo bandi ancora aperti
}
```

## Avvio manuale

Dalla tab **Actions** su GitHub → seleziona il workflow → **Run workflow**.

## Licenza dati

I dati sono rilasciati da MIMIT con licenza [IODL 2.0](https://www.dati.gov.it/iodl/2.0/) — uso libero anche commerciale con obbligo di attribuzione.
