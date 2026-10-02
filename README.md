## About this repository (updated 2026-10-02)

This is GradedLP's public, append-only pre-registration record: <https://gradedlp.com>.
It began on 2026-07-06 with the XRPL AMM forward test described further down and now carries every
GradedLP stream. Nothing here is ever edited or deleted: a correction is a new, dated artifact.

### What is published, per board

| Path | What it is | When it appears |
|---|---|---|
| `prereg/disclosures/*_standing_acceptance_standard_<board>_sealed.json` | The sealed grading rule for a board | Before that board's first forecast |
| `prereg/<board>/universe/universe.json` | The board's sealed pool list, including excluded pools and why (its sha256 is in the standard and in every forecast row) | — |
| `prereg/<board>/*_preregistered_at_prediction.json` | Each day's frozen forecasts, one row per pool and band, each with its own `prediction_hash`, plus a `batch_root` over the day | Before the forecast window opens |
| `prereg/<board>/outcomes/*_outcomes.json` | Every forecast whose 14-day window has closed: its frozen fields, its outcome, and evidence (first sample outside the band with its block, lowest liquidity, gap to the exchange price, daily tick extremes with their blocks) | The day after the window closes |
| `prereg/<board>/*_verdict_*.json` | Cumulative verdicts under the sealed rule | On the rule's cadence |
| `prereg/disclosures/*` | Addenda and disclosures (corrections, schedules, closures) | Before anything they govern |

Boards: `market-weather`, `sol-v2`, `op-v2`, `xrpl-v2`, `sui-v2`, `avax-v2`, `bsc-v2`, `base-v2`, `base-v4`,
`hyperevm-v2`, `monad-v2`, `poolwatch-v2`. Closed streams (`solana`, `sui`, `xrpl`, `xrpl-mc`, `op-mc`, `poolwatch`)
stay exactly as published. Board pages link straight to that day's files.

### Check it yourself (`pip install jcs`)

```bash
git clone https://github.com/GradedLP/publiciq.git && cd publiciq
python3 verifier/verify_addendum_hash.py prereg/disclosures/<any sealed standard>.json
python3 verifier/verify_manifest.py prereg/bsc-v2/*_preregistered_at_prediction.json
python3 verifier/verify_outcomes.py prereg/bsc-v2/outcomes/*.json --rpc <archive RPC URL>
```

`verify_manifest.py` recomputes every row's `prediction_hash`, the `batch_root` and the envelope, and checks
that no window opened before its row was created. `verify_outcomes.py` checks each outcome against the row
that was pre-registered, checks that its breach evidence is consistent, and with `--rpc` reads the pool's
price on chain at the reported block (this needs an archive node).

### What is not published, on purpose

The model code is private. What is public is enough to check timing, integrity and outcomes: each row
commits to its inputs (`input_sha256`) and every forecast is fixed before its window opens, so a forecast
cannot be changed after the fact even though the code that made it is not shared. Calibration is judged on
the published outcomes alone.

- **Independent timestamps:** every change to `main` is anchored on the XRP Ledger; see [ANCHORS.md](ANCHORS.md).
- **Methods in plain language:** <https://gradedlp.com/methodology.html>. (`METHODOLOGY.md` in this repo is Pool IQ's, kept as published.)
- **Home:** this repository moved from `github.com/sinfun46290-bit/publiciq` to `github.com/GradedLP/publiciq`
  on 2026-09-28. Old links redirect. Files sealed before the move keep the old URL on purpose: changing
  them would change their hashes.
- **License:** Copyright (c) 2026 Nathen Wright, operating as GradedLP. Everything here except `verifier/` is
  [CC BY 4.0](LICENSE): share and adapt for any purpose with credit ("GradedLP, github.com/GradedLP/publiciq").
  `verifier/` is [MIT](verifier/LICENSE).
- Analytics, not financial advice: <https://gradedlp.com/terms.html>.

---

# Pool IQ (XRPL) — Public Pre-Registration & Grade Ledger

**Published 2026-07-06.** This repository is the public, tamper-evident record of a
pre-registered forward test: does a frozen XRPL AMM risk scorer predict realized
14-day net LP return (fees − impermanent loss) out-of-sample?

The **frozen scoring contract** was committed **2026-07-01 as git commit `b6efae7`**
in a **separate private repository**. Only the pre-registration, the verdict-response
protocol, the methodology, and the dated data-audit exhibits are public here; the
scoring implementation is deliberately withheld. **The `b6efae7` hash is verifiable
on request** — it lets anyone confirm the scoring code existed and was frozen before
any outcome resolved, without the code itself being disclosed.

This public repository was created 2026-07-06 to publish the pre-registration; the
frozen scorer it references was committed earlier (2026-07-01) in the private working
repository, which is not public.

## Why this repo exists
To make the prediction impossible to back-fit. Everything here was committed while
the outcome was unknown: the first 14-day cohort closes ~mid-July 2026; the earliest
*powered* verdict is ~mid-August (pre-registered maturity deadline 2026-08-15). The
companion exhibit `exhibits/preflight_2026-07-02.txt` is a read-only data audit run
on 2026-07-02 showing **zero resolved rows** at that date — independent evidence the
predictions predated any resolution.

## The verdict — a frozen A-AND-B gate
The scorer "works" only if **both** legs of a pre-registered dual gate clear, on
cross-sectional IC (Spearman rank IC of predicted vs realized net, per date):

- **Leg A** — overlapping IC, Newey-West HAC (calendar-aware, lag L = 14), one-sided **t ≥ 2.0**.
- **Leg B** — non-overlapping phase sweep: promote in **all** of **≥ 10 of 14** resolvable phases.
- **Quorum** — **≥ 12 pools per date**; underpowered ⇒ **HOLD**, never pass or fail.
- **Verdict = Leg A AND Leg B.** Anything short ⇒ HOLD (underpowered) or FAIL.

(Constant values above are as fixed in `PREREGISTRATION.md`.)

## The freeze model
The scoring pipeline is frozen at `b6efae7`. It is never edited to make a result
pass: any change is a **new model version on a fresh forward clock**, never a
retro-fit. Verdict-day responses (pass / hold / fail) were fixed in advance in
`VERDICT_PROTOCOL.md`. Deviations, if any, are logged as post-hoc and dated.

## Contents
| File | What it is |
|---|---|
| `PREREGISTRATION.md` | The frozen hypothesis, primary metric, pass contract, quorum, universe (committed 2026-07-01). |
| `VERDICT_PROTOCOL.md` | Outcome A/B/C responses, decided before maturity. |
| `METHODOLOGY.md` | Plain-language methodology: tiers, grading, dead-pool imputation, the gate. |
| `exhibits/preflight_2026-07-02.txt` | Read-only data audit, 2026-07-02 — zero resolved rows (prediction-predates-resolution evidence). |
| `exhibits/verdict-inputs-*.json` | Input manifest: SHA-256 + per-table row counts of the graded database snapshot (no database contents published). |

## Verify the published hashes

Every artifact under `prereg/` carries its own `addendum_hash`. It is reproducible
from a fresh clone using only RFC-8785 JSON Canonicalization (JCS) + SHA-256 — no
other dependency. The verifier is a self-contained script in `verifier/`:

```bash
git clone https://github.com/sinfun46290-bit/publiciq.git
cd publiciq
pip install jcs
python3 verifier/verify_addendum_hash.py prereg/solana/20260817_140500_sol_verdict_20260813.json
python3 verifier/verify_addendum_hash.py prereg/disclosures/20260818_120000_sui_acceptance_standard.json
python3 verifier/verify_addendum_hash.py prereg/disclosures/20260819_160000_xrpl-mc_genesis_acceptance_standard.json
```

All three report `MATCH` — `ea032462…`, `dbbe0cef…`, `bb41474d…` respectively.
See `verifier/README.md` for the full hash semantics.

*This is analytics, not financial advice. No capital executor is wired to any tier.*
