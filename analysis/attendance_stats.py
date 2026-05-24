#!/usr/bin/env python3
"""
SkaRe 2026 — statistiky skutečné účasti

Počítá osoby, které se SkaRe skutečně zúčastnily, tj. byly kdykoli
označeny jako přítomné. Pokrývá i případy, kdy má osoba aktuálně jiný
status (např. "Nepřijede"), ale v historii příchodu záznam existuje.

Kritéria "byl přítomen":
  1. arrived_at IS NOT NULL  — infostánek záznám zaznamenal příchod, nebo
  2. existuje záznam v AttendanceLog se status='arrived'

Použití:
    python analysis/attendance_stats.py [cesta/k/databazi.sqlite3]

Výchozí cesta: plachtis-db.sqlite3 (spuštěno z kořene projektu)
"""

import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("plachtis-db.sqlite3")

CATEGORY_LABELS = {
    "CUB":   "Vlče/světluška (CUB)",
    "SCOUT": "Skaut/skautka (SCOUT)",
    "ROVER": "Rover/roverka (ROVER)",
    "ADULT": "Dospělý (ADULT)",
    None:    "Bez kategorie",
}

PERSON_TYPE_LABELS = {
    "regular":     "Člen oddílu (RegularParticipant)",
    "individual":  "Individuální účastník (IndividualParticipant)",
    "organizer":   "Organizátor (Organizer)",
}

# Všechny aktuálně existující hodnoty attendance_status pro přehled
ATTENDANCE_STATUS_LABELS = {
    "expected":   "Očekáván",
    "arrived":    "Přítomen",
    "departed":   "Odjel",
    "not_coming": "Nepřijede",
}


def connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        print(f"CHYBA: Databáze nenalezena: {path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_attended_persons(conn: sqlite3.Connection) -> list[dict]:
    """
    Vrátí seznam osob, které byly kdykoli přítomny.
    UNION přes:
      - arrived_at IS NOT NULL  (infostánek zaznamenal příchod)
      - existence záznamu v AttendanceLog se status='arrived'
    """
    sql = """
    SELECT
        p.id,
        p.first_name,
        p.last_name,
        p.category,
        p.attendance_status,
        p.arrived_at,
        CASE
            WHEN r.person_ptr_id IS NOT NULL THEN 'regular'
            WHEN i.person_ptr_id IS NOT NULL THEN 'individual'
            WHEN o.person_ptr_id IS NOT NULL THEN 'organizer'
            ELSE 'unknown'
        END AS person_type,
        -- zda byl příchod zaznamenán přes arrived_at nebo jen přes log
        CASE WHEN p.arrived_at IS NOT NULL THEN 1 ELSE 0 END AS has_arrived_at,
        CASE WHEN al_arrived.person_id IS NOT NULL THEN 1 ELSE 0 END AS has_log_entry
    FROM SkaRe_person p
    LEFT JOIN SkaRe_regularparticipant    r ON r.person_ptr_id = p.id
    LEFT JOIN SkaRe_individualparticipant i ON i.person_ptr_id = p.id
    LEFT JOIN SkaRe_organizer             o ON o.person_ptr_id = p.id
    LEFT JOIN (
        SELECT DISTINCT person_id
        FROM SkaRe_attendancelog
        WHERE status = 'arrived'
    ) al_arrived ON al_arrived.person_id = p.id
    WHERE p.arrived_at IS NOT NULL
       OR al_arrived.person_id IS NOT NULL
    ORDER BY p.last_name, p.first_name
    """
    return [dict(row) for row in conn.execute(sql)]


def get_current_status_distribution(conn: sqlite3.Connection) -> dict:
    """Aktuální rozložení stavů VŠECH osob v DB (pro kontext)."""
    sql = """
    SELECT attendance_status, COUNT(*) AS cnt
    FROM SkaRe_person
    GROUP BY attendance_status
    ORDER BY cnt DESC
    """
    return {row["attendance_status"]: row["cnt"] for row in conn.execute(sql)}


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def subsection(title: str) -> None:
    print()
    print(f"--- {title} ---")


def main() -> None:
    conn = connect(DB_PATH)

    attended = get_attended_persons(conn)
    current_dist = get_current_status_distribution(conn)

    total_in_db = sum(current_dist.values())
    total_attended = len(attended)

    # Osoby přítomné jen přes log (bez arrived_at) — "chaos" zmíněný v e-mailu
    log_only = [p for p in attended if not p["has_arrived_at"] and p["has_log_entry"]]

    section("CELKOVÉ POČTY")
    print(f"Celkem osob v databázi:          {total_in_db:>5}")
    print(f"Skuteční účastníci (přítomni):   {total_attended:>5}")
    print()
    print("Aktuální stav v DB (pro informaci):")
    for status, cnt in current_dist.items():
        label = ATTENDANCE_STATUS_LABELS.get(status, status)
        print(f"  {label:<30} {cnt:>5}")
    if log_only:
        print()
        print(
            f"  ⚠  {len(log_only)} osob bylo v historii označeno jako přítomno,\n"
            f"     ale aktuálně mají jiný stav (arrived_at = NULL):"
        )
        for p in log_only:
            status_label = ATTENDANCE_STATUS_LABELS.get(p["attendance_status"], p["attendance_status"])
            print(f"     • {p['first_name']} {p['last_name']} — aktuální stav: {status_label}")

    # --- Podle výchovné kategorie ---
    section("PODLE VÝCHOVNÉ KATEGORIE")
    by_category: dict[str | None, list] = defaultdict(list)
    for p in attended:
        by_category[p["category"]].append(p)

    category_order = ["CUB", "SCOUT", "ROVER", "ADULT", None]
    for cat in category_order:
        persons = by_category.get(cat, [])
        if not persons:
            continue
        label = CATEGORY_LABELS.get(cat, str(cat))
        print(f"  {label:<35} {len(persons):>5}")

    # --- Kategorie × typ osoby ---
    section("KATEGORIE × TYP OSOBY")
    header = f"{'Kategorie':<28} {'Člen oddílu':>12} {'Individuální':>14} {'Organizátor':>13} {'Celkem':>8}"
    print(header)
    print("-" * len(header))

    grand_total = defaultdict(int)
    for cat in category_order:
        persons = by_category.get(cat, [])
        if not persons:
            continue
        counts = defaultdict(int)
        for p in persons:
            counts[p["person_type"]] += 1
        regular    = counts["regular"]
        individual = counts["individual"]
        organizer  = counts["organizer"]
        total      = len(persons)
        label = CATEGORY_LABELS.get(cat, str(cat))
        print(f"  {label:<26} {regular:>12} {individual:>14} {organizer:>13} {total:>8}")
        grand_total["regular"]    += regular
        grand_total["individual"] += individual
        grand_total["organizer"]  += organizer
        grand_total["total"]      += total

    print("-" * len(header))
    print(
        f"  {'CELKEM':<26}"
        f" {grand_total['regular']:>12}"
        f" {grand_total['individual']:>14}"
        f" {grand_total['organizer']:>13}"
        f" {grand_total['total']:>8}"
    )

    # --- Podle typu osoby ---
    section("PODLE TYPU OSOBY")
    by_type: dict[str, list] = defaultdict(list)
    for p in attended:
        by_type[p["person_type"]].append(p)

    for ptype, label in PERSON_TYPE_LABELS.items():
        cnt = len(by_type.get(ptype, []))
        print(f"  {label:<45} {cnt:>5}")

    conn.close()
    print()


if __name__ == "__main__":
    main()
