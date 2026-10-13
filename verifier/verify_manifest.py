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
Legacy manifests (the pre-v2 streams: solana, sui, xrpl, xrpl-mc, poolwatch) have no envelope
hash and publish a redacted subset of each frozen row, so a row's prediction_hash cannot be recomputed
from the file; for them only the batch_root over the published prediction_hash values is checked, and
the result is reported as LEGACY, not OK.
Exit 0 only if every check on every file passes. Needs: pip install jcs
"""
import hashlib
import json
import sys

import jcs


def h(obj):
    return hashlib.sha256(jcs.canonicalize(obj)).hexdigest()


def _rows(rows, root, label):
    errs = []
    bad = [r.get("record_id") for r in rows
           if r.get("prediction_hash") != h({k: v for k, v in r.items() if k != "prediction_hash"})]
    if bad:
        errs.append(f"{label}{len(bad)} row(s) whose prediction_hash does not recompute, e.g. {bad[0]}")
    if root is not None:
        if hashlib.sha256("\n".join(sorted(r["prediction_hash"] for r in rows)).encode()).hexdigest() != root:
            errs.append(f"{label}batch_root does not recompute")
    late = [r.get("record_id") for r in rows
            if r.get("window_start_ts") is not None and r.get("created_at_ts") is not None
            and r["window_start_ts"] < r["created_at_ts"]]
    if late:
        errs.append(f"{label}{len(late)} row(s) whose window opened before the row was created")
    return errs


def check(path):
    d = json.load(open(path, encoding="utf-8"))
    errs = []
    if "addendum_hash" not in d:                       # legacy (pre-v2) manifest
        rows = d.get("rows") or []
        if "batch_root" not in d:
            return len(rows), ["no addendum_hash and no batch_root: nothing in this file can be checked"], True
        if hashlib.sha256("\n".join(sorted(r["prediction_hash"] for r in rows)).encode()).hexdigest() != d["batch_root"]:
            errs.append("batch_root does not recompute")
        return len(rows), errs, True
    body = {k: v for k, v in d.items() if k != "addendum_hash"}
    if d.get("addendum_hash") != "sha256:" + h(body):
        errs.append("addendum_hash does not recompute")
    rows = d.get("rows") or []
    errs += _rows(rows, d.get("batch_root"), "")
    n = len(rows)
    for name, c in (d.get("challengers") or {}).items():
        errs += _rows(c.get("rows") or [], c.get("batch_root"), f"challenger {name}: ")
        n += len(c.get("rows") or [])
    return n, errs, False


def main(paths):
    fail = 0
    for p in paths:
        n, errs, legacy = check(p)
        tag = ("LEGACY " if legacy else "OK     ") if not errs else "FAIL   "
        note = "  batch_root only (pre-v2 format: rows are a redacted subset)" if legacy and not errs else ""
        print(tag + f"{p}  ({n} rows)" + note + ("" if not errs else "\n     " + "\n     ".join(errs)))
        fail += bool(errs)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
