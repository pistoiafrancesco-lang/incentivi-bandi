#!/usr/bin/env python3
"""
Scraper EU Funding & Tenders Portal — SEDIA API
-------------------------------------------------
API pubblica della Commissione Europea, nessuna autenticazione richiesta.
Endpoint: api.tech.ec.europa.eu/search-api/prod/rest/search

Produce: eu_bandi_YYYY-MM-DD.json + eu_bandi_YYYY-MM-DD.csv
"""

import requests, csv, json, sys, time
from datetime import date

# ── Configurazione ────────────────────────────────────────────────────────────

API_URL  = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
API_KEY  = "SEDIA"
PAGE_SIZE = 50       # massimo per chiamata
MAX_PAGES = 20       # sicurezza: max 1000 bandi per run
OUTPUT_JSON = True
OUTPUT_CSV  = True

# Filtri: solo bandi aperti o in apertura, rilevanti per imprese/associazioni italiane
QUERY_PARAMS = {
    "apiKey":     API_KEY,
    "text":       "*",
    "pageSize":   PAGE_SIZE,
    "pageNumber": 1,
    # Solo bandi aperti o in apertura imminente
    "callStatus": "open,forthcoming",
}

# ── Mapping campi API → output ────────────────────────────────────────────────

def map_record(item: dict) -> dict:
    md = item.get("metadata", {})
    def first(key):
        v = md.get(key, [])
        return v[0] if isinstance(v, list) and v else (v or "")

    return {
        "id":                  item.get("identifier", ""),
        "titolo":              first("title"),
        "descrizione":         first("description") or first("callTitle"),
        "programma":           first("frameworkProgramme"),
        "tipo":                first("type"),
        "stato":               first("status"),
        "data_apertura":       first("startDate") or first("openingDate"),
        "data_chiusura":       first("deadlineDate") or first("closingDate"),
        "budget_totale":       first("budgetOverallMax") or first("budget"),
        "contributo_max":      first("budgetIndividualMax"),
        "beneficiari":         ", ".join(md.get("eligibleApplicants", [])) if isinstance(md.get("eligibleApplicants"), list) else first("eligibleApplicants"),
        "settore":             ", ".join(md.get("sector", [])) if isinstance(md.get("sector"), list) else first("sector"),
        "keywords":            ", ".join(md.get("keywords", [])[:5]) if isinstance(md.get("keywords"), list) else "",
        "link":                f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{item.get('identifier', '')}",
        "ente":                first("callIdentifier") or "Commissione Europea",
    }


# ── Fetch paginato ────────────────────────────────────────────────────────────

def fetch_all() -> list[dict]:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    all_records = []
    total_pages = 1

    for page in range(1, MAX_PAGES + 1):
        params = {**QUERY_PARAMS, "pageNumber": page}
        print(f"  Pagina {page}/{total_pages} — {len(all_records)} bandi finora...")

        try:
            r = session.get(API_URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ✗ Errore pagina {page}: {e}")
            break

        hits = data.get("results", [])
        if not hits:
            break

        for item in hits:
            all_records.append(map_record(item))

        total = data.get("totalResults", 0)
        total_pages = min(MAX_PAGES, -(-total // PAGE_SIZE))  # ceil division

        if page >= total_pages:
            break

        time.sleep(0.5)  # rispetta il rate limit

    return all_records


# ── Output ────────────────────────────────────────────────────────────────────

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
    print(f"\n{'─'*50}")
    print(f"  Totale bandi EU: {len(rows)}")

    programmi = {}
    for r in rows:
        p = r.get("programma", "N/D") or "N/D"
        programmi[p] = programmi.get(p, 0) + 1
    print("  Top programmi:")
    for p, c in sorted(programmi.items(), key=lambda x: -x[1])[:8]:
        print(f"    {c:4d}  {p}")

    stati = {}
    for r in rows:
        s = r.get("stato", "N/D") or "N/D"
        stati[s] = stati.get(s, 0) + 1
    print("  Stato bandi:")
    for s, c in sorted(stati.items(), key=lambda x: -x[1]):
        print(f"    {c:4d}  {s}")
    print(f"{'─'*50}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Scraper EU Funding & Tenders — SEDIA API")
    print("=" * 50)

    rows = fetch_all()

    if not rows:
        print("✗ Nessun risultato ricevuto dall'API.")
        sys.exit(1)

    save_outputs(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
