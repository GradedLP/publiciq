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
Exit 0 only if every check on every file passes. Needs: pip install jcs
"""
import hashlib
import json
import sys

import jcs


def h(obj):
    return hashlib.sha256(jcs.canonicalize(obj)).hexdigest()


def check(path):
    d = json.load(open(path, encoding="utf-8"))
    errs = []
    body = {k: v for k, v in d.items() if k != "addendum_hash"}
    if d.get("addendum_hash") != "sha256:" + h(body):
        errs.append("addendum_hash does not recompute")
    rows = d.get("rows") or []
    bad = [r.get("record_id") for r in rows
           if r.get("prediction_hash") != h({k: v for k, v in r.items() if k != "prediction_hash"})]
    if bad:
        errs.append(f"{len(bad)} row(s) whose prediction_hash does not recompute, e.g. {bad[0]}")
    if "batch_root" in d:
        root = hashlib.sha256("\n".join(sorted(r["prediction_hash"] for r in rows)).encode()).hexdigest()
        if root != d["batch_root"]:
            errs.append("batch_root does not recompute")
    late = [r.get("record_id") for r in rows
            if r.get("window_start_ts") is not None and r.get("created_at_ts") is not None
            and r["window_start_ts"] < r["created_at_ts"]]
    if late:
        errs.append(f"{len(late)} row(s) whose window opened before the row was created")
    return len(rows), errs


def main(paths):
    fail = 0
    for p in paths:
        n, errs = check(p)
        print(("OK   " if not errs else "FAIL ") + f"{p}  ({n} rows)" + ("" if not errs else "\n     " + "\n     ".join(errs)))
        fail += bool(errs)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
