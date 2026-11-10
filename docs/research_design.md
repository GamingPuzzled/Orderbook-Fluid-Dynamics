# Research Design — Spatial Refill of Swept Order Books

*Version 0.1, 2026-11-09. Companion to `literature_review.md`.*

## 1. Research question

After an isolated aggressive sweep clears L ≥ 3 price levels of a crypto perpetual order book, **where inside the cleared gap does liquidity return, and by which mechanism?**

Two mechanisms, mapped to the PDE

$$\frac{\partial \mathcal V}{\partial t} = \underbrace{\frac{\partial}{\partial x}\Big(D(x,\mu)\,\frac{\partial P}{\partial x}\Big)}_{\text{local transport}} + \underbrace{S(x,t)}_{\text{non-local source}}$$

- **Transport (Darcy-like):** refill propagates in from the gap edges; neighbouring depth matters; refill front advances as τ^γ with γ ≈ ½ (diffusive).
- **Source:** makers post directly at the new touch / chosen levels, independent of neighbours; no propagating front.

**Headline estimand:** the source share
$$\theta = \frac{\int_{\text{gap}} S\,dx\,dt}{\int_{\text{gap}} \partial_t \mathcal V\,dx\,dt}$$
and how θ varies with toxicity, volatility, sweep size, and venue.

**Secondary:** aggregate recovery linear (Obizhaeva–Wang exponential, ≙ Darcy) vs nonlinear (≙ Forchheimer), with a regime threshold indexed by Re_M. Reported as robustness, not headline.

## 2. Hypotheses

| ID | Hypothesis | Test | Figure |
|---|---|---|---|
| H1 | Refill is not purely local transport: θ > 0 | structural fit §6.4 | θ distribution across events |
| H2 | θ rises with toxicity (makers avoid ladder-building, post only at touch when adverse selection high) — sign is open | θ ~ markout + RV + controls | θ by toxicity decile |
| H3 | Refill order is touch-first, not far-edge-first | rank statistic §6.1 | heatmap: level × τ refill fraction |
| H4 | Neighbour depth predicts refill beyond own-level state | spatial panel §6.3 | coefficient plot |
| H5 | Aggregate recovery departs from exponential above Re_crit | §6.6 | % recovered @100 ms by Re_M decile |

Each hypothesis is compared against the baselines in §7.

## 3. Data (zero cost)

**Update 2026-11-09:** Bybit and Binance APIs are geo-blocked from the user's location (HTTP 403 / 451); no circumvention. **Primary data is now Tardis.dev free first-of-month days** (Bybit + Binance futures, 2020 onward, ~75 days/venue): Bybit `orderbook.50` at 20 ms, exchange ts (ms) + local ts (µs). Live recording, if pursued, must use a venue accessible from the user's location (e.g. Coinbase L3 — spot, order-by-order).

**Original primary (now not accessible):** self-recorded Bybit v5 linear perps BTCUSDT, ETHUSDT.
- `orderbook.1` (10 ms, snapshot-only) for touch timing.
- `orderbook.50` (20 ms, snapshot + deltas) for spatial profile.
- `publicTrade` for sweep detection (aggressor side, trade ids).

**Secondary:** Binance USDⓈ-M same symbols — `@depth@100ms` + `aggTrade`. More liquidity → more sweeps; coarser time grid → cross-venue robustness at τ ≥ 100 ms.

**Development:** Tardis.dev first-of-month free days (Bybit, Binance) to build the pipeline before own recording accumulates.

**Recorder spec (to implement):** asyncio WebSocket client; record exchange ts, local receive ts (µs, `time.time_ns()`), sequence `u`/`seq`; detect gaps → resubscribe for snapshot; write hourly Parquet partitions `venue/symbol/date/hour`; run on a machine with NTP/chrony sync; log reconnects and drop counts. **Start week 1** — data accrues in real time; aim ≥ 8 weeks before estimation.

**Data-quality table (paper appendix):** message drop rate, median/99p exchange→local latency, snapshot resyncs, share of events overlapping a resync (excluded).

**Equity benchmark:** deferred (paid data) — future work.

## 4. Event definition

1. **Candidate sweep:** consecutive aggressor trades on same side sharing exchange timestamp (or within 1 ms with consecutive trade ids) whose price range spans ≥ 3 ticks.
2. **Book confirmation:** each level in the range had positive depth in the last pre-sweep book and zero (or below 5% of pre-level) in the first post-sweep book.
3. **Size filter:** sweep volume ≥ 95th percentile per symbol-month.
4. **Isolation:** no other candidate sweep in the preceding 500 ms; no resync/gap in [−1 s, +1 s].
5. **Frames:** x measured in ticks relative to **pre-shock** mid (fixed frame, primary) and to post-shock mid (moving frame, robustness).
6. **Observation grid:** τ ∈ {20, 40, 60, 100, 250, 500 ms, 1 s}. 20 ms = `orderbook.50` push interval; shorter offsets only repeat the pre-shock state (verified on data, §14). Book and trades aligned on the **exchange clock** (monotone in Tardis Bybit data); pre-shock state = book strictly before t₀; clearing confirmed at τ = 20 ms.
7. **Power:** report event counts per venue × symbol × month; require ≥ 200 events per Re_M decile for decile analyses.

## 5. Variables (operational)

| Symbol | Definition | Units | Source |
|---|---|---|---|
| 𝒱(x,τ) | resting depth at level x, time τ after shock | contracts | book |
| q(x,τ) | [𝒱(x,τ+Δτ) − 𝒱(x,τ)]/Δτ — **net** flux (adds − cancels − fills) | contracts/ms | book |
| P(x) | half-spread(x) + fee/rebate(tier mix) − AS(x,h) | bp | see below |
| AS(x,h) | mean signed mid markout at horizon h after fills at distance x, estimated on **pre-event** rolling window | bp | trades + mid |
| ρ | pre-shock depth density: mean depth per tick over ±N levels, t₀−100 ms | contracts/tick | book |
| μ | primary: AS(1, 1 s) over 5-min pre-window; robustness: VPIN (exact signed flow), RV | bp | trades |
| k | tick / (latency proxy × σ_tick); latency proxy = median exchange→local delay | dimensionless | feed |
| v_sweep | ticks cleared / sweep duration (floor 1 ms) | ticks/ms | trades |
| L_gap | ticks cleared | ticks | trades/book |
| Re_M | ρ · v_sweep · L_gap / μ (units reported; dimensionless after normalising by pre-window medians) | — | derived |
| Kn | mean free path proxy / L_gap; free path = mean inter-order spacing in ticks at τ | — | book |

Horizons h ∈ {1 s, 5 s, 30 s} for AS sensitivity. Fee term: published tier schedule; report results at retail tier and top-maker tier.

## 6. Tests

### 6.1 Refill order
For each event, first-refill time T_x = min{τ : 𝒱(x,τ) > ε·𝒱_pre(x)} for x in gap (x=1 nearest new touch … x=L far edge). Statistic: Spearman ρ_s between x and T_x.
- Transport from far edge ⇒ ρ_s < 0 (far levels first).
- Source at touch ⇒ ρ_s > 0.
Aggregate: distribution of ρ_s; sign test.

### 6.2 Front speed
Define front x_f(τ) = deepest-into-gap level with ≥ ε refill. Fit log x_f = a + γ log τ per event (pooled with event FE). γ≈½ diffusive, γ≈1 ballistic, γ≈0 (jump then flat) ⇒ source.

### 6.3 Neighbour dependence (discrete Laplacian)
Panel over (event, x, τ):
$$q_{x,\tau} = \alpha_e + \beta_1 \mathcal V_{x,\tau} + \beta_2\,(\mathcal V_{x+1,\tau} - 2\mathcal V_{x,\tau} + \mathcal V_{x-1,\tau}) + \beta_3\,\mathbb 1[x=\text{touch}] + \gamma' Z + \varepsilon$$
β₂ > 0 ⇒ transport. β₃ captures touch source. SE clustered by event; FE by event.

### 6.4 Structural decomposition
Discretised model per event: 𝒱_{x,τ+Δ} − 𝒱_{x,τ} = Δ·[D Δ²_x P_{x,τ} + S_x(τ)], with S parametrised (e.g. S_x(τ) = s₀ e^{−λτ} φ(x), φ concentrated at touch). Estimate (D, s₀, λ) by nonlinear least squares; compute θ. Validate on simulated books with known θ (§9).

### 6.5 Continuum check (run first)
Compute Kn per event and τ. If median Kn ≥ 0.3 at τ ≤ 40 ms, report §6.3 discrete version as primary and restrict PDE fits to τ where Kn < 0.3.

### 6.6 Aggregate recovery (secondary)
R(τ) = Σ_gap 𝒱(x,τ)/Σ_gap 𝒱_pre(x). Fit exponential (OW) vs nonlinear (power/Forchheimer-type) recovery; compare by AIC and out-of-sample RMSE. Recovery @100 ms by Re_M decile; locate Re_crit via segmented regression (Hansen 2000 threshold test, bootstrap CI). Bingham τ₀: threshold regression of q on ∇P_pre.

## 7. Baselines (must beat out-of-sample)

1. **OW exponential** — aggregate only, no spatial structure.
2. **Queue-reactive** (Huang–Lehalle–Rosenbaum) — per-level intensities from own queue, no neighbour coupling.
3. **Pure diffusion** (latent-book analogue, θ = 0).
4. **Hawkes** with level-specific kernels (if time permits).
Metric: RMSE of 𝒱(x,τ) over held-out months.

## 8. Identification

- P and q from the same book ⇒ mechanical correlation. Use **pre-shock P** (predetermined at t₀) to explain post-shock q.
- **Placebo events:** random non-sweep timestamps matched on depth, spread, RV; apply identical pipeline; θ, γ, β₂ should differ from real events.
- **Heterogeneity is descriptive**, not causal, unless a natural experiment (tick-size / fee change on Bybit or Binance) falls inside the sample — check exchange announcements.

## 9. Validation by simulation

Build a synthetic LOB generator with tunable transport D and source θ (queue-reactive engine + neighbour coupling + touch source). Inject sweeps; run full pipeline; confirm estimators recover θ, γ, β₂ within tolerance and that 20 ms sampling does not bias them. Do this before touching real data.

## 10. Robustness

Venue (Bybit vs Binance), symbol (BTC vs ETH), buy vs sell sweeps, time-of-day (Asia/EU/US), volatility regime, fixed vs moving frame, ε threshold, size percentile (90/95/99), isolation window (250/500/1000 ms), fee tier assumption, markout horizon h.

## 11. Threats to validity

- Hidden/iceberg orders: refill may be revealed hidden depth, not new posts.
- Spoofing / flickering quotes inflate transient refill → require persistence ≥ 2 snapshots.
- Feed drops concentrated during sweeps → exclude events near resyncs; report share.
- L2 aggregation: cannot separate add vs cancel at a level.
- Liquidation-engine orders (forced flow) mixed into sweeps → flag sweeps coinciding with liquidation stream messages (Bybit `allLiquidation`, Binance `forceOrder`); report separately.

## 12. Timeline

| Month | Work |
|---|---|
| 1 | Recorder live (week 1); Tardis free-day dev data; book reconstructor; synthetic simulator |
| 2 | Sweep detector + event panel; Knudsen check; refill order & front-speed stats |
| 3 | Spatial panel, structural θ, baselines, robustness |
| 4 | Writing; figures (refill heatmaps, θ by toxicity, front-speed exponents); arXiv q-fin.TR + SSRN |

## 13. Fixes to original prototype code

- `group_by_dynamic` with fixed 5 ms buckets splits sweeps at bucket edges → group by aggressor run (shared ts / consecutive trade ids).
- Hardcoded tick 0.1 → read per-symbol tick from exchange instrument info.
- `pl.count()` deprecated → `pl.len()`.
- `curve_fit` model lacked intercept α₀ and clustered SEs → use statsmodels / linearmodels with event clusters.
- No book confirmation of cleared levels → add §4 step 2.

## 14. Preliminary diagnostics (Bybit BTCUSDT, 2026-10-01, one day — descriptive only)

Pipeline: `lobflow download → convert → events`. 26.3 M book updates, 1.48 M trades, 418,822 aggressor runs, 70,192 runs spanning ≥ 3 price levels, **1,777 isolated sweeps ≥ Q0.95**; 789 (44%) with ≥ 95% of pre-shock gap levels confirmed empty at τ = 20 ms (median cleared fraction 0.93).

| τ (ms) | 20 | 40 | 60 | 100 | 250 | 500 | 1000 |
|---|---|---|---|---|---|---|---|
| Gap ticks occupied, swept side | 2.5% | 3.6% | 4.1% | 4.2% | 4.8% | 5.4% | 6.2% |
| Gap ticks occupied, opposite side | 16.6% | 18.9% | 19.3% | 21.2% | 21.4% | 21.6% | 21.5% |
| Median mid move / L_gap (sweep direction) | 1.46 | 2.27 | 2.47 | 2.53 | 2.65 | 2.58 | 2.55 |

Gap = tick span touch → deepest traded price (median 59 ticks; median 18 of those ticks had resting depth pre-shock — BTC book is sparse at 0.1 tick).

**Implication — reframe required.** The mid moves past the cleared gap within one push and keeps going; the gap is overtaken, not refilled. In the fixed (pre-shock) frame, the refill-order statistic (§6.1) shows "far-edge-first" in 90% of events, but this is geometric: the far edge *is* the new touch. The fixed frame therefore cannot separate transport from source.

**Proposed change (pending decision):** measure refill in the **moving frame** — depth profile at distance d = 1..D ticks behind the *current* best quote on the swept side, relative to a matched pre-shock profile. Transport ⇒ profile rebuilds from deep levels inward; source ⇒ near-touch levels first. Also condition on continuation vs reversal (mid at 1 s vs mid at 20 ms) and test whether isolation should also require no follow-on sweep (forward-looking window) — mind look-ahead bias if used as a filter rather than a covariate.

Caveats: one day; isolation is backward-looking only; aggressor runs merge same-ms taker orders; Spearman uses crude censoring (unrefilled = 2000 ms).

## 15. Moving-frame results — Bybit BTCUSDT, 42 days (2022–2026 free days with 20 ms / 50-level feed)

25,428 confirmed sweeps (cleared fraction ≥ 0.95, of 47,793 detected); 84,000 placebo times (no large sweep within ±2 s). 35 days (2020–22) excluded: older 25-level feed, 20–60 ms pushes, 0.5 tick. Full tables: `results/bybit/BTCUSDT/summary.md`.

**Shock-specific (placebo R = 1.00 ± 0.01 in every cell):**
1. **Touch depletion and fast refill.** R(d=1) = 0.19 at 20 ms (below 1 on all 42 days; day median 0.17), 0.63 at 40 ms (day-cluster 95% CI 0.58–0.68), 0.91 at 100 ms (0.84–0.99), 1.14 at 1 s (1.08–1.22, overshoot). Half-life ≈ 30–40 ms.
2. **Synchronous over-posting behind the touch.** R(d=2–5) = 1.75 at 40 ms (CI 1.47–2.05; > 1 on 88% of days), similar at d = 6–50, then relaxing to ≈ 1.2 by 250 ms. The peak occurs at the same τ at all distances — no inward-propagating front.
3. **Book translation.** By 40 ms both best quotes have moved ≈ 85 ticks in the sweep direction (opposite side advances as far as the swept side retreats); spread is +2 ticks at 20 ms and back to median pre-shock by 40 ms. P(one-tick spread) 0.22 → 0.43 (40 ms) → 0.51 (1 s) vs placebo 0.53.

**Not shock-specific (fails placebo):** the half-recovery *order* (touch before deeper ticks: 57–60% vs 16–19% after sweeps) is also seen at placebo times (67% vs 8%). Single deeper ticks are routinely empty in BTC's sparse 0.1-tick book and the touch is always replenished because it defines the quote. **This statistic does not discriminate transport from source and is dropped as evidence.**

**Interpretation for the porous-media hypothesis.** In the moving frame the only depleted region is the touch itself; levels 2–50 are not depleted at any τ. There is therefore no depleted medium for a Darcy-type front to propagate through. Observed dynamics = (i) price relocation of ≈ 1.5× the gap, (ii) touch refill on a ≈ 30–40 ms timescale, (iii) broad, synchronous, transient over-posting. This is better described by a source term S(x,t) with wide spatial support than by local transport. **Current evidence does not support Darcy transport as the refill mechanism.**

**Caveats / open checks.**
- **Composition vs new posting:** part of R > 1 behind the touch may be surviving deep liquidity that is now near the new touch (book thickens with distance). The rise from 20 → 40 ms and decay after suggest new posting, but a price-level decomposition (surviving vs new depth) is needed.
- Placebo is time-matched only, not state-matched (sweeps may occur in thicker books / higher activity).
- Ratio-of-sums weights large-depth events; event-bootstrap CIs in parquet ignore within-day correlation (day-cluster CIs above for key cells).
- 20 ms sampling bounds t½ resolution; one venue, one symbol.

### 15.1 Surviving vs new depth (resolves the composition caveat)

L2 bound per absolute price: surviving ≤ running minimum of depth since the pre-shock book; new ≥ depth − that minimum. Cells where the pre-shock price was observed only (60–80% of post-shock depth at d ≤ 20; 32–41% at d = 21–50).

| d | R_new 20 ms | R_new 40 ms | R_new 1 s | placebo R_new 40 ms | placebo R_new 1 s | R_surv 20 ms | R_surv 1 s |
|---|---|---|---|---|---|---|---|
| 1 | 0.09 | 0.50 | 1.23 | 0.03 | 0.26 | 0.09 | 0.15 |
| 2 | 0.16 | 0.61 | 0.89 | 0.04 | 0.20 | 0.77 | 0.41 |
| 3–5 | 0.22 | 0.74 | 0.95 | 0.05 | 0.22 | 0.69 | 0.43 |
| 6–10 | 0.16 | 0.67 | 0.95 | 0.05 | 0.23 | 0.88 | 0.39 |
| 11–20 | 0.12 | 0.48 | 0.80 | 0.05 | 0.24 | 0.93 | 0.56 |
| 21–50 | 0.07 | 0.33 | 0.82 | 0.03 | 0.20 | 0.91 | 0.53 |

**Findings.**
1. At 20 ms, depth behind the new touch is mostly **pre-existing** orders that were deep before the shock (composition). The 20 ms R > 1 is largely mechanical.
2. Between 20 and 40 ms, **new** depth arrives at every distance d = 1–50 simultaneously, at 10–15× the placebo rate, peaking at d = 3–10. The 40 ms over-posting is genuine new liquidity, not composition.
3. Over 1 s, surviving depth falls to ≈ 0.4–0.55 of the pre-shock profile while new depth rises to ≈ 0.8–0.95 (placebo ≈ 0.2): post-sweep book turnover ≈ 4× normal.
4. The touch (d = 1) is rebuilt almost entirely from new orders.

**Implication.** Refill is a burst of new posting with broad spatial support, 20–40 ms after the shock (≈ one push interval plus maker reaction latency), not propagation from surviving deep liquidity. Strengthens the source-term (S(x,t)) reading over Darcy transport. Bounds are conservative: 20 ms sampling misses cancel-and-repost within a push, so true new depth is ≥ the reported R_new.

**Next:** state-matched placebo; ETHUSDT and Binance futures replication; 2020–22 feed as coarse robustness; publication figures.

### 15.2 Mass balance: gross add / cancel / fill flows (2026-11-09)

Module `flows.py`; CLI `lobflow flows`; 42 main-sample days; sweeps with cleared ≥ 0.95 vs
placebo. Every L2 message in [t0, t0+1 s) classified as add / cancel / fill (matched to trades) /
edge_in / edge_out (top-50 window artefacts). Fractions of pre-shock swept-side depth, pooled;
95% day-cluster CIs.

| window (ms) | add | cancel | κ = add/cancel | κ placebo | excess near (d≤5) net build | excess far (11–50) net depletion | cover |
|---|---|---|---|---|---|---|---|
| 20–40 | 0.24 | 0.30 | 0.80 [0.73, 0.88] | 1.05 | 0.053 | 0.032 | 0.60 [0.36, 0.88] |
| 40–100 | 0.45 | 0.50 | 0.91 [0.86, 0.96] | 1.04 | 0.109 | 0.068 | 0.62 [0.53, 0.73] |
| 100–250 | 0.72 | 0.72 | 1.00 [0.96, 1.04] | 1.03 | 0.105 | 0.075 | 0.71 [0.58, 0.91] |
| 250–1000 | 2.32 | 2.09 | 1.11 [1.10, 1.13] | 1.03 | 0.446 | 0.193 | 0.43 [0.39, 0.47] |

Including all non-near zones (6–10, 11–50, 51+), excess depletion elsewhere covers the excess
near-touch build-up ≈ 2.1× (20–40), 1.4× (40–100), 1.1× (100–250), 0.5× (250–1000).
Per-event Spearman ρ(near add, far cancel): sweeps 0.32–0.36 vs placebo 0.18–0.30 (≤ 250 ms).

Reading: in the first ~250 ms the touch is rebuilt while the swept side as a whole *loses*
depth (κ < 1): near-touch posting is fully funded by cancellations deeper in the book —
consistent with non-local repositioning (cancel deep, repost near), not net injection.
Net injection (κ > placebo, near build-up exceeding deep depletion) appears only at
0.25–1 s. Mixed model: early phase ≈ conservative jump transport, later phase adds a source.

Caveats: (i) L2 cannot link orders — balance ≠ same orders moving; (ii) fill matching covers
71% of swept-side traded volume (0.66 vs 0.92 of pre depth); unmatched sweep volume could be
misfiled as 20–40 ms cancels and bias κ down there — 40–100 and 100–250 ms windows are not
affected (traded ≤ filled) and still give κ ≤ 1; (iii) 20 ms netting understates gross
churn; (iv) ambiguous cancel-deepest + post assigned to edge_out (κ_lo bound reported).

### 15.3 Fill-matching fix and state-matched placebo (2026-11-09)

Diagnosis (2025-03-01): 33% of sweep volume exceeds displayed pre-shock size at its price
(hidden/iceberg or posted after the last push); this volume never appears as a removal.
Uncapped, it stayed in the fill pool and relabelled later genuine cancels as fills. Fix: pool
capped at displayed size. Effect: κ 20–40 ms 0.80 → 0.74 [0.68, 0.80]; 40–100 0.91 → 0.87
[0.82, 0.91]; 100–250 1.00 → 0.99 [0.95, 1.02]; 250–1000 1.11 (unchanged). Conclusion stronger.

State-matched placebo: within-day coarsened exact matching on quartiles (of that day's sweeps)
of 10 s volume, 60 s realised variation, pre-shock swept-side depth. Support 100%. Balance
(sweep / raw placebo / matched): vol_10s 28.9 / 9.0 / 24.9; rv_60s 0.0028 / 0.0014 / 0.0024;
depth 19.2 / 32.3 / 26.7 (sweeps hit thinner books; quartile bins leave residual imbalance).

| window | κ sweep | κ matched placebo | excess near build | excess far depletion | cover |
|---|---|---|---|---|---|
| 20–40 | 0.74 | 1.05 | 0.050 [0.045, 0.056] | 0.038 | 0.76 [0.50, 1.04] |
| 40–100 | 0.87 | 1.07 | 0.096 [0.079, 0.113] | 0.071 | 0.74 [0.62, 0.90] |
| 100–250 | 0.99 | 1.04 | 0.083 [0.060, 0.106] | 0.067 | 0.81 [0.62, 1.12] |
| 250–1000 | 1.11 | 1.04 | 0.324 [0.264, 0.377] | 0.130 | 0.40 [0.34, 0.45] |

Matched-placebo R_new at 40 ms: 0.04–0.09 (sweeps 0.33–0.74); at 1 s: 0.31–0.44 (sweeps
0.8–1.2). Two-phase reading survives state matching: early refill funded by deep
cancellations (κ < 1 vs ≈ 1.05 in matched calm), net source only after ~250 ms (κ 1.11 vs 1.04).
Next: finer matching (deciles / continuous propensity) for depth balance.

### 15.4 Replication: Bybit ETHUSDT (2026-11-09)

43 main-sample days (2023-05 → 2026-11), 42,622 sweeps (16,752 cleared ≥ 0.95), 86,000 placebo.
Same pipeline, same parameters.

| window | κ sweep | κ placebo (matched) | excess near build | excess far depletion | cover (matched) |
|---|---|---|---|---|---|
| 20–40 | 0.61 [0.56, 0.66] | 1.01 | 0.028 | 0.067 | 2.38 [1.71, 3.33] |
| 40–100 | 0.85 [0.81, 0.89] | 1.00 | 0.056 | 0.071 | 1.26 [1.01, 1.62] |
| 100–250 | 1.12 [1.08, 1.16] | 1.03 | 0.047 | −0.005 | ≈ 0 |
| 250–1000 | 1.09 [1.07, 1.11] | 1.03 | 0.110 | −0.003 | ≈ 0 |

R_new at 40 ms: 0.21–0.87 (matched placebo 0.03–0.16); touch R 0.53 at 40 ms, 0.84 at 1 s.
Two-phase pattern replicates and is sharper: repositioning phase (κ < 1, deep depletion ≥ near
build-up) then source phase (κ > placebo, no deep depletion). Phase switch earlier on ETH
(~100 ms) than BTC (~250 ms). Touch over-recovery at 1 s is BTC-specific (ETH 0.84).

### 15.5 Three-component refill model (2026-11-09)

Module `model.py`, CLI `lobflow model`. Fine flow grid (20 ms steps to 100 ms, then
140/200/300/450/650/1000), excess vs state-matched placebo. Per window: near (d ≤ 5) net
build-up N and deep net depletion J are split into **transport** T = min(N, J) (repositioning,
depth-conserving), **withdrawal** W = J − T (liquidity leaves the book), **source**
S = N − T (new liquidity). Nonparametric over observed 20–1000 ms; day-cluster CIs. Gamma-pulse
fits were tried and dropped as headline: masses are not identified outside the observed
range (extrapolated into 0–20 ms; BTC transport continues past 1 s).

| (fractions of pre depth) | BTC deep d>5 | BTC deep 6–50 | ETH deep d>5 | ETH deep 6–50 |
|---|---|---|---|---|
| transport < 250 ms | 0.19 [0.16, 0.21] | 0.15 | 0.09 [0.07, 0.11] | 0.09 |
| withdrawal < 250 ms | 0.22 [0.18, 0.25] | 0.04 | 0.20 [0.17, 0.25] | 0.08 |
| source < 250 ms | 0.01 | 0.05 | 0.02 | 0.03 |
| source > 250 ms | 0.21 | 0.17 | 0.12 | 0.10 |
| transport share of near build-up < 250 ms | 0.93 [0.89, 0.97] | 0.74 [0.66, 0.83] | 0.81 [0.73, 0.86] | 0.78 [0.73, 0.84] |
| centroid: withdrawal / transport / source (ms) | 69 / 322 / 507 | 109 / 357 / 451 | 47 / 133 / 449 | 58 / 202 / 415 |
| switch (source > transport thereafter) | 140–200 (CI) | 200–300 | 140 [100, 140] | 140 |

Sequence after a sweep: **withdrawal** (≈50–110 ms; mostly far stale orders d > 50 on BTC)
→ **transport/repositioning** of deep depth to the touch (supplies 74–93% of near-touch
build-up before 250 ms) → **source** (new liquidity, centroid ≈ 410–510 ms, 85–95% of its mass
after 250 ms). Ordering robust to deep-zone definition and asset. BTC transport has a second
rise at 650–1000 ms (switch undefined in point estimate).

PDE reading: ∂ρ/∂t = ∫K(x,y,t)[ρ(y) − ρ(x)]dy (non-local jump kernel, early) − ν(x,t)ρ
(withdrawal) + S(x,t) (delayed source); no evidence for a local Darcy/diffusion term.

### 15.6 Figures and withdrawal novelty (2026-11-09)

`scripts/figures.py` → `figures/fig1_three_phases`, `fig2_mass_balance`,
`fig3_recovery_heatmap` (PNG + PDF; BTC and ETH; rerun with `--assets` once SOL/XRP/LINK land).
Fig 1 plots rates, so the late source looks small though its integrated mass (0.12–0.21 of
pre depth) is comparable to early transport — state this in the caption.
Withdrawal phase = multi-level "quote fade" (Malinova & Park 2016); cite as precursor
(literature_review §12). Contribution = decomposition + sequencing, not the existence of fades.
