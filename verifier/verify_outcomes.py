#!/usr/bin/env python3
"""verify_outcomes.py — check published outcomes against the pre-registrations, and (optionally)
against the chain itself.

  python verifier/verify_outcomes.py prereg/<chain>/outcomes/<file>.json [--rpc https://<archive-node>]

For every outcome row:
  1. it was pre-registered: its record_id is in a prereg/<chain>/*_preregistered_at_prediction.json
     manifest, every frozen field in the outcome row equals that manifest row, and its
     prediction_hash recomputes from the manifest row;
  2. it is internally consistent: a RESOLVED row with a band (EVM / Sui boards) has y = 1 exactly
     when a first_breach is reported, and the reported first_breach tick is outside the band;
  3. with --rpc (EVM boards; needs an ARCHIVE node — ordinary public nodes keep only recent state):
     the pool's tick read on chain AT the reported first_breach block is the reported tick.
     Uniswap v4 pools (66-character ids) are read through that chain's StateView.
A "no breach" can't be proven from a single block; for that, the coverage and the sample count are
published with each row, and the samples themselves are archived (see README).
Needs: pip install jcs
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import urllib.request

import jcs

STATE_VIEW = {"monad-v2": "0x77395f3b2e73ae90843717371294fa97cc419d64",
              "base-v4": "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71"}
SLOT0 = "0x3850c7bd"            # slot0()             (v3-style pool contract)
GETSLOT0 = "0xc815641c"         # getSlot0(bytes32)   (Uniswap v4 StateView)


def h(obj):
    return hashlib.sha256(jcs.canonicalize(obj)).hexdigest()


def manifests_index(repo, chain):
    idx = {}
    for p in glob.glob(os.path.join(repo, "prereg", chain, "*_preregistered_at_prediction.json")):
        for r in json.load(open(p, encoding="utf-8")).get("rows", []):
            idx[r["record_id"]] = (r, os.path.basename(p))
    return idx


def tick_at(rpc, chain, pool, block):
    if len(pool) == 66:
        to, data = STATE_VIEW[chain], GETSLOT0 + pool[2:]
    else:
        to, data = pool, SLOT0
    req = {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": to, "data": data}, hex(block)]}
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        rpc, data=json.dumps(req).encode(), headers={"Content-Type": "application/json", "User-Agent": "verifier"}), timeout=30))
    if "result" not in r:
        raise RuntimeError(r.get("error"))
    w = int(r["result"][2 + 64: 2 + 128], 16)
    return w - (1 << 256) if w >= (1 << 255) else w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--rpc", default=None)
    ap.add_argument("--max-rpc", type=int, default=20, help="breach rows to check on chain per file")
    a = ap.parse_args()
    fail = 0
    for path in a.files:
        doc = json.load(open(path, encoding="utf-8"))
        chain = doc["chain"]
        repo = os.path.abspath(os.path.join(os.path.dirname(path), "..", "..", ".."))
        body = {k: v for k, v in doc.items() if k != "addendum_hash"}
        errs = [] if doc.get("addendum_hash") == "sha256:" + h(body) else ["addendum_hash does not recompute"]
        idx = manifests_index(repo, chain)
        checked_rpc = 0
        for r in doc["rows"]:
            m = idx.get(r["record_id"])
            if not m:
                errs.append(f"{r['record_id'][:12]}: not in any pre-registration manifest"); continue
            mrow, mfile = m
            diff = [k for k, v in mrow.items() if r.get(k) != v]
            if diff:
                errs.append(f"{r['record_id'][:12]}: differs from {mfile} in {diff[:4]}")
            if mrow["prediction_hash"] != h({k: v for k, v in mrow.items() if k != "prediction_hash"}):
                errs.append(f"{r['record_id'][:12]}: manifest prediction_hash does not recompute")
            ev = r.get("evidence") or {}
            if r.get("status") == "RESOLVED" and "band_tick_lower" in r and "first_breach" in ev:
                fb = ev["first_breach"]
                if bool(fb) != bool(r.get("y")):
                    errs.append(f"{r['record_id'][:12]}: y={r.get('y')} but first_breach={fb}")
                if fb and r["band_tick_lower"] <= fb["tick"] < r["band_tick_upper"]:
                    errs.append(f"{r['record_id'][:12]}: reported breach tick is inside the band")
                if fb and a.rpc and "block" in fb and checked_rpc < a.max_rpc:
                    checked_rpc += 1
                    try:
                        t = tick_at(a.rpc, chain, r["pool"], fb["block"])
                        if t != fb["tick"]:
                            errs.append(f"{r['record_id'][:12]}: on-chain tick {t} at block {fb['block']} != reported {fb['tick']}")
                    except Exception as e:
                        errs.append(f"{r['record_id'][:12]}: RPC check failed at block {fb['block']} ({e}) - archive node?")
        tag = "OK  " if not errs else "FAIL"
        print(f"{tag} {path}  rows={len(doc['rows'])} resolved={doc.get('n_resolved')} incomplete={doc.get('n_incomplete')}"
              + (f" on-chain-checked={checked_rpc}" if a.rpc else ""))
        for e in errs[:20]:
            print("     " + e)
        fail += bool(errs)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
