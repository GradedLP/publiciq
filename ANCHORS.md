# XRPL anchors of this repository

Every change to `main` of this repository (and at least one state per day) is timestamped on the
XRP Ledger by a memo transaction from this account, and **only** this account:

| network | account | since |
|---|---|---|
| XRPL mainnet | `rPUig22h1mAiCsiRT2C9TGpqotHGCS8Y3K` | 2026-09-25 |

The same account is declared at <https://gradedlp.com/.well-known/xrp-ledger.toml> and its on-ledger
`Domain` field is `gradedlp.com`. All three must agree.

## What an anchor proves

Each anchor is an `AccountSet` transaction whose memo (type `gradedlp/anchor/v1`, canonical JSON)
names a commit of this repo and `tree_sha256`: a SHA-256 over every file's bytes in that commit
(git's own SHA-1 ids are not collision-safe, so the files are re-hashed). XRPL ledger close times
cannot be backdated. So every file in an anchored commit existed, byte for byte, **no later than**
the close time of the ledger that holds the anchor. Git commit dates are set by the author and prove
nothing; this does.

Anchoring started on the date above. Earlier commits are covered from that date only; their earlier
existence rests on GitHub's push history, not on the ledger.

## Verify it yourself (Python 3 standard library + git; trusts no GradedLP server)

    git clone https://github.com/GradedLP/publiciq.git
    curl -O https://gradedlp.com/anchors/verify_anchor.py
    python3 verify_anchor.py --repo publiciq
    python3 verify_anchor.py --repo publiciq --file prereg/<some file>.json   # earliest proof for that file

Proof index (convenience copy; the ledger is the source of truth): <https://gradedlp.com/anchors/index.json>
