# Outreach kit

## One-page summary (attach as PDF with Figure 1)

**Pulled, moved, then made: how crypto order books refill after liquidity sweeps**
Joel Pulikkan — Rutgers University–New Brunswick, sophomore · Code: https://github.com/GamingPuzzled/Orderbook-Fluid-Dynamics

**Question.** When a large aggressive order wipes out several price levels of a limit order
book, how does the book refill, and where does the new liquidity come from? Continuum models
treat liquidity as a density that diffuses between neighbouring prices; resilience models
describe only the aggregate recovery rate.

**Data.** Free 20 ms level-2 order book and trade data (Tardis.dev) for Bybit BTCUSDT and
ETHUSDT perpetual futures: 85 days from 2023 to 2026, about 42,000 isolated multi-level sweeps,
and 170,000 placebo times matched on volume, volatility and depth. Plus a live recording of
Bitstamp's public order-level feed, where every order has an ID.

**Method.** I measure depth relative to the moving opposite quote, which removes the mechanical
price jump, and decompose every book update in the second after a sweep into additions,
cancellations and fills, which gives a mass balance of the swept side.

**Findings.**

1. **Three ordered phases**, the same for both assets:
   - **Withdrawal** (from the sweep on): deep orders are cancelled, a multi-level version of
     the "quote fade" documented for equities by Malinova & Park.
   - **Repositioning** (first ~100 ms, overlapping withdrawal): depth cancelled deep in the book is re-posted near the new
     best quote. It supplies 74–93% of the early rebuild while total depth *falls*
     (added ÷ cancelled = 0.61–0.73, against ≈1.0 at matched placebo times).
   - **New liquidity** (~0.4–0.8 s): only then do additions exceed cancellations.
2. **Model comparison.** Out of sample, a three-phase model (withdrawal + early move pulse with
   mean ~50 ms + delayed source) beats exponential recovery and every model without the move or
   the source. A linear-Hawkes response fits as well and recovers the same two time scales
   (~30–50 ms and ~0.6 s). A queue-reactive model, where flows depend only on the book's
   current state, fails (out-of-sample R² 0.10–0.45): refill depends on time since the sweep.
   A local diffusion term adds no predictive power for the depth profile.
3. **Not driven by information.** The early phases are nearly the same whether the price later
   continues in the sweep's direction or reverts: a generic reaction to the sweep itself, with
   only a modest tilt towards protection after informative sweeps.
4. **Execution.** A follow-up market order pays 2–3× the normal cost 20 ms after a sweep, but
   about 90% of that excess is gone within 250 ms, during repositioning.
5. **Order-level check (preliminary).** On Bitstamp, about a quarter of near-touch liquidity is
   an existing order cancelled deep and re-posted near the touch with the identical amount, so
   "moving" liquidity is routine.

**Status.** Full pipeline (Python, tested, public on GitHub); draft paper written; replications
on SOL, XRP, LINK, Binance and OKX are being processed; Bitstamp order-level recording ongoing.

**What I'm looking for.** A faculty mentor or co-author to review the framing and help prepare
the paper for submission (target: *Quantitative Finance*).

---

## Email template

**Subject:** Undergraduate research on order book refill: looking for feedback or a mentor

Dear Professor [Name],

I'm a sophomore in [major] at Rutgers–New Brunswick. I have been working independently on how limit
order books refill after large aggressive trades, and given your work on [specific paper or
topic of theirs], I'd be grateful for your view on it.

Using 20 ms order book data for Bitcoin and Ether perpetual futures (about 42,000 events), I
find that refill happens in three phases: within the first ~100 ms market makers pull deep
orders and move existing depth to the new price, and only after ~0.4–0.8 s does new liquidity
arrive. A three-phase parametric model beats exponential recovery out of sample, a queue-reactive
model based on the book's state alone fails, the early phases look the same whether or not the
sweep turns out to be informative, there is no role for the diffusion term that continuum order
book models assume, and the excess cost of a follow-up trade is mostly gone within 250 ms. A one-page summary and the main figure are attached; the code is public at
https://github.com/GamingPuzzled/Orderbook-Fluid-Dynamics.

I have a full draft. Would you have 20 minutes in the coming weeks to look at it, or would you
consider advising the project toward a journal submission?

Thank you for your time.

Best regards,
Joel Pulikkan
Rutgers University–New Brunswick · joelpulikkan253@gmail.com

---

## Who to email

- Professors in finance, economics, applied math, statistics, operations research or physics
  whose recent papers mention market microstructure, limit order books, high-frequency trading,
  Hawkes processes, stochastic PDEs or econophysics.
- Start at your own university (department pages, Google Scholar). Then try authors of the
  closest papers in the literature review, especially those who work with students.
- Personalise the first paragraph with one specific paper of theirs. Send to 3–5 people at a
  time, and follow up once after about 10 days.

## Targets (checked 2026-11-10; confirm on each page before emailing)

**Rutgers–New Brunswick (start here; an in-person meeting is easiest)**

| Who | Dept | Why them | Mention |
|---|---|---|---|
| **Bruce Mizrach** (first choice) | Economics | Market microstructure of electronic limit order markets is his current research | "An Empirical Analysis of the Shanghai and Shenzhen Limit Order Books" (with Chung, Gao, Lu, *Economic Modelling*) |
| Xiye Yang | Economics | High-frequency financial econometrics; organised the Rutgers High Frequency Financial Econometrics Workshop | "Testing for mutually exciting jumps and financial flights in high frequency data" (*J. Econometrics* 2018) |
| Norman R. Swanson | Economics | Econometrics; co-edited a special issue on high-frequency financial data | the *Econometrics* special issue on high-dimensional and high-frequency data |
| Paul Feehan | Mathematics | Mathematical finance with PDEs; directs the Mathematical Finance MS | the continuum-model (PDE) section of the paper |
| Tavy Ronen | Finance (Rutgers Business School) | Empirical market microstructure | her microstructure work (pick one paper from her CV) |

Suggested order: Mizrach first, alone. If no reply in 10 days, Yang and Feehan.

**Authors of the closest papers (cite their paper in the first line; verify current affiliation)**

- Michael Ludkovski (UC Santa Barbara): Bechler & Ludkovski (2017), LOB resiliency on the meso-scale; supervises students.
- Martin D. Gould: Bonart & Gould (2017), latency and liquidity provision — the paper ours is closest to.
- Joel Hasbrouck (NYU Stern): fleeting orders; runs the NYU microstructure meeting.
- Gideon Saar (Cornell): fleeting orders, HFT.
- Andreas Park (Toronto) and Katya Malinova (McMaster): quote fade, "Modern" market makers.
- Michael Benzaquen (École Polytechnique) / Jean-Philippe Bouchaud (CFM): latent and fractional order-book models — our PDE result speaks directly to them.
- Tim Gebbie (Cape Town): anomalous-diffusion order-book simulation.

A Rutgers mentor matters most: they can also endorse an arXiv q-fin submission.
