#!/usr/bin/env python3
"""
Scraper EU Funding & Tenders Portal — SEDIA API
-------------------------------------------------
Usa filtro ElasticSearch range sulla deadlineDate per ottenere
solo bandi non ancora scaduti (deadlineDate >= oggi).

Produce: eu_bandi_YYYY-MM-DD.json + eu_bandi_YYYY-MM-DD.csv
"""

import requests, csv, json, sys, time
from datetime import date, datetime, timezone

API_URL   = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
PAGE_SIZE = 50
MAX_PAGES = 20
OUTPUT_JSON = True
OUTPUT_CSV  = True

def build_es_query() -> str:
    """Filtro ES: deadlineDate >= oggi (bandi non scaduti)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    query = {
        "bool": {
            "filter": [
                {
                    "range": {
                        "deadlineDate": {
                            "gte": today
                        }
                    }
                }
            ]
        }
    }
    return json.dumps(query)

def fetch_page(page: int, es_query: str) -> dict:
    params = {
        "apiKey":     "SEDIA",
        "text":       "*",
        "pageSize":   PAGE_SIZE,
        "pageNumber": page,
    }
    files = {
        "query": ("query.json", es_query, "application/json")
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; EUScraper/1.0)"}
    r = requests.post(API_URL, params=params, files=files, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def map_record(item: dict) -> dict:
    md = item.get("metadata", {})
    def first(key):
        v = md.get(key, [])
        return v[0] if isinstance(v, list) and v else (v or "")
    def join(key, limit=5):
        v = md.get(key, [])
        return ", ".join(str(x) for x in v[:limit]) if isinstance(v, list) else str(v or "")

    return {
        "id":             item.get("identifier", ""),
        "titolo":         first("title"),
        "descrizione":    first("description") or first("callTitle") or "",
        "programma":      first("frameworkProgramme"),
        "tipo":           first("type"),
        "stato_codice":   first("status"),
        "data_apertura":  first("startDate") or first("openingDate") or "",
        "data_chiusura":  first("deadlineDate") or first("closingDate") or "",
        "budget_totale":  first("budgetOverallMax") or first("budget") or "",
        "contributo_max": first("budgetIndividualMax") or "",
        "beneficiari":    join("eligibleApplicants"),
        "settore":        join("sector"),
        "keywords":       join("keywords"),
        "ente":           first("callIdentifier") or "Commissione Europea",
        "link": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{item.get('identifier', '')}",
    }

def fetch_all() -> list[dict]:
    es_query = build_es_query()
    all_records = []
    total_pages = 1

    for page in range(1, MAX_PAGES + 1):
        print(f"  Pagina {page}/{total_pages} — {len(all_records)} bandi finora...")
        try:
            data = fetch_page(page, es_query)
        except Exception as e:
            print(f"  ✗ Errore pagina {page}: {e}")
            break

        hits = data.get("results", [])
        if not hits:
            print("  Nessun risultato — fine.")
            break

        for item in hits:
            all_records.append(map_record(item))

        total = data.get("totalResults", 0)
        total_pages = min(MAX_PAGES, -(-total // PAGE_SIZE))
        print(f"    → {len(hits)} ricevuti, totale API: {total}")

        if page >= total_pages:
            break

        time.sleep(0.3)

    return all_records

def save_outputs(rows: list[dict]):
    ds = date.today().strftime("%Y-%m-%d")
    if OUTPUT_JSON:
        fname = f"eu_bandi_{ds}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON: {fname} ({len(rows)} bandi)")
    if OUTPUT_CSV and rows:
        fname = f"eu_bandi_{ds}.csv"
        with open(fname, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"✓ CSV:  {fname} ({len(rows)} bandi)")

def print_summary(rows: list[dict]):
    print(f"\n{'─'*50}\n  Totale bandi EU attivi: {len(rows)}")
    programmi = {}
    for r in rows:
        p = r.get("programma") or "N/D"
        programmi[p] = programmi.get(p, 0) + 1
    print("  Top programmi:")
    for p, c in sorted(programmi.items(), key=lambda x: -x[1])[:8]:
        print(f"    {c:4d}  {p}")
    print(f"{'─'*50}\n")

def main():
    print("="*50+"\n  Scraper EU Funding & Tenders — SEDIA API\n"+"="*50)
    print(f"  Filtro: deadlineDate >= {date.today()}")
    rows = fetch_all()
    if not rows:
        print("✗ Nessun bando attivo trovato.")
        sys.exit(1)
    save_outputs(rows)
    print_summary(rows)

if __name__ == "__main__":
    main()
