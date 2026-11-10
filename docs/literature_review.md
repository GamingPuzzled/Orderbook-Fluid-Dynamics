# Literature Review — Order Book Refill as Porous-Media Flow

*Last updated: 2026-11-09. Scope: bounded web + arXiv search (not exhaustive). "Verified" = title/authors checked against arXiv API or publisher record. Items marked ⚠ seen as abstract only.*

## 0. Positioning in one paragraph

The project models how a limit order book (LOB) refills a gap cleared by an aggressive multi-tick sweep, borrowing language from porous-media flow (Darcy, Forchheimer, Bingham). The closest prior art is the **latent order book / reaction–diffusion** programme (Bouchaud and co-authors), **SPDE models of the book** (Cont–Müller and successors), and the **resilience** literature (Obizhaeva–Wang; Large; Xu et al.). Two facts constrain novelty: (i) Darcy's law with constant permeability/viscosity reduces to a linear diffusion equation, which is essentially the latent-book model; (ii) a linear refill rate proportional to the deficit is exactly Obizhaeva–Wang exponential resilience. Novelty therefore cannot rest on the analogy. It rests on a **measurement nobody has made**: the *spatial* refill profile inside the cleared gap at 10–20 ms resolution, and a decomposition of refill into **local transport** (flow from the void edges) versus a **non-local source** (makers posting directly at the new touch).

---

## 1. Continuum / physics models of the order book (closest prior art)

### 1.1 Latent order book and reaction–diffusion
- **Donier, Bonart, Mastromatteo & Bouchaud (2015)**, "A fully consistent, minimal model for non-linear market impact", *Quantitative Finance* 15(7):1109–1121. arXiv:1412.0141. ✔
  Buy/sell "intentions" form a latent book that diffuses and annihilates; reproduces square-root impact; decomposes impact into transient mechanical + permanent informational parts.
  **Relevance:** the latent book obeys a diffusion equation — the same PDE as Darcy flow with constant coefficients. Our H0 must be distinguished from it. Key difference: latent book is *unobserved, low-frequency*; we study the *revealed* book at ms scale, which these authors explicitly say reflects HFT market makers.
- **Mastromatteo, Tóth & Bouchaud (2014)**, "Anomalous impact in reaction–diffusion models", *Phys. Rev. Lett.* 113:268701. arXiv:1403.3571. ✔ Exact solution: reaction front displacement grows as √Q.
- **Mastromatteo, Tóth & Bouchaud (2014)**, "Agent-based models for latent liquidity and concave price impact", *Phys. Rev. E* 89:042805. arXiv:1311.6262. ✔ Limit orders reacting to flow; square-root law robust.
- **Benzaquen & Bouchaud (2018)**, "Market impact with multi-timescale liquidity", *Quantitative Finance*. arXiv:1710.03734. ✔ Finite cancellation/deposition rates; notes pure model's impact decay is too fast. **Relevance:** multiple timescales ↔ our expected two-speed refill (HFT touch vs slower depth).
- **Tóth, Lempérière, Deremble, de Lataillade, Kockelkoren & Bouchaud (2011)**, "Anomalous price impact and the critical nature of liquidity in financial markets", *Phys. Rev. X* 1:021006. arXiv:1105.1694. ✔ Latent liquidity V-shaped, vanishing at price → liquidity "critical".

### 1.2 SPDE models of the book
- **Cont & Müller (2021)**, "A stochastic partial differential equation model for limit order book dynamics", *SIAM J. Financial Mathematics*. arXiv:1904.03058. ✔ Book density centred on mid as SPDE with multiplicative noise; reducible to low-dim Markov process.
  **Gap noted by successors:** ignores market orders (Chen-Shue, Li & Yong 2024, "A limit order book model for high frequency trading with rough volatility", arXiv:2412.16850 ✔). Our sweeps are exactly the market-order shocks these models omit.
- **Keller-Ressel & Müller** — coupled bid/ask SPDEs with free boundary (stochastic Stefan problem). ⚠ exact citation to confirm.
- **Hambly, Kreher & Starovoitovs (2024)**, "Non-negative martingale solutions to the stochastic porous medium equation with sticky behavior", arXiv:2411.05924. ✔ Motivated by SPDE limits of LOBs; sticky boundary models queues that sit at zero. **Only paper found linking the porous-medium equation to LOBs** — cite as mathematical precedent.
- Horst & Kreher (and co-authors): functional limit theorems for LOBs yielding PDE/SPDE limits. ⚠ specific paper to select.

### 1.3 Order book as a fluid; continuum breakdown
- **Yura, Takayasu, Sornette & Takayasu (2014)**, "Financial Brownian particle in the layered order book fluid and fluctuation–dissipation relations", *Phys. Rev. Lett.* 112:098703. arXiv:1401.8065. ✔ Price as Brownian particle in a fluid of order particles; FDR verified on FX data.
- **Yura, Takayasu, Sornette & Takayasu (2015)**, "Financial Knudsen number: breakdown of continuous price dynamics…", arXiv:1508.06024. ✔ Defines a Knudsen number for the book; when Kn → 1 a continuum description fails.
  **Direct threat to the project:** a cleared gap at ms scale may be a non-continuum regime. We must estimate Kn per event *before* fitting a PDE, and keep a discrete-lattice fallback.

### 1.4 Econophysics "Reynolds number"
- **Jakimowicz & Juzwiszyn (2015)**, *Acta Physica Polonica A* 127(3-A). Market Reynolds number for volatility regimes; heuristic thresholds borrowed from pipe flow; no out-of-sample validation. **Relevance:** prior use of the name; our Re_M is event-level and built from microstructure quantities.

---

## 2. Resilience and replenishment (empirical baselines)

- **Large (2007)**, "Measuring the resiliency of an electronic limit order book", *J. Financial Markets* 10(1):1–25. 10-dimensional Hawkes on LSE; in >60% of cases the book does not replenish reliably after a large trade; when it does, half-life ≈ 20 s.
- **Degryse, de Jong, van Ravenswaaij & Wuyts (2005)**, "Aggressive orders and the resiliency of a limit order market", *Review of Finance* 9(2). Euronext; depth/spread dynamics around aggressive orders.
- **Xu, Chen, Xiong, Zhang, Zhou & Stanley (2017)**, "Limit-order book resiliency after effective market orders: spread, depth and intensity", *J. Stat. Mech.* 073404. arXiv:1602.00731. ✔ Spread and depth recover within ~20 best-limit updates.
- **Clapham, Haferkorn & Zimmermann (2020)**, "Does speed matter? The role of high-frequency trading for order book resiliency", *J. Financial Research* 43(4):933–964. HFTs restore the *spread* within seconds; *depth* refill slower and mainly non-HFT. **Relevance:** supports a two-mechanism picture — fast touch posting (source-like) vs slower depth rebuilding (transport-like?).
- **Kempf, Mayston, Gehde-Trapp & Yadav** — resiliency via high-frequency VAR; consistently high in large stocks. ⚠ venue/year to confirm.

### 2.1 Resilience in optimal execution (theoretical null)
- **Obizhaeva & Wang (2013)**, "Optimal trading strategy and supply/demand dynamics", *J. Financial Markets* 16(1):1–32 (NBER w11444, 2005). Book deficit decays exponentially: dD/dt = −ρD. Optimal execution depends on resilience, not static depth.
  **Mapping:** Darcy with refill rate ∝ incentive ∝ deficit ⇒ exponential relaxation. *Our aggregate H0 is OW.*
- **Alfonsi, Fruth & Schied (2010)**, "Optimal execution strategies in limit order books with general shape functions", *Quantitative Finance* 10(2). General/nonlinear resilience.
- **Predoiu, Shaikhet & Shreve (2011)**, "Optimal execution in a general one-sided limit-order book", *SIAM J. Financial Math.* 2.
- **Fruth, Schöneborn & Urusov (2014)**, time-varying depth and resilience, *Math. Finance*.
  **Relevance:** Forchheimer-type nonlinearity = nonlinear resilience; a measured breakdown point feeds directly into these execution models.

---

## 3. Point-process and state-dependent order-flow models (competitors)

- **Huang, Lehalle & Rosenbaum (2015)**, "Simulating and analyzing order book data: the queue-reactive model", *JASA* 110(509):107–122. arXiv:1312.0563. ✔ Queues as Markov system; intensities depend on current queue sizes. **No explicit spatial coupling between levels** — our neighbour-dependence test targets this.
- **Rambaldi, Bacry & Lillo (2017)**, "The role of volume in order book dynamics: a multivariate Hawkes process analysis", *Quantitative Finance* 17(7):999–1020. arXiv:1602.07663. Volume and timing not independent.
- **Bacry, Mastromatteo & Muzy (2015)**, "Hawkes processes in finance", *Market Microstructure and Liquidity* 1(1). arXiv:1502.04592. ✔ Review.
- **Cont, Stoikov & Talreja (2010)**, "A stochastic model for order book dynamics", *Operations Research* 58(3). Queueing model.
- **Smith, Farmer, Gillemot & Krishnamurthy (2003)**, "Statistical theory of the continuous double auction", *Quantitative Finance* 3(6). Zero-intelligence benchmark.
- **Muni Toke (2010)**, "'Market making' behaviour in an order book model and its impact on the bid-ask spread", arXiv:1003.3796. ✔ Orders placed *inside the spread* after market orders — an explicit source-term mechanism.
- Recent: Noble, Rosenbaum & Souilmi (2026), interactive queue-reactive simulator for large-tick assets. ⚠

**Requirement:** our spatial model must beat queue-reactive, Hawkes, and OW-exponential on out-of-sample refill prediction.

---

## 4. Liquidity crises and thresholds (Re_crit, Bingham τ₀)

- **Fosset, Bouchaud & Benzaquen (2020)**, "Endogenous liquidity crises", *J. Stat. Mech.* arXiv:1912.00359. ✔ Feedback from volatility to liquidity → second-order phase transition; non-linear Hawkes processes give "activated" crises without fine-tuning. **Closest theory to Re_crit.**
- **Fosset, Bouchaud & Benzaquen (2020)**, "Non-parametric estimation of quadratic Hawkes processes for order book events", arXiv:2005.05730. ✔ Zumbach-type feedback; markets near criticality.
- ⚠ **Garcia Seuma (2026)**, "Measuring the engine of a liquidation cascade: subcritical branching inside a first-order transition", arXiv:2608.03616. Single author, recent, unrefereed — verify before citing.
- ⚠ **Lim (2026)**, "Two-regime liquidity recovery after a perpetual futures liquidation cascade: evidence from Hyperliquid and the October 10, 2025 event", SSRN 6636998. Minute-level data.

---

## 5. Toxicity / "viscosity" proxies

- **Easley, López de Prado & O'Hara (2012)**, "Flow toxicity and liquidity in a high-frequency world", *Review of Financial Studies* 25(5). VPIN.
- **Andersen & Bondarenko (2014, 2015)**, "VPIN and the flash crash", *J. Financial Markets* 17; "Assessing measures of order flow toxicity and early warning signals for market turbulence", *Review of Finance* 19(1). VPIN's predictive power stems from bulk-volume-classification errors; peaked *after* the Flash Crash. Rejoinder: Easley, López de Prado & O'Hara (2014).
  **Implication:** crypto feeds report aggressor side → use exact signed flow (no BVC). Use **markout-based adverse selection** as primary μ; VPIN as robustness only.
- **Cont, Kukanov & Stoikov (2014)**, "The price impact of order book events", *J. Financial Econometrics* 12(1):47–88. arXiv:1011.6402. ✔ Order-flow imbalance (OFI) — control variable.

---

## 6. Crypto perpetual microstructure

- **Albers, Cucuringu, Howison & Shestopaloff (2025)**, "The market maker's dilemma: navigating the fill probability vs. post-fill returns trade-off", arXiv:2502.18625. ✔ Live experiments on Binance BTC perp; queue position untrackable on L2; best-tier fees taker 1.5 bp / maker −0.5 bp. **Implication:** rebates exist only at top tiers; most makers pay positive fees → the rebate term in P is a distribution over participants, not a constant.
- **Bieganowski & Ślepaczuk (2026)**, "Explainable patterns in cryptocurrency microstructure", arXiv:2602.00776. ✔ Binance perps, 1 s sampling.
- **Wang (2025)**, "Exploring microstructural dynamics in cryptocurrency limit order books", arXiv:2506.05764. ✔
  **Gap:** existing crypto LOB work samples at ≥1 s and focuses on prediction; none studies post-sweep spatial refill at 10–20 ms.

---

## 7. Data facts (verified 2026-11-09)

| Source | Content | Cadence | Cost |
|---|---|---|---|
| Bybit v5 public WS, linear | `orderbook.{1,50,200,1000}` snapshot + deltas; `publicTrade` | 10 / 20 / 100 / 200 ms | free |
| Binance USDⓈ-M WS | diff depth `@depth@100ms` (also 250/500 ms); `aggTrade` | 100 ms min | free |
| Tardis.dev | raw historical L2 + trades, many venues | as recorded | 1st day of each month free, no key |
| data.binance.vision | historical aggTrades, bookTicker | per trade | free |

---

## 8. Comparison table

| Model / paper | Spatial (per level)? | Market-order shocks? | Nonlinear response? | Threshold / regime? | Time scale |
|---|---|---|---|---|---|
| Latent book (Donier et al.) | yes (latent) | meta-orders | √ impact | no | minutes–days |
| Cont–Müller SPDE | yes | no | no | no | seconds+ |
| Obizhaeva–Wang | no (aggregate) | yes | no (exp.) | no | seconds–minutes |
| Alfonsi–Fruth–Schied | no | yes | yes | no | theory |
| Queue-reactive | per queue, no coupling | yes | state-dep. | no | event-level |
| Hawkes (Large; Rambaldi et al.) | by event type | yes | linear/quadratic | crit. (Fosset) | event-level |
| Xu et al.; Clapham et al. | aggregate depth/spread | yes | — | — | updates–seconds |
| **This project** | **yes, inside cleared gap** | **isolated sweeps** | **tested** | **tested (Re_M)** | **10–500 ms** |

---

## 9. Gap and contribution

No paper found (bounded search) that:
1. measures the **spatial refill profile across levels inside a cleared gap** after isolated sweeps at 10–20 ms;
2. separates **local transport** from **non-local source** refill and relates the split to toxicity/volatility;
3. does so on crypto perpetuals with free, reproducible data.

The porous-media vocabulary is new to this setting but is **not itself the contribution**.

## 10. Reviewer risks surfaced

1. Constant-coefficient Darcy ≡ diffusion ≡ latent book / OW → show what is *not* captured by these.
2. Continuum breakdown (Knudsen) at ms scale → test before fitting; discrete fallback.
3. VPIN credibility → markouts primary.
4. Endogeneity: P and q built from same book → predetermined pre-shock P; matched placebo events.
5. L2 only: q is net (adds − cancels − fills); arrivals not separately identified.

## 11. Targeted novelty check for next steps (2026-11-09)

Bounded web search (8 queries) on: multilevel Hawkes, level-by-level replenishment after market
orders, cancel-and-repost, SPDE calibration, non-local/fractional order-book models. ✔ = abstract
fetched; ◐ = seen in search results only.

| Work | What it covers | Overlap with our steps |
|---|---|---|
| Lu & Abergel, QF 18(2):249–264, 2018 (DOI 10.1080/14697688.2017.1403142) ◐ | High-dim Hawkes, exponential kernels, inhibition → nonlinear Hawkes | Event-type dependence; level structure believed best-limits only — **verify full text (HAL hal-01686122)** |
| Bacry, Jaisson, Muzy, QF 2016 ◐ | 8-dim Hawkes: limit/cancel/market at best | Market→limit excitation; best quotes only |
| Lo & Hall, JEDC 61:222–244, 2015 ◐ | VAR impulse responses after shocks; depth beyond best recovers weaker | Aggregate depth by level; no spatial transport test |
| Xu et al., arXiv 1602.00731 ✔ (already §2) | Spread/depth recover in ~20 best-limit updates | Best-level only |
| Ponzi, Lillo, Mantegna, arXiv physics/0608032 ◐ | Placement inside spread after liquidity crises | Closest to "source at touch"; equities, no spatial profile |
| Wyart/Bouchaud-style placement studies (cond-mat/0206280, physics/0509194) ◐ | Unconditional placement-distance power law | Unconditional, not post-shock |
| Benzaquen & Bouchaud, arXiv 1704.02638 ✔ | Fractional reaction-diffusion latent book; sub-diffusion tunes impact decay | **Non-local/fractional PDE exists** (theory, no calibration, no refill) |
| Diana & Gebbie, JCAM 2024, arXiv 2310.06079 ✔ | Fractional-diffusion order book simulation; impulse responses | Simulation only, no data fit |
| Cont & Müller 2021 ✔ (already §1) | SPDE with source term f(x); calibrated to *average* profile | Unconditional; no post-shock dynamics |
| Horst & Kreher, arXiv 2308.00805 ◐ | Second-order LOB approximation, linear drift/diffusion calibrated | Unconditional |
| Nordén (cancellation determinants, FINEC 2018) ◐; Yeo (NYSE) ◐ | Chasing: cancel + resubmit more aggressively; explicit repricing only ~0.9% of cancels in one dataset | Order-level, equities; no level-profile mass balance |

### Verdict per proposed step
1. **Mass balance (cancel vs add, by level, moving frame).** Not found in prior work in this form.
   Cancel-and-chase is known at order level in equities; the event-level spatial conservation
   test separating jump transport from source is new as far as this search shows. L2 cannot link
   individual orders → result is aggregate evidence only.
2. **Separability test.** Standard diagnostic; not a contribution alone.
3. **Post-shock fit of D, ν(t), λ(x,t).** Prior SPDE calibrations are unconditional (average
   profile). Post-shock, time-varying estimation looks new. Fractional/non-local alternative
   must cite Benzaquen–Bouchaud 2017 and Diana–Gebbie 2024 (theory/simulation only → we would be
   first empirical discrimination, if claim survives).

### Defence vs multilevel Hawkes
Hawkes papers found model event *timing* at best limits (or few levels) by type. They do not
measure the spatial depth profile across ~50 levels relative to the moving opposite quote, nor
test local vs non-local vs source transport. Ponzi–Lillo–Mantegna is the nearest empirical
precedent for the source-at-touch reading and must be cited as such.

### Still unverified
Lu–Abergel level structure; Ponzi et al. full findings; Lo–Hall depth-by-level details; exact
venues for ◐ entries. Add to references.bib after full-text check.

## 12. Novelty check: post-sweep withdrawal / repositioning (2026-11-09)

Searches (4): cancellation surges after large market orders; market-maker cancel/reprice after
trades at ms scale; liquidity withdrawal / phantom liquidity in crypto books; resiliency
decomposed into submissions vs cancellations.

| Work | Finding | Overlap |
|---|---|---|
| Malinova & Park, "Modern" Market Makers (2016 WP; IIROC trader-level data, TSX60) ✔ (PDF p.1–2 read) | **Quote fade**: HFT market makers cancel opposite-side quotes (across venues) within ms of a trade; cancellations decline per ms after the trade, mostly done by ~250 ms; 17.6% of trades followed by HFTMM cancellations; latency arbitrage | = our **withdrawal** phase (qualitatively, best quotes, counts). No depth profile, no add/cancel mass balance, no repositioning vs source split |
| Clapham, Haferkorn, Zimmermann, J. Fin. Research 2020 ✔ (already §2) | After large market orders HFTs narrow the spread within seconds with small orders; depth resiliency mostly from non-HFT net provision | Net submissions by trader type; seconds scale; no spatial transport |
| Wuyts 2008 (CFS WP) ◐ | After shocks to spread/depth/book beyond best, several liquidity dimensions deteriorate together | Aggregate VAR; deep-book deterioration ≈ withdrawal, no ms timing |
| Hasbrouck & Saar 2009 ◐ | Fleeting orders: >1/3 of non-marketable limit orders cancelled within 2 s | Unconditional |
| Dahlström et al., Financial Review 2024 ◐ | HFTs cancel more; nearly all limit orders cancelled | Unconditional |
| Large 2007 ◐; Xu et al. 2016 ✔ | Market orders raise limit-order intensity on both sides; recovery in ~20 updates | Best level, intensity |

Verdict: the *existence* of fast post-trade cancellation (quote fade) is known (equities,
best quotes, trader-level data). Not found: (i) a depth-profile mass balance separating
withdrawal, depth-conserving repositioning toward the touch, and net new liquidity; (ii) their
ordering and timing (withdrawal ≈ 50–110 ms → repositioning ≈ 130–360 ms → source ≈ 450 ms);
(iii) on crypto perpetuals at 20 ms. Frame withdrawal as multi-level quote fade and cite
Malinova–Park as the precursor; the contribution is the decomposition and sequencing.

## 13. Deeper novelty check (2026-11-10)

Six extended web searches (refill/cancellation/mass balance; crypto perp millisecond
replenishment; cancel-and-resubmit beyond best; post-shock SPDE calibration; "stimulated refill"
by level; 2025–26 crypto order-level resilience) plus arXiv/Crossref metadata checks.

| Work | Finding | Overlap |
|---|---|---|
| **Bonart & Gould, QF 17(10):1601–1616, 2017** (arXiv 1511.04116) ✔ PDF p.1–6 read | Nasdaq LOBSTER, 5 large-tick stocks: after market orders, net flow at the **best quotes** passes through phases — platform latency (0), response latency (small +), **high-speed reaction** (strong net outflow same side), then **stimulated refill** (net inflow) | **Closest precedent for phase structure.** Best quotes only; any market order (not multi-level sweeps); no depth profile, no deep→near reallocation, no source split. Our withdrawal / source = multi-level analogues. Must be cited in intro + contribution |
| Bechler & Ludkovski, Market Microstructure & Liquidity 3(3–4) 1850006, 2017 ✔ (abstract) | Meso-scale flows; "LOB fade": providers anticipating one-sided flow cancel after executions | Aggregate/volume buckets; supports withdrawal |
| Mahseredjian, arXiv 2511.18117 (2025) ✔ (abstract) | Hawkes-driven book with **migration between neighbouring levels** → diffusion limit (discrete Laplacian); calibration listed as future work | Theory with *local* migration; our out-of-sample fits find no diffusion term → direct empirical counterpoint |
| Gu et al., JSTAT 2013 P04027 ✔ | Cancellation position profiles (Shenzhen) | Unconditional |
| Lim, SSRN 6636998 (2026) ◐ | Hyperliquid, minute data, two-regime recovery after Oct-10-2025 cascade | Minutes–weeks scale; not ms |
| Hambly, Kalsi, Newbould (reflected SPDE limits) ◐ | Micro→macro LOB limits, calibration discussed | Unconditional |

Verdict: phases of net order flow after market orders are **known at the best quotes**
(Bonart–Gould). Still not found: multi-level depth-profile mass balance separating withdrawal,
depth-conserving deep→near reallocation and new liquidity; their timing after multi-level
sweeps; out-of-sample test of local vs non-local continuum terms post-shock; crypto at 20 ms.
Novelty claim narrowed accordingly in paper (contribution paragraph).
