# Outreach kit

## One-page summary (attach as PDF with Figure 1)

**Pulled, moved, then made: how crypto order books refill after liquidity sweeps**
Joel Pulikkan — [university], sophomore

**Question.** When a large aggressive order wipes out several price levels of a limit order
book, how does the book refill, and where does the new liquidity come from? Continuum models
treat liquidity as a density that diffuses between neighbouring prices; resilience models
describe only the aggregate recovery rate.

**Data.** Free 20 ms level-2 order book and trade data (Tardis.dev) for Bybit BTCUSDT and
ETHUSDT perpetual futures: 85 days from 2023 to 2026, about 42,000 isolated multi-level sweeps,
and 170,000 placebo times matched on volume, volatility and depth.

**Method.** I measure depth relative to the moving opposite quote, which removes the mechanical
price jump. I then decompose every book update in the second after a sweep into additions,
cancellations and fills, which gives a mass balance of the swept side.

**Findings.** Refill happens in three ordered phases, the same for both assets:

1. **Withdrawal** (~50–110 ms): deep orders are cancelled, a multi-level version of the "quote
   fade" documented for equities by Malinova & Park.
2. **Repositioning** (~130–360 ms): depth cancelled deep in the book is re-posted near the new
   best quote. This supplies 74–93% of the early rebuild, while total depth *falls*: added ÷
   cancelled = 0.61–0.74, against ≈1.0 at matched placebo times.
3. **New liquidity** (~450 ms): only after ~140–300 ms do additions exceed cancellations.

There is no sign of diffusion-like flow between adjacent price levels. The evidence points to
continuum models with a non-local jump term, a shock-dependent cancellation rate and a delayed
source.

**Status.** Full pipeline built and tested (Python), results replicated on two assets, draft
paper written. Replications on three more coins and a second exchange are under way.

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
find that refill happens in three ordered phases. Market makers first pull deep orders (within
~100 ms), then move existing depth to the new price (~100–350 ms), and only after ~450 ms does
new liquidity arrive. There is no sign of the diffusion-like flow that continuum order book
models assume. A one-page summary and the main figure are attached.

I have a full draft and tested code. Would you have 20 minutes in the coming weeks to look at
it, or would you consider advising the project toward a journal submission?

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
