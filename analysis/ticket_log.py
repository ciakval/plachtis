#!/usr/bin/env python3
"""
SkaRe 2026 — chronologický výpis změn stavu plavenek

Pro každý záznam v SailTicketLog vypíše:
  čas (CEST)  |  kód plavenky  |  nový stav  |  název lodi

Poznámka: log nezaznamenává historii párování plavenky s lodí.
Sloupec 'Loď' odráží aktuální spárování plavenky, nikoli nutně
stav v okamžiku záznamu.

Použití:
    python analysis/ticket_log.py [cesta/k/databazi.sqlite3]

Volitelné filtry (lze kombinovat):
    --ticket KÓD      zobraz jen záznamy pro danou plavenku (např. P550-4)
    --status STAV     filtruj dle stavu: ashore | on_water | lost
    --date DATUM      filtruj dle dne v CEST (formát YYYY-MM-DD)
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("plachtis-db.sqlite3")
Prague  = ZoneInfo("Europe/Prague")
UTC     = timezone.utc

STATUS_CS = {
    "ashore":   "Na souši  ",
    "on_water": "Na vodě   ",
    "lost":     "Ztracena  ",
}


def connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        print(f"CHYBA: Databáze nenalezena: {path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def load_entries(conn, ticket_filter=None, status_filter=None, date_filter=None):
    sql = """
        SELECT
            l.changed_at,
            t.code        AS ticket_code,
            l.status,
            b.sail_number AS boat_sail,
            b.name        AS boat_name
        FROM SkaRe_sailticketlog l
        JOIN SkaRe_sailticket t ON t.id = l.ticket_id
        LEFT JOIN SkaRe_boat  b ON b.id = t.boat_id
        ORDER BY l.changed_at ASC, l.id ASC
    """
    rows = []
    for r in conn.execute(sql):
        ts = datetime.fromisoformat(r["changed_at"]).replace(tzinfo=UTC).astimezone(Prague)

        if ticket_filter and r["ticket_code"] != ticket_filter:
            continue
        if status_filter and r["status"] != status_filter:
            continue
        if date_filter and ts.strftime("%Y-%m-%d") != date_filter:
            continue

        if r["boat_sail"]:
            boat = f"{r['boat_sail']} {r['boat_name']}"
        elif r["boat_name"]:
            boat = r["boat_name"]
        else:
            boat = "—"

        rows.append({
            "ts":     ts,
            "code":   r["ticket_code"],
            "status": r["status"],
            "boat":   boat,
        })
    return rows


def parse_args():
    # argv[1] may be the DB path (handled above) — skip it for argparse
    args_to_parse = [a for a in sys.argv[1:] if not a.endswith(".sqlite3") and not a.endswith(".db")]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--ticket", default=None)
    parser.add_argument("--status", default=None, choices=["ashore", "on_water", "lost"])
    parser.add_argument("--date",   default=None)
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_args(args_to_parse)


def main():
    opts = parse_args()
    if opts.help:
        print(__doc__)
        sys.exit(0)

    conn    = connect(DB_PATH)
    entries = load_entries(conn, opts.ticket, opts.status, opts.date)
    conn.close()

    if not entries:
        print("Žádné záznamy nevyhověly zadaným filtrům.")
        return

    # Šířka sloupce pro název lodi
    max_boat = max(len(e["boat"]) for e in entries)
    max_boat = max(max_boat, len("Loď"))

    # Hlavička
    print()
    print("  Poznámka: sloupec 'Loď' odráží aktuální spárování, "
          "ne historické (log párování nezaznamenává).")
    print()
    header = (
        f"  {'Čas (CEST)':<19}  "
        f"{'Plavenka':<12}  "
        f"{'Nový stav':<12}  "
        f"{'Loď':<{max_boat}}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    prev_day = None
    for e in entries:
        day = e["ts"].strftime("%Y-%m-%d")
        if day != prev_day:
            if prev_day is not None:
                print()
            label = e["ts"].strftime("%-d.%-m.%Y (%A)").replace(
                "Monday", "pondělí").replace("Tuesday", "úterý") \
                .replace("Wednesday", "středa").replace("Thursday", "čtvrtek") \
                .replace("Friday", "pátek").replace("Saturday", "sobota") \
                .replace("Sunday", "neděle")
            print(f"  === {label} ===")
            prev_day = day

        status_label = STATUS_CS.get(e["status"], e["status"])
        print(
            f"  {e['ts'].strftime('%Y-%m-%d %H:%M:%S'):<19}  "
            f"{e['code']:<12}  "
            f"{status_label:<12}  "
            f"{e['boat']}"
        )

    print()
    print(f"  Celkem záznamů: {len(entries)}")
    print()


if __name__ == "__main__":
    main()
