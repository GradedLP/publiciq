# Public Artifact Verifier

MIT-licensed (see `LICENSE` in this folder). Four scripts, all standalone. The first three need `pip install jcs`;
`verify_anchor.py` needs only the Python standard library and `git`.

- `verify_addendum_hash.py` — the envelope hash of any artifact (below).
- `verify_manifest.py` — a pre-registration manifest end to end: every row's `prediction_hash`, the
  `batch_root`, the envelope, and that no window opened before its row was created — for the champion
  rows and for any pre-registered challenger rows (`challengers.<model_id>`, e.g. XRPL v2's XV-F1 or
  Market Weather's MW-H1); a challenger row's timing is checked against its champion row's window.
  Legacy pre-v2 manifests (only the solana, sui, xrpl, xrpl-mc and poolwatch chains) publish a redacted
  subset of each row and no envelope hash: for them only the `batch_root` can be checked, and the result
  is `LEGACY`. Any other manifest without an envelope or `batch_root` fails. Rows with no window field
  (e.g. Market Weather pool positions) are reported as timing-unchecked rather than silently passed.
- `verify_outcomes.py` — published outcomes against the rows that were pre-registered, breach-evidence
  consistency, and (with `--rpc <archive node>`) the pool's tick on chain at the reported block.
- `verify_anchor.py` — the XRP Ledger anchors of this repository. It reads every anchor transaction from public XRPL
  nodes, recomputes each anchored commit's `tree_sha256` from your clone, and with `--file <path>` reports the earliest
  ledger close time that proves a file's exact bytes. It is GradedLP's configuration of the open-source verifier in
  [xrpl-git-anchor](https://github.com/GradedLP/xrpl-git-anchor). See `../ANCHORS.md`.

This directory contains a **standalone public verifier** for pre-registration
artifacts published in `prereg/`. It lets an independent third party — with
nothing but this cloned repository — reproduce the `addendum_hash` of every
published artifact and confirm it matches the declared value.

## What the verifier does

For a given artifact JSON file:

1. **Loads** the artifact as a JSON object (native Python types).
2. **Excludes** the top-level `addendum_hash` key from the payload.
3. **Canonicalizes** the remaining object using **RFC-8785 JSON Canonicalization
   Scheme (JCS)** via the `jcs` package.
4. **Hashes** the canonical bytes with **SHA-256**.
5. **Compares** the calculated digest against the declared `addendum_hash`.

If they match → `MATCH`. If they differ → `MISMATCH` (exit code 1).

## Fail-closed behavior

The verifier fails closed (exit code 2) and reports an error (no partial
result) when:

- The file does not exist or cannot be read.
- The JSON is malformed.
- The root value is not a JSON object (e.g., an array or scalar).
- The `addendum_hash` field is missing or not a string.
- JCS canonicalization itself fails (e.g., non-finite floats like `NaN` or
  `Infinity`, which JCS rejects — matching the original hash function's
  safety behavior).

The artifact is **never silently modified** during verification.

## Hash semantics (the recipe)

```python
import json, hashlib, jcs

artifact = json.load(open("artifact.json"))
declared = artifact["addendum_hash"]              # "sha256:<hex>"
payload  = {k: v for k, v in artifact.items()    # exclude addendum_hash
            if k != "addendum_hash"}
canonical = jcs.canonicalize(payload)            # RFC-8785 JCS
calculated = hashlib.sha256(canonical).hexdigest() # SHA-256 hex digest
assert calculated == declared.split(":", 1)[-1]   # MATCH
```

This reproduces the `canonical_row_hash(doc, exclude=('addendum_hash',))`
semantics. The original implementation applies a `to_native()` coercion that
handles numpy scalars and rejects NaN/Inf; for artifacts loaded from JSON,
all values are already JSON-native Python types, so `to_native()` is a no-op.
JCS canonicalization independently rejects non-finite floats, preserving
the same fail-closed safety guarantee without needing numpy.

## Dependencies

- Python 3.8+
- `jcs` (RFC-8785 JSON Canonicalization Scheme) — `pip install jcs`
- `hashlib` (Python standard library)
- `json`, `os`, `sys`, `argparse` (Python standard library)

**No gradedlp dependency. No prereg_hash.py dependency.**

## Usage

```bash
# Verify a single artifact
python3 verify_addendum_hash.py prereg/solana/20260817_140500_sol_verdict_20260813.json

# Verbose output (shows mismatch details)
python3 verify_addendum_hash.py prereg/solana/20260817_140500_sol_verdict_20260813.json --verbose
```

### Verified published hashes

| Chain     | Artifact                                                                             | Declared hash (prefix) |
|-----------|--------------------------------------------------------------------------------------|------------------------|
| SOL       | `prereg/solana/20260817_140500_sol_verdict_20260813.json`                           | `ea032462...`           |
| SUI       | `prereg/disclosures/20260818_120000_sui_acceptance_standard.json`                   | `dbbe0cef...`           |
| XRPL-MC   | `prereg/disclosures/20260819_160000_xrpl-mc_genesis_acceptance_standard.json`     | `bb41474d...`           |

All three reproduce from the public repository alone.
