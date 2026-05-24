#!/usr/bin/env python3
"""
SkaRe 2026 — analýza pohybu plavenek

Rekonstruuje pohyb plavenek z SailTicketLog a vytváří textové i grafické výstupy.

Požadavky: matplotlib (pip install matplotlib)

Použití:
    python analysis/ticket_analysis.py [cesta/k/databazi.sqlite3]

Výstup: konzole + adresář analysis/ticket_graphs/ s PNG grafy.
"""

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import MaxNLocator
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠  matplotlib není nainstalován — grafy se nevytvoří.")
    print("   pip install matplotlib\n")

DB_PATH   = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("plachtis-db.sqlite3")
OUT_DIR   = Path(__file__).parent / "ticket_graphs"

COLOR_LABELS = {"p550": "P550", "sail": "Plachetnice", "other": "Ostatní", "spare": "Náhradní"}
STATUS_CS    = {"ashore": "Na souši", "on_water": "Na vodě", "lost": "Ztracena"}

UTC  = timezone.utc
Prague = ZoneInfo("Europe/Prague")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        print(f"CHYBA: Databáze nenalezena: {path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def load_tickets(conn) -> dict:
    """ticket_id → {code, color, status, rfid_uid, boat_id}"""
    rows = conn.execute("""
        SELECT t.id, t.code, t.color, t.status, t.rfid_uid, t.boat_id,
               b.sail_number
        FROM SkaRe_sailticket t
        LEFT JOIN SkaRe_boat b ON b.id = t.boat_id
        ORDER BY t.code
    """)
    return {r["id"]: dict(r) for r in rows}


def load_log(conn) -> list[dict]:
    """Všechny záznamy logu seřazené chronologicky."""
    rows = conn.execute("""
        SELECT l.id, l.ticket_id, l.status, l.changed_at, l.note,
               u.username AS changed_by
        FROM SkaRe_sailticketlog l
        LEFT JOIN auth_user u ON u.id = l.changed_by_id
        ORDER BY l.changed_at ASC, l.id ASC
    """)
    entries = []
    for r in rows:
        d = dict(r)
        d["changed_at"] = datetime.fromisoformat(d["changed_at"]).replace(tzinfo=UTC).astimezone(Prague)
        entries.append(d)
    return entries


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def reconstruct_timeline(log: list[dict]) -> list[tuple[datetime, int]]:
    """
    Pro každý okamžik změny stavu vypočte, kolik plavenek je právě na vodě.
    Vrátí seznam (timestamp, počet_na_vodě).
    """
    ticket_state: dict[int, str] = {}   # ticket_id → aktuální stav
    timeline: list[tuple[datetime, int]] = []

    on_water_count = 0
    for entry in log:
        tid    = entry["ticket_id"]
        new_st = entry["status"]
        old_st = ticket_state.get(tid)

        if old_st == "on_water" and new_st != "on_water":
            on_water_count -= 1
        elif old_st != "on_water" and new_st == "on_water":
            on_water_count += 1

        ticket_state[tid] = new_st
        timeline.append((entry["changed_at"], on_water_count))

    return timeline


def compute_trips(log: list[dict], tickets: dict) -> dict[int, list[dict]]:
    """
    Rekonstruuje 'výlety' pro každou plavenku.
    Výlet = přechod ashore→on_water následovaný on_water→(ashore|lost).
    Vrátí {ticket_id: [{"start": dt, "end": dt|None, "duration_min": int|None}, ...]}.
    """
    trips: dict[int, list[dict]] = defaultdict(list)
    pending: dict[int, datetime] = {}   # ticket_id → čas odjezdu

    for entry in log:
        tid = entry["ticket_id"]
        st  = entry["status"]
        ts  = entry["changed_at"]

        if st == "on_water":
            pending[tid] = ts
        elif st in ("ashore", "lost") and tid in pending:
            start = pending.pop(tid)
            dur   = int((ts - start).total_seconds() / 60)
            trips[tid].append({"start": start, "end": ts, "duration_min": dur})

    # Výlety bez ukončení (plavenka stále na vodě na konci záznamu)
    for tid, start in pending.items():
        trips[tid].append({"start": start, "end": None, "duration_min": None})

    return trips


def lost_events(log: list[dict]) -> list[dict]:
    """Záznamy přechodu do stavu 'lost'."""
    return [e for e in log if e["status"] == "lost"]


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print()
    print("=" * 62)
    print(f"  {title}")
    print("=" * 62)


def print_report(tickets: dict, log: list[dict], trips: dict) -> None:
    # --- Základní přehled ---
    section("ZÁKLADNÍ PŘEHLED PLAVENEK")

    by_color: dict[str, list] = defaultdict(list)
    for t in tickets.values():
        by_color[t["color"]].append(t)

    print(f"  {'Typ':<20} {'Celkem':>7} {'Na souši':>9} {'Na vodě':>9} {'Ztracena':>9}")
    print("  " + "-" * 56)
    totals = defaultdict(int)
    for color, ts_list in sorted(by_color.items()):
        ashore   = sum(1 for t in ts_list if t["status"] == "ashore")
        on_water = sum(1 for t in ts_list if t["status"] == "on_water")
        lost     = sum(1 for t in ts_list if t["status"] == "lost")
        lbl      = COLOR_LABELS.get(color, color)
        print(f"  {lbl:<20} {len(ts_list):>7} {ashore:>9} {on_water:>9} {lost:>9}")
        totals["total"]    += len(ts_list)
        totals["ashore"]   += ashore
        totals["on_water"] += on_water
        totals["lost"]     += lost
    print("  " + "-" * 56)
    print(f"  {'CELKEM':<20} {totals['total']:>7} {totals['ashore']:>9} {totals['on_water']:>9} {totals['lost']:>9}")

    # --- Log souhrn ---
    section("SOUHRN LOGOVÝCH ZÁZNÁMŮ")
    total_entries = len(log)
    by_status = defaultdict(int)
    for e in log:
        by_status[e["status"]] += 1
    print(f"  Celkem záznamů v logu:        {total_entries:>6}")
    for st, cnt in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  └ {STATUS_CS.get(st, st):<28} {cnt:>6}")
    print()
    if log:
        print(f"  Nejstarší záznam:  {log[0]['changed_at']:%Y-%m-%d %H:%M}")
        print(f"  Nejnovější záznam: {log[-1]['changed_at']:%Y-%m-%d %H:%M}")

    # --- Ztráty ---
    section("ZTRACENÉ PLAVENKY")
    lost_now  = [t for t in tickets.values() if t["status"] == "lost"]
    lost_evts = lost_events(log)
    print(f"  Aktuálně ztraceny:            {len(lost_now):>6}")
    print(f"  Celkem přechodů do 'lost':    {len(lost_evts):>6}  (včetně poté nalezených)")
    if lost_evts:
        print()
        seen_tickets: dict[int, int] = defaultdict(int)
        for e in lost_evts:
            seen_tickets[e["ticket_id"]] += 1
        for tid, count in sorted(seen_tickets.items(), key=lambda x: -x[1]):
            t = tickets[tid]
            suffix = " ← aktuálně stále ztracena" if t["status"] == "lost" else " (nalezena)"
            sail = f", plachetnice č. {t['sail_number']}" if t.get("sail_number") else ""
            print(f"  • {t['code']} ({COLOR_LABELS.get(t['color'], t['color'])}{sail}): "
                  f"{count}× označena jako ztracena{suffix}")

    # --- Výlety ---
    section("STATISTIKY VÝLETŮ (ashore → on_water → ashore)")
    all_trips_complete = [
        tr for tlist in trips.values()
        for tr in tlist if tr["duration_min"] is not None
    ]
    all_trips_open = [
        tr for tlist in trips.values()
        for tr in tlist if tr["duration_min"] is None
    ]
    total_trips = len(all_trips_complete) + len(all_trips_open)
    tickets_used = len([t for t in trips if trips[t]])

    print(f"  Plavenek použitých na výlet:  {tickets_used:>6}  (z {len(tickets)} celkem)")
    print(f"  Celkem výletů:                {total_trips:>6}")
    print(f"  └ Uzavřených (s návratem):    {len(all_trips_complete):>6}")
    print(f"  └ Otevřených (bez návratu):   {len(all_trips_open):>6}")

    if all_trips_complete:
        durations = [t["duration_min"] for t in all_trips_complete]
        durations.sort()
        n = len(durations)
        mean  = sum(durations) / n
        med   = durations[n // 2]
        p90   = durations[int(n * 0.9)]
        print()
        print(f"  Délka výletu (jen uzavřené):")
        print(f"  └ Průměr:     {mean:>6.0f} min  ({mean/60:.1f} h)")
        print(f"  └ Medián:     {med:>6} min  ({med/60:.1f} h)")
        print(f"  └ 90. percentil: {p90:>3} min  ({p90/60:.1f} h)")
        print(f"  └ Nejkratší:  {durations[0]:>6} min")
        print(f"  └ Nejdelší:   {durations[-1]:>6} min  ({durations[-1]/60:.1f} h)")

    # Plavenky s nejvíce výlety
    print()
    print("  Plavenky s nejvíce výlety:")
    top = sorted(trips.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for tid, tlist in top:
        t = tickets[tid]
        sail = f", č. {t['sail_number']}" if t.get("sail_number") else ""
        print(f"  • {t['code']} ({COLOR_LABELS.get(t['color'], t['color'])}{sail}): "
              f"{len(tlist)} výletů")

    # --- Aktivita operátorů ---
    section("AKTIVITA OPERÁTORŮ (podle uživatele)")
    by_user: dict[str, int] = defaultdict(int)
    for e in log:
        by_user[e["changed_by"] or "(RFID/systém)"] += 1
    for user, cnt in sorted(by_user.items(), key=lambda x: -x[1]):
        print(f"  {user:<30} {cnt:>6} záznamů")


# ---------------------------------------------------------------------------
# Graphs
# ---------------------------------------------------------------------------

def save_graph(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → uloženo: {path}")


def plot_on_water_timeline(timeline: list[tuple[datetime, int]]) -> None:
    """Čárový graf: počet plavenek na vodě v čase."""
    if not timeline:
        return
    times  = [t for t, _ in timeline]
    counts = [c for _, c in timeline]

    # Přidáme i počáteční nulový bod
    t_start = times[0] - timedelta(hours=1)
    times   = [t_start] + times
    counts  = [0] + counts

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.step(times, counts, where="post", color="#1a6faf", linewidth=1.5)
    ax.fill_between(times, counts, step="post", alpha=0.2, color="#1a6faf")
    ax.set_title("Počet plavenek na vodě v čase", fontsize=13, pad=10)
    ax.set_xlabel("Čas")
    ax.set_ylabel("Počet plavenek")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.xticks(rotation=45, ha="right")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    save_graph(fig, "01_on_water_timeline.png")


def plot_events_per_hour(log: list[dict]) -> None:
    """Histogram: počet změn stavu po hodinách celého eventu."""
    if not log:
        return

    # Zjistíme rozsah
    t_min = log[0]["changed_at"].replace(minute=0, second=0, microsecond=0)
    t_max = log[-1]["changed_at"].replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Bucket per hodina
    hours: list[datetime] = []
    current = t_min
    while current < t_max:
        hours.append(current)
        current += timedelta(hours=1)

    # Počty pro každý stav
    counts: dict[str, list[int]] = {st: [0] * len(hours) for st in ("on_water", "ashore", "lost")}
    for e in log:
        bucket = int((e["changed_at"] - t_min).total_seconds() // 3600)
        if 0 <= bucket < len(hours):
            counts[e["status"]][bucket] += 1

    fig, ax = plt.subplots(figsize=(14, 4))
    bar_w   = timedelta(hours=0.85)
    colors  = {"on_water": "#2196F3", "ashore": "#4CAF50", "lost": "#F44336"}
    labels  = {"on_water": "Na vodu", "ashore": "Na souš", "lost": "Ztracena"}

    bottom = [0] * len(hours)
    for st in ("on_water", "ashore", "lost"):
        bars = ax.bar(
            hours, counts[st], width=bar_w,
            bottom=bottom,
            color=colors[st], label=labels[st], align="edge",
        )
        bottom = [b + c for b, c in zip(bottom, counts[st])]

    # Denní dělicí čáry
    day = t_min.replace(hour=0, minute=0)
    while day <= t_max:
        if t_min <= day <= t_max:
            ax.axvline(day, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
            ax.text(day, ax.get_ylim()[1] * 0.97, day.strftime("%-d.%-m."),
                    ha="left", va="top", fontsize=8, color="gray")
        day += timedelta(days=1)

    ax.set_title("Počet změn stavu plavenek po hodinách", fontsize=13, pad=10)
    ax.set_xlabel("Čas")
    ax.set_ylabel("Počet změn")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    plt.xticks(rotation=45, ha="right")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_graph(fig, "02_events_per_hour.png")


def plot_trip_duration_histogram(trips: dict) -> None:
    """Histogram délek výletů."""
    durations = [
        tr["duration_min"]
        for tlist in trips.values()
        for tr in tlist
        if tr["duration_min"] is not None
    ]
    if not durations:
        return

    # Skupiny po 30 min, max 8 h (delší = outlier)
    cap    = 8 * 60
    clipped = [min(d, cap) for d in durations]
    bins   = list(range(0, cap + 31, 30))

    fig, ax = plt.subplots(figsize=(10, 4))
    n, _, patches = ax.hist(clipped, bins=bins, color="#5C6BC0", edgecolor="white")

    # Zvýrazni průměr a medián
    mean = sum(durations) / len(durations)
    med  = sorted(durations)[len(durations) // 2]
    ax.axvline(mean, color="#F44336", linestyle="--", linewidth=1.5,
               label=f"Průměr: {mean:.0f} min ({mean/60:.1f} h)")
    ax.axvline(med,  color="#FF9800", linestyle="--", linewidth=1.5,
               label=f"Medián: {med} min ({med/60:.1f} h)")

    ax.set_xticks(bins[::2])
    ax.set_xticklabels([f"{b//60}h{b%60:02d}" if b < cap else f"≥{cap//60}h" for b in bins[::2]],
                       rotation=45, ha="right")
    ax.set_title("Délka výletů (od výjezdu do návratu na souš)", fontsize=13, pad=10)
    ax.set_xlabel("Délka výletu")
    ax.set_ylabel("Počet výletů")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_graph(fig, "03_trip_duration_histogram.png")


def plot_trips_per_ticket(trips: dict, tickets: dict) -> None:
    """Histogram: kolik výletů absolvovala každá plavenka."""
    counts = []
    for tid in tickets:
        counts.append(len(trips.get(tid, [])))

    if not counts:
        return

    max_c = max(counts)
    bins  = list(range(0, max_c + 2))

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(counts, bins=bins, align="left", rwidth=0.8, color="#26A69A", edgecolor="white")
    ax.set_title("Počet výletů na jednu plavenku", fontsize=13, pad=10)
    ax.set_xlabel("Počet výletů")
    ax.set_ylabel("Počet plavenek")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # Popisky sloupců
    for rect in ax.patches:
        h = rect.get_height()
        if h > 0:
            ax.text(rect.get_x() + rect.get_width() / 2, h + 0.15, str(int(h)),
                    ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    save_graph(fig, "04_trips_per_ticket.png")


def plot_on_water_by_color(log: list[dict], tickets: dict) -> None:
    """
    Vrstvený čárový graf: počet plavenek na vodě v čase, rozděleno podle barvy/typu.
    """
    if not log:
        return

    # Mapování ticket_id → color
    tid_color = {tid: t["color"] for tid, t in tickets.items()}
    colors_present = sorted({t["color"] for t in tickets.values()})

    # Aktuální stav per (tid, color)
    ticket_state: dict[int, str] = {}
    on_water_by_color: dict[str, int] = defaultdict(int)

    # Sbíráme body pro každou časovou událost
    times: list[datetime] = []
    color_counts: dict[str, list[int]] = {c: [] for c in colors_present}

    for entry in log:
        tid    = entry["ticket_id"]
        new_st = entry["status"]
        old_st = ticket_state.get(tid)
        color  = tid_color.get(tid, "other")

        if old_st == "on_water" and new_st != "on_water":
            on_water_by_color[color] = max(0, on_water_by_color[color] - 1)
        elif old_st != "on_water" and new_st == "on_water":
            on_water_by_color[color] += 1

        ticket_state[tid] = new_st
        times.append(entry["changed_at"])
        for c in colors_present:
            color_counts[c].append(on_water_by_color[c])

    if not times:
        return

    # Přidáme nulový bod
    t_start = times[0] - timedelta(hours=1)
    times   = [t_start] + times
    for c in colors_present:
        color_counts[c] = [0] + color_counts[c]

    color_palette = {
        "p550":  "#1a6faf",
        "sail":  "#e65100",
        "other": "#2e7d32",
        "spare": "#9c27b0",
    }

    fig, ax = plt.subplots(figsize=(12, 4))
    bottom = [0] * len(times)
    for color in colors_present:
        vals = color_counts[color]
        ax.fill_between(times, bottom, [b + v for b, v in zip(bottom, vals)],
                        step="post", alpha=0.75,
                        color=color_palette.get(color, "gray"),
                        label=COLOR_LABELS.get(color, color))
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_title("Plavenky na vodě v čase — podle typu", fontsize=13, pad=10)
    ax.set_xlabel("Čas")
    ax.set_ylabel("Počet plavenek na vodě")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.xticks(rotation=45, ha="right")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    save_graph(fig, "05_on_water_by_type.png")


def plot_daily_activity(log: list[dict]) -> None:
    """
    Pro každý den eventu: hodinový heatmap (stav aktivity).
    Jeden subplot per den.
    """
    if not log:
        return

    # Rozdělíme záznamy po dnech
    days: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for e in log:
        day  = e["changed_at"].strftime("%Y-%m-%d")
        hour = e["changed_at"].hour
        days[day][hour] += 1

    sorted_days = sorted(days.keys())
    n = len(sorted_days)
    if n == 0:
        return

    fig, axes = plt.subplots(n, 1, figsize=(12, 2.5 * n), squeeze=False)
    fig.suptitle("Denní aktivita — počet změn stavu plavenek po hodinách", fontsize=13, y=1.01)

    for i, day in enumerate(sorted_days):
        ax       = axes[i][0]
        hourly   = [days[day].get(h, 0) for h in range(24)]
        dt_label = datetime.strptime(day, "%Y-%m-%d").strftime("%-d.%-m.%Y (%A)").replace(
            "Monday", "Pondělí").replace("Tuesday", "Úterý").replace("Wednesday", "Středa") \
            .replace("Thursday", "Čtvrtek").replace("Friday", "Pátek") \
            .replace("Saturday", "Sobota").replace("Sunday", "Neděle")

        bars = ax.bar(range(24), hourly, color="#5C6BC0", edgecolor="white", width=0.9)
        ax.set_title(dt_label, fontsize=10)
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=7)
        ax.set_ylabel("Počet změn")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        # Popisky
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.1, str(int(h)),
                        ha="center", va="bottom", fontsize=7)

    fig.tight_layout()
    save_graph(fig, "06_daily_activity.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    conn    = connect(DB_PATH)
    tickets = load_tickets(conn)
    log     = load_log(conn)
    conn.close()

    print_report(tickets, log, compute_trips(log, tickets))

    if HAS_MPL and log:
        section("GENEROVÁNÍ GRAFŮ")
        timeline = reconstruct_timeline(log)
        trips    = compute_trips(log, tickets)

        plot_on_water_timeline(timeline)
        plot_events_per_hour(log)
        plot_trip_duration_histogram(trips)
        plot_trips_per_ticket(trips, tickets)
        plot_on_water_by_color(log, tickets)
        plot_daily_activity(log)
        print()
        print(f"  Grafy uloženy do: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
