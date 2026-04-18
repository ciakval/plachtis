# RFID Reader UX Gaps

This document records UX changes required in the InfoDesk ticket management UI to support the RFID reader workflow.

## Context

The RFID reader API introduces two workflows that InfoDesk members must be able to manage:

1. **Pairing mode** — linking a physical RFID card to a SailTicket
2. **Scanning mode** — on-water tracking via card scans at departure/arrival

The existing UI supports initiating pairing and changing ticket status manually, but has two gaps.

---

## Gap 1: No way to unpair a card

### Problem

`SailTicket.rfid_uid` can only be set by scanning a card while in pairing mode. There is no UI action to clear or change it. If a card is accidentally paired to the wrong ticket, InfoDesk has no way to fix it without direct database access.

### Required change

Add an **"Unpair card"** button on the ticket detail page, visible only when `rfid_uid` is set. On confirmation, clears `rfid_uid` and logs a `SailTicketLog` entry (status unchanged, note: "RFID card unpaired by [user]").

---

## Gap 2: No way to cancel a pending pairing

### Problem

Once an InfoDesk member clicks "Pair RFID" on a ticket, `pending_pairing=True` is set on that ticket. There is no explicit way to cancel this — the only current escape is clicking "Pair RFID" on a *different* ticket, which implicitly cancels the first (the view clears all other `pending_pairing` flags). This is not obvious and could lead to confusion.

### Required change

When a ticket has `pending_pairing=True`, replace (or supplement) the "Pair RFID" button with a **"Cancel pairing"** button. On click, sets `pending_pairing=False` without any other changes and shows a confirmation message.
