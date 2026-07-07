# InkTrack Maintenance Rules — Canonical Reference & Decision Memo

**Author:** Claude Opus 4.8 (from a multi-LLM audit + arbitration round)  
**Date:** 2026-07-05 (updated as vendor facts were confirmed)  
**Status:** Canonical source of truth for the eufyMake E1 maintenance/consumption model in
InkTrack. Originated as the final arbitration of a three-LLM review (Claude Opus 4.8, xAI Grok
4.3, GPT-5.5); those individual review documents have been retired (see git history) now that
their conclusions are reconciled here and shipped.

> This memo reconciles the reviews into one implementation-ready decision. Where an earlier
> claim was weakened by later evidence, it sides with the evidence.
>
> **Manufacturer sources:** A = eufyMake blog "Current Maintenance Rules & Future Improvements";
> B = support article "Cleaning and Maintenance Strategy & Update of Specific Ink Consumption";
> C = "Soft White Ink Usage Guide"; D = wiki "Introduction to Cleaning Cartridge" (compartment
> capacities: cleaning 255 ml, moisturizer 125 ml, waste ink 125 ml — one physical cartridge).

> **UPDATE 2026-07-05 — eufyMake support confirmed (resolves D1 / §6.4).** Cleaning and
> moisturizing consumption is **per ink channel**, and the E1 runs **6 active channels at a time**.
> Example given by support: an **Automatic Deep Clean uses 6 × 1.5 ml = 9.0 ml** cleaning solution.
> **Consequences:** (1) my original "under-count" finding is CONFIRMED, at exactly **6×**, not
> "6–7×"; Grok's "shared, dosed once" hypothesis is **wrong**. (2) The `service_liquid_multiplier`
> should default to **×6 (active channel count)**, applied to CLN and ML on every service action
> that draws them.
>
> **UPDATE 2026-07-05 (b) — `FW` clarified (revises D4).** `FW` = **Flexible White**, a distinct
> fabric white ink. It is a **real channel**, but **`W` (normal white) and `FW` (flexible white)
> share the same physical white slot** — only one can be installed at a time. So the machine always
> has **6 active channels**, where the white position is **either `W` or `FW`, never both**. `FW`
> is therefore **not** a phantom channel (my earlier update was wrong); it is a **mutually
> exclusive alternate** to `W`. **Switching whites triggers a flush + refill + calibration of the
> white line** — a real, currently-unmodeled consumption event (see new finding W-SWAP below).

---

## 1. Consensus Findings

All three reviewers effectively agree on the following:

- **Ink values match exactly** and need no change: Flash Clean 0.0002, Medium Clean 0.2, Deep
  Clean 1.5, Ink Injection 1.5 ml/ch (items #1, #2, #3, #8).
- **Trigger logic is already correct**: 10-min idle flash cadence, rolling 72 h / 24 h windows,
  configurable daily run time, and the "already-moisturized ⇒ skip" suppression (items #15, #17,
  #18). Source B confirmed the rolling-window design; the blog's "calendar day" wording is the
  looser source and should be ignored.
- **Extended Shutdown Restart over-counts** (item #14): modeling it as a 15 ml/ch initial fill is
  wrong; a moisturized restart needs an Ink Injection (~1.5 ml/ch). **Unanimous, high confidence.**
- **Initial Startup omits the 4.67 ml/ch cleaning-liquid draw** (item #13). Unanimous.
- **The generic `Ink Injection` preset's `CLN=1.5` is not defensible** (item #9): the spec has
  `CLN=0` post-deep and `CLN=1.83` post-moisturize; a flat 1.5 matches neither.
- **Post-maintenance Ink Injection is unmodeled** (item #10) and is a real under-count of ink.
- **White Ink Flash Cleaning is entirely missing** (item #20) and is a genuine, potentially large
  omission for intermittent-white workflows.
- **Pre-print priming is real but throttled** (item #11): source B's 12 h / restart / resume
  trigger means it is **not** a per-print cost. All three now rank it **below** white flash and
  deferred injection.
- **Double-counting is a first-class risk** (Q5): any automatic/inferred logging must be tagged,
  reversible, and de-duped against manual logs.
- **Channel count / `FW` is unverified** (item #19): do not delete `FW` without hardware
  confirmation.

---

## 2. Disputed Findings

**D1 — Per-channel vs shared reservoir for CLN/ML (the crux, items #4–#7). RESOLVED.**
- Claude (me, original): confident **under-count ~6–7×** based on the literal "per color channel"
  header.
- Grok: leans **shared, dosed once** (InkTrack likely correct), from the repeated 1.83 value and
  single cartridge capacities.
- GPT-5.5: **unresolved**; both arguments are non-decisive; make it configurable and measure.
- **RESOLUTION (eufyMake support, 2026-07-05):** consumption **IS per ink channel**, across
  **6 channels (C, M, Y, K, W, G)**. Example: Automatic Deep Clean = **6 × 1.5 = 9.0 ml** cleaning
  solution. So InkTrack under-counts CLN/ML by **exactly 6×**. My original finding is **confirmed**
  (though I overstated the certainty *at the time*); Grok's shared-dose hypothesis is **refuted**;
  GPT's "make it configurable" is still the right *mechanism*, now with a **known default of ×6**.
  This is the highest-impact fix because it drives CLN/ML refill warnings.

**D2 — Pre-print priming severity.** My original draft over-weighted it; Grok/GPT and my own
updated §4.3 agree it is low priority. **Settled: low priority, 12 h/restart/resume trigger only.**

**D3 — White Ink Flash Cleaning priority.** Grok and GPT rank it **above** priming and near the
per-channel question; my original had it lower. **Settled: high priority.** GPT's point that its
white draw (up to 3 ml) can dwarf priming (0.2 ml) is decisive.

**D4 — `FW` / channel-count priority. RESOLVED (revised).** Grok ranked "verify/drop FW" low; GPT
argued a phantom channel contaminates every event. **RESOLUTION (support): the E1 runs 6 active
channels, and `FW` (Flexible White) is a REAL channel — but it shares the white slot with `W` and
only one white can be installed at a time.** My intermediate "FW is phantom, delete it" call was
**wrong**. Correct handling: model the white position as **`W` XOR `FW`** (6 active channels
always), not 7 simultaneous channels. Per-channel maintenance/ink applies to whichever white is
installed. `GL` = manufacturer **G** (Gloss). **New consequence:** white swaps cause a
flush/refill/calibration event — tracked as **W-SWAP** below.

**D6 — White-line swap event (W-SWAP), newly surfaced and now quantified.** Switching between
`W` and `FW` flushes the white line, refills with the new white, and recalibrates. **Confirmed by
source C (Soft White Ink Usage Guide):** each swap **consumes approximately 30 ml of ink from the
new cartridge** (aided by a dedicated cleaning solution to flush residual old ink) and takes about
**10–15 minutes** to prime (the in-app image cited ~10 min; the written step says ~15 min). This
is a single, flat ~30 ml event, **not** a per-channel value — it applies only to the one white
line. It is **entirely unmodeled** today and is material for anyone who alternates Hard White (`W`,
rigid materials) and Soft/Flexible White (`FW`, fabric/leather/foil-stamping).

> **Terminology (source C):** `W` = **Hard White** (rigid, scratch-resistant; metal/plastic/glass;
> required for crystal/UV-transfer stickers). `FW` = **Soft / Flexible White** (elastic; fabric,
> leather, soft cases; **required for all foil stamping** and soft materials). They are mutually
> exclusive in the single white slot; Soft White prints 3D texture ~50% slower than Hard White.

**D7 — CLN + ML are one physical cartridge; ML capacity was wrong; waste-ink is unmodeled.**
Source D (eufyMake wiki, "Introduction to Cleaning Cartridge") confirms `CLN` and `ML` are **two
compartments of a single physical "UV Cleaning Cartridge"**, which also has a **third compartment:
waste ink**. Verbatim capacities: **Cleaning solution 255 ml, Moisturizer 125 ml, Waste ink
125 ml** (dimensions 174.5×52×113 mm, 745 g).
- **Bug found & fixed:** InkTrack seeded **ML capacity at 500 ml** — 4× the real **125 ml** — which
  overstated moisturizer capacity and delayed low-ML refill warnings. Corrected to 125 ml
  (migration `0020`), and CLN/ML are no longer clobbered by the shared ink-capacity setting.
- **Refill-timing consequence:** because CLN, ML, and waste share one cartridge, the user must
  replace the whole unit when **any** compartment is exhausted (cleaning empty **OR** moisturizer
  empty **OR** waste full). InkTrack currently tracks CLN and ML as two independent cartridges and
  does **not** model waste ink at all — so it can't warn on the true "replace cleaning cartridge"
  trigger. **Deferred to Phase 2** (waste-ink accumulation + unified cleaning-cartridge model).
- **Waste ink:** every cleaning/deep-clean/priming purge drains into the 125 ml waste compartment.
  Its fill rate roughly tracks total CLN + purged-ink volume; modeling it would let InkTrack
  predict cartridge replacement by whichever compartment hits its limit first.

**D5 — Deferred injection modeling scope.** GPT wants it modeled as a **deferred state attributed
to the next project**, not an immediate child of the maintenance event. Grok treats it as a simple
auto-chained log. **Arbitration: GPT's framing is more correct for a COGS tool, but full state
tracking is over-engineering for a manual app.** Compromise: log it as a reviewable pending item,
not silently, not perfectly attributed.

---

## 3. Final Recommendation

Adopt a **staged, reversible** approach. The per-channel question is now **settled (×6)**, so the
CLN/ML correction moves into the near-term work rather than waiting on measurement. Concretely:

1. Ship the unanimous value/preset corrections now (they have no downside).
2. **Apply the confirmed ×6 per-channel multiplier to CLN and ML** on every service action that
   draws them (Deep Clean, Auto Deep Clean, Moisturizing, Safe Shutdown, Initial Startup,
   White Flash). Make the factor a setting (`service_liquid_multiplier`, default = **6**, = active
   channel count) so it stays correct if the channel set ever changes.
3. **Model white as `W` XOR `FW` (6 active channels), not 7 simultaneous.** `FW` is a real but
   mutually exclusive alternate to `W`; do not delete it, but do not count both at once.
4. Add White Ink Flash Cleaning as a manual preset now; add inference later behind a toggle.
5. **Add a White-Line Swap (W-SWAP) event** for `W`↔`FW` changes (flush + refill + calibration);
   volumes TBD from vendor/measurement.
6. Keep all inferred/automatic additions **off by default, tagged, and undoable.**
7. **Migration care:** applying ×6 changes historical CLN/ML depletion. Make the multiplier change
   effective **going forward** (or clearly annotate the change-over) so past cartridge math isn't
   silently rewritten.

Guiding principle (all three reviewers converge here): **for a personal COGS + refill tracker,
prefer reversible, visible, configurable fixes over silent hidden automation.**

---

## 4. Implementation Plan

### Phase 1 — Low-risk preset/value fixes (do now; unanimous)
- **P1.0** **Apply the confirmed ×6 per-channel multiplier to CLN and ML** on every service action
  that draws them, and **model white as `W` XOR `FW` (6 active channels)** — keep `FW` as a real
  but mutually exclusive alternate to `W`, not a 7th simultaneous channel. *(value/logic)*
- **P1.1** Split `Extended Shutdown Restart` from `Initial Startup`; make it an Ink-Injection-style
  event (~1.5 ml/ch ink), not a 15 ml/ch fill. *(value/preset)*
- **P1.2** Fix the generic `Ink Injection` preset: either drop `CLN=1.5` or split into
  `Ink Injection (post-Deep)` = 1.5 ink/ch, no CLN, and `Ink Injection (post-Moisturize)` =
  1.5 ink/ch + CLN (1.83 × 6). *(value/preset)*
- **P1.3** Add the documented **4.67 cleaning-liquid × 6** draw to `Initial Startup`. *(value/preset)*
- **P1.4** Add a **manual White Ink Flash Cleaning** preset (up to 3 ml white + 1.83 × 6 cleaning)
  so users can log it today. *(preset)*
- **P1.5** Confirm/annotate that `Print Head Replacement` genuinely triggers a full 15 ml/ch
  init; if not, correct it. *(value/preset)*
- **P1.6** Add a **White-Line Swap (W-SWAP)** preset for `W`↔`FW` changes: **~30 ml of the new
  white ink** (flat, single-line — NOT ×6) + cleaning solution for the flush; ~10–15 min. Source C
  confirms the 30 ml figure. *(preset)*

### Phase 2 — Inferred/manual logging improvements (behind toggles, reviewable)
- **P2.1** Expose the CLN/ML **multiplier as a setting** (`service_liquid_multiplier`, default = **6**
  = channel count) so the confirmed ×6 stays correct if the channel set changes; make it apply
  going forward, not retroactively. *(schema/config + logic)*
- **P2.2** **Deferred post-maintenance Ink Injection** as a *pending, reviewable* item created
  when an auto Deep Clean / Moisturizing / Safe Shutdown is logged; user confirms at next print.
  *(logic)*
- **P2.3** **Inferred White Ink Flash Cleaning** using project white usage over the last 36 h to
  *suggest* (not silently commit) the event, with de-dupe. *(logic)*
- **P2.4** **Roll up** the many tiny `Automatic Flash Clean` events (144/day idle) into a daily
  aggregate for display; keep exact depletion math. *(UI/logic)*

### Phase 3 — Optional calibration/automation (only if the user wants it)
- **P3.1** Pre-print priming inference on the 12 h / restart / resume rule — manual-friendly,
  de-duped, off by default. *(logic)*
- **P3.2** Optional maintenance-**time** capture (45 min deep, 7m30 moisturize, 4–9 min white) for
  labor/overhead, if the user ever wants time in COGS. *(schema)*
- **P3.3** Change the **default** maintenance time 03:00 → midnight for fidelity. *(cosmetic)*

### Explicitly NOT doing (all reviewers agree)
- A faithful printer state machine for OTA/restart/pause (InkTrack can't observe the device).
- Silent auto-commit of inferred high-volume events.
- Per-print priming multipliers.
- Deleting `FW` before hardware confirmation.

---

## 5. Risks and Double-Counting Controls

- **Tag every non-manual event** with a machine-readable marker (e.g. `[AUTO_INFERRED]` /
  `[AUTO_SCHED]`) so it is distinguishable and filterable.
- **Off by default**: all Phase 2/3 inference ships dark; the user opts in.
- **Review queue, not silent commit**: inferred deferred-injection and white-flash events land as
  *pending* suggestions the user accepts/rejects.
- **De-dupe window**: suppress an inferred event if a matching manual action exists within a
  configurable time window (e.g. ±N hours).
- **One-click undo** on any inferred/auto event (the app already supports action deletion + cache
  invalidation — reuse it).
- **Cartridge-swap boundary**: when a replacement is logged, ensure inferred events that occurred
  before the physical swap are attributed to the correct (old) cartridge window; surface a warning
  if timestamps straddle a replacement.
- **Multiplier changes are non-retroactive by default**: changing `service_liquid_multiplier`
  should not silently rewrite historical depletion; note the change-over point.

---

## 6. Evidence Still Needed (smallest tests to settle assumptions)

1. **Per-channel vs shared (D1) — RESOLVED.** eufyMake support confirmed **per ink channel across
   6 channels (C, M, Y, K, W, G)**; e.g. Automatic Deep Clean = 6 × 1.5 = 9.0 ml cleaning. No
   further test needed; apply ×6 (see P1.0).
2. **Real channel count / `FW` (D4) — RESOLVED (revised).** 6 **active** channels; `FW` (Flexible
   White) is real but shares the white slot with `W` (mutually exclusive). Model white as
   `W` XOR `FW`; do not delete `FW`.
3. **White flash cleaning actuals (D3).** Still worth a one-off observation to confirm the
   "up to 3 ml white + 1.83 × 6 cleaning" figures in practice, but the per-channel basis is now
   confirmed to also apply here.
4. **Vendor question — ANSWERED.** Support confirmed values are **per-channel draws** summed from
   the shared cartridge. D1 is closed.
5. **White-line swap (W-SWAP) volumes — RESOLVED (source C).** Each `W`↔`FW` swap consumes
   **~30 ml of the new white ink** (flat, single white line, not per-channel) plus cleaning
   solution for the flush; ~10–15 min to prime. Only open sub-question: the exact cleaning-solution
   volume of the flush (not stated numerically), if it matters for CLN refill timing.

---

## Prioritized change list (developer-facing)

1. **P1.0: apply ×6 per-channel CLN/ML multiplier + model white as `W` XOR `FW`** — **highest
   impact, now unblocked** (vendor-confirmed). Fixes CLN/ML refill timing; keeps `FW` as a real
   mutually-exclusive white rather than a 7th simultaneous channel.
2. Phase 1 (P1.1–P1.6): remaining preset/value fixes — **ship now** (incl. W-SWAP preset).
3. P2.1 multiplier setting (default 6, forward-effective) — hardens P1.0 against future channel changes.
4. P1.4 manual white-flash preset now; P2.3 inferred white-flash behind a toggle.
5. P2.2 deferred-injection review queue.
6. P2.4 flash-clean roll-up (UI cleanliness).
7. Phase 3 items only on demand.

---

*End of final arbitration. This memo supersedes the individual recommendation orderings in the
three source reviews where they conflict.*
