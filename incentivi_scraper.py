#!/usr/bin/env python3
"""
Scraper open data incentivi.gov.it
-----------------------------------
Scarica il CSV ufficiale pubblicato giornalmente da incentivi.gov.it
(licenza IODL 2.0 - uso libero e legale).

URL pattern: https://www.incentivi.gov.it/sites/default/files/open-data/YYYY-M-D_opendata-export.csv

Output: incentivi_YYYY-MM-DD.json  +  incentivi_YYYY-MM-DD.csv
"""

import requests
import csv
import json
import io
import sys
from datetime import date, timedelta

# ── Configurazione ────────────────────────────────────────────────────────────

BASE_URL = "https://www.incentivi.gov.it/sites/default/files/open-data"
MAX_DAYS_BACK = 30          # cerca fino a 30 giorni indietro se oggi non c'è ancora
OUTPUT_JSON = True
OUTPUT_CSV  = True
ENCODING    = "utf-8-sig"   # il file governativo usa BOM UTF-8

# Filtri opzionali (lascia None per prendere tutto)
FILTRI = {
    "regioni": None,             # es. ["Sicilia"] — filtra per regione
    "forma_agevolazione": None,  # es. ["Contributo/Fondo perduto"]
    "aperto_oggi": False,        # True = solo bandi con Data_chiusura >= oggi o vuota
}

# ── Mappa colonne CSV → chiavi JSON output ────────────────────────────────────

COLUMN_MAP = {
    "ID_Incentivo":              "id",
    "Titolo":                    "titolo",
    "Descrizione":               "descrizione",
    "Obiettivo_Finalita":        "obiettivo",
    "Data_apertura":             "data_apertura",
    "Data_chiusura":             "data_chiusura",
    "Note_di_apertura_chiusura": "note_date",
    "Dimensioni":                "dimensioni_impresa",
    "Tipologia_Soggetto":        "tipologia_soggetto",
    "Forma_agevolazione":        "forma_agevolazione",
    "Costi_Ammessi":             "costi_ammessi",
    "Spesa_Ammessa_min":         "spesa_min",
    "Spesa_Ammessa_max":         "spesa_max",
    "Agevolazione_Concedibile_min": "agevolazione_min",
    "Agevolazione_Concedibile_max": "agevolazione_max",
    "Settore_Attivita":          "settore",
    "Codici_ATECO":              "codici_ateco",
    "Regioni":                   "regioni",
    "Comuni":                    "comuni",
    "Ambito_territoriale":       "ambito_territoriale",
    "Soggetto_Concedente":       "ente",
    "Base_normativa_primaria":   "normativa_primaria",
    "Stanziamento_incentivo":    "stanziamento",
    "Link_istituzionale":        "link",
    "Data_ultimo_aggiornamento": "aggiornato_il",
}


# ── Funzioni ──────────────────────────────────────────────────────────────────

def build_url(d: date) -> str:
    """Costruisce l'URL per una data specifica (senza zero-padding nel giorno/mese)."""
    return f"{BASE_URL}/{d.year}-{d.month}-{d.day}_opendata-export.csv"


def fetch_latest_csv() -> tuple[str, date]:
    """
    Cerca il file CSV più recente disponibile, partendo da oggi
    e andando indietro fino a MAX_DAYS_BACK giorni.
    Ritorna (contenuto_csv_testo, data_file).
    """
    today = date.today()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (IncentiviBotOpenData/1.0)"})

    for delta in range(MAX_DAYS_BACK + 1):
        d = today - timedelta(days=delta)
        url = build_url(d)
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 500:
                print(f"✓ File trovato: {url}")
                return resp.content.decode(ENCODING, errors="replace"), d
            else:
                print(f"  {d} → {resp.status_code}, provo data precedente...")
        except requests.RequestException as e:
            print(f"  {d} → errore rete: {e}")

    raise RuntimeError(f"Nessun file trovato negli ultimi {MAX_DAYS_BACK} giorni.")


def parse_csv(raw: str) -> list[dict]:
    """Parsa il CSV e restituisce una lista di dizionari con chiavi rinominate."""
    reader = csv.DictReader(io.StringIO(raw))
    rows = []
    for row in reader:
        record = {}
        for col_csv, col_json in COLUMN_MAP.items():
            record[col_json] = row.get(col_csv, "").strip()
        # Aggiungi eventuali colonne non mappate con il nome originale
        for k, v in row.items():
            if k not in COLUMN_MAP:
                record[k.lower()] = v.strip()
        rows.append(record)
    return rows


def apply_filters(rows: list[dict]) -> list[dict]:
    """Applica i filtri configurati in FILTRI."""
    today_str = date.today().isoformat()
    filtered = []

    for r in rows:
        # Filtro regioni
        if FILTRI["regioni"]:
            regioni_bando = [x.strip() for x in r.get("regioni", "").split(",")]
            if not any(reg in regioni_bando for reg in FILTRI["regioni"]):
                continue

        # Filtro forma agevolazione
        if FILTRI["forma_agevolazione"]:
            forme = [x.strip() for x in r.get("forma_agevolazione", "").split(",")]
            if not any(f in forme for f in FILTRI["forma_agevolazione"]):
                continue

        # Filtro bandi aperti oggi
        if FILTRI["aperto_oggi"]:
            chiusura = r.get("data_chiusura", "")
            if chiusura and chiusura < today_str:
                continue

        filtered.append(r)

    return filtered


def save_outputs(rows: list[dict], file_date: date):
    """Salva i dati in JSON e/o CSV."""
    date_str = file_date.strftime("%Y-%m-%d")
    saved = []

    if OUTPUT_JSON:
        fname = f"incentivi_{date_str}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        saved.append(fname)
        print(f"✓ JSON salvato: {fname} ({len(rows)} bandi)")

    if OUTPUT_CSV:
        fname = f"incentivi_{date_str}.csv"
        if rows:
            fieldnames = list(rows[0].keys())
            with open(fname, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            saved.append(fname)
            print(f"✓ CSV salvato: {fname} ({len(rows)} bandi)")

    return saved


def print_summary(rows: list[dict]):
    """Stampa un riepilogo rapido dei dati."""
    print(f"\n{'─'*50}")
    print(f"  Totale bandi: {len(rows)}")

    enti = {}
    for r in rows:
        e = r.get("ente", "N/D")[:40]
        enti[e] = enti.get(e, 0) + 1

    print(f"  Top 5 enti erogatori:")
    for ente, count in sorted(enti.items(), key=lambda x: -x[1])[:5]:
        print(f"    {count:4d}  {ente}")

    forme = {}
    for r in rows:
        for f in r.get("forma_agevolazione", "").split(","):
            f = f.strip()
            if f:
                forme[f] = forme.get(f, 0) + 1
    print(f"\n  Forme di agevolazione:")
    for forma, count in sorted(forme.items(), key=lambda x: -x[1])[:6]:
        print(f"    {count:4d}  {forma}")
    print(f"{'─'*50}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Scraper Open Data — incentivi.gov.it")
    print("=" * 50)

    try:
        raw_csv, file_date = fetch_latest_csv()
    except RuntimeError as e:
        print(f"\n✗ Errore: {e}")
        sys.exit(1)

    all_rows = parse_csv(raw_csv)
    print(f"  Bandi totali nel dataset: {len(all_rows)}")

    filtered_rows = apply_filters(all_rows)
    if len(filtered_rows) < len(all_rows):
        print(f"  Dopo filtri: {len(filtered_rows)} bandi")

    saved = save_outputs(filtered_rows, file_date)
    print_summary(filtered_rows)

    print("File pronti per l'importazione nel tuo database:")
    for f in saved:
        print(f"  → {f}")


if __name__ == "__main__":
    main()
