#!/usr/bin/env python3
"""verify_manifest.py — check a pre-registration manifest end to end, from this repo alone.

  python verifier/verify_manifest.py prereg/<chain>/<stamp>_<chain>_preregistered_at_prediction.json [more ...]

For each manifest:
  1. addendum_hash   RFC-8785 (JCS) sha256 of the artifact without addendum_hash (same as
                     verify_addendum_hash.py).
  2. prediction_hash every row's hash recomputes from that row's own fields (JCS sha256 of the row
                     without prediction_hash) — so no forecast field can have been edited.
  3. batch_root      sha256 of the sorted row hashes joined by newlines equals the declared root.
  4. timing          every row's window opens no earlier than the row was created
                     (window_start_ts >= created_at_ts) where those fields exist.
  5. challengers     a manifest may also carry pre-registered challenger rows under
                     challengers.<model_id> (rows + batch_root): checks 2-4 run on them too.
Legacy manifests (ONLY the pre-v2 chains: solana, sui, xrpl, xrpl-mc, poolwatch) have no envelope
hash and publish a redacted subset of each frozen row, so a row's prediction_hash cannot be recomputed
from the file; for them only the batch_root over the published prediction_hash values is checked, and
the result is reported as LEGACY, not OK. Any other manifest missing its envelope or batch_root FAILS.
Challenger rows carry no window of their own: their timing is checked against their champion row's
window (source_record_id). Rows with no window field at all are counted and reported as unchecked.
Exit 0 only if every check on every file passes. Needs: pip install jcs
"""
import hashlib
import json
import sys

import jcs


def h(obj):
    return hashlib.sha256(jcs.canonicalize(obj)).hexdigest()


LEGACY_CHAINS = {"solana", "sui", "xrpl", "xrpl-mc", "poolwatch"}


def _rows(rows, root, label, windows=None):
    """windows: {champion record_id: window_start_ts}, for challenger rows (timed against their champion)."""
    errs, unchecked = [], 0
    bad = [r.get("record_id") for r in rows
           if r.get("prediction_hash") != h({k: v for k, v in r.items() if k != "prediction_hash"})]
    if bad:
        errs.append(f"{label}{len(bad)} row(s) whose prediction_hash does not recompute, e.g. {bad[0]}")
    if root is None:
        errs.append(f"{label}no batch_root")
    elif hashlib.sha256("\n".join(sorted(r["prediction_hash"] for r in rows)).encode()).hexdigest() != root:
        errs.append(f"{label}batch_root does not recompute")
    late = []
    for r in rows:
        w = r.get("window_start_ts")
        if w is None and windows is not None:
            w = windows.get(r.get("source_record_id"))
            if w is None:
                errs.append(f"{label}row {r.get('record_id')} names no champion row in this manifest")
                continue
        if w is None or r.get("created_at_ts") is None:
            unchecked += 1
        elif w < r["created_at_ts"]:
            late.append(r.get("record_id"))
    if late:
        errs.append(f"{label}{len(late)} row(s) whose window opened before the row was created")
    return errs, unchecked


def check(path):
    d = json.load(open(path, encoding="utf-8"))
    errs = []
    if "addendum_hash" not in d:
        rows = d.get("rows") or []
        if d.get("chain") not in LEGACY_CHAINS:
            return len(rows), [f"no addendum_hash (envelope) on a {d.get('chain')!r} manifest - only pre-v2 chains may lack it"], False, 0
        if "batch_root" not in d:
            return len(rows), ["no addendum_hash and no batch_root: nothing in this file can be checked"], True, 0
        if hashlib.sha256("\n".join(sorted(r["prediction_hash"] for r in rows)).encode()).hexdigest() != d["batch_root"]:
            errs.append("batch_root does not recompute")
        return len(rows), errs, True, 0
    body = {k: v for k, v in d.items() if k != "addendum_hash"}
    if d.get("addendum_hash") != "sha256:" + h(body):
        errs.append("addendum_hash does not recompute")
    rows = d.get("rows") or []
    e, unchecked = _rows(rows, d.get("batch_root"), "")
    errs += e
    n = len(rows)
    win = {r.get("record_id"): r.get("window_start_ts") for r in rows}
    for name, c in (d.get("challengers") or {}).items():
        e, u = _rows(c.get("rows") or [], c.get("batch_root"), f"challenger {name}: ", windows=win)
        errs += e; unchecked += u
        n += len(c.get("rows") or [])
    return n, errs, False, unchecked


def main(paths):
    fail = 0
    for p in paths:
        n, errs, legacy, unchecked = check(p)
        tag = ("LEGACY " if legacy else "OK     ") if not errs else "FAIL   "
        note = "  batch_root only (pre-v2 format: rows are a redacted subset)" if legacy and not errs else ""
        if unchecked and not errs:
            note += f"  ({unchecked} row(s) carry no window field: timing not checkable from this file)"
        print(tag + f"{p}  ({n} rows)" + note + ("" if not errs else "\n     " + "\n     ".join(errs)))
        fail += bool(errs)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
