# Outreach kit

## One-page summary (attach as PDF with Figure 1)

**Pulled, moved, then made: how crypto order books refill after liquidity sweeps**
Joel Pulikkan — [university], sophomore · Code: https://github.com/GamingPuzzled/Orderbook-Fluid-Dynamics

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
   - **Withdrawal** (~50–110 ms): deep orders are cancelled, a multi-level version of the
     "quote fade" documented for equities by Malinova & Park.
   - **Repositioning** (~130–360 ms): depth cancelled deep in the book is re-posted near the new
     best quote. It supplies 74–93% of the early rebuild while total depth *falls*
     (added ÷ cancelled = 0.61–0.73, against ≈1.0 at matched placebo times).
   - **New liquidity** (~0.4–0.5 s): only then do additions exceed cancellations.
2. **No diffusion.** In out-of-sample fits of the depth profile, a local diffusion term adds no
   predictive power; a non-local jump term and a delayed source fit the data.
3. **Execution.** A follow-up market order pays 2–3× the normal cost 20 ms after a sweep, but
   about 90% of that excess is gone within 250 ms, during repositioning.
4. **Order-level check (preliminary).** On Bitstamp, about a quarter of near-touch liquidity is
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

I'm a sophomore in [major] at [university]. I have been working independently on how limit
order books refill after large aggressive trades, and given your work on [specific paper or
topic of theirs], I'd be grateful for your view on it.

Using 20 ms order book data for Bitcoin and Ether perpetual futures (about 42,000 events), I
find that refill happens in three ordered phases: market makers first pull deep orders (within
~100 ms), then move existing depth to the new price (~100–350 ms), and only after ~0.4–0.5 s
does new liquidity arrive. Out-of-sample fits show no role for the diffusion term that
continuum order book models assume, and the excess cost of a follow-up trade is mostly gone
within 250 ms. A one-page summary and the main figure are attached; the code is public at
https://github.com/GamingPuzzled/Orderbook-Fluid-Dynamics.

I have a full draft. Would you have 20 minutes in the coming weeks to look at it, or would you
consider advising the project toward a journal submission?

Thank you for your time.

Best regards,
Joel Pulikkan
[university] · joelpulikkan253@gmail.com

---

## Who to email

- Professors in finance, economics, applied math, statistics, operations research or physics
  whose recent papers mention market microstructure, limit order books, high-frequency trading,
  Hawkes processes, stochastic PDEs or econophysics.
- Start at your own university (department pages, Google Scholar). Then try authors of the
  closest papers in the literature review, especially those who work with students.
- Personalise the first paragraph with one specific paper of theirs. Send to 3–5 people at a
  time, and follow up once after about 10 days.
