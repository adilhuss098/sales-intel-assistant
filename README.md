# Sales Intelligence Assistant

A 6-step AI pipeline that turns a LinkedIn profile or company description into a specific, grounded commercial intelligence brief.

Built for the Consulting Point AI & Systems Analyst assessment.

## Setup

```bash
cd sales-intel-assistant

# Install dependencies
pip install -r requirements.txt

# Add your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run
streamlit run app.py
```

## Optional enrichment APIs

Without extra keys the tool still works — it uses DuckDuckGo for news and scrapes company websites directly.

For better search quality (Google results), add to `.env`:
```
SERPER_API_KEY=your_key   # free tier at serper.dev — 100 req/day
```

## Test profiles

Three ready-to-use test cases in `test_profiles/`:
- `cfo_series_b.txt` — Marcus Okafor, CFO at Pave (post-Series B, compensation SaaS)
- `vp_sales_enterprise.txt` — Sarah Chen, VP Sales EMEA at Deel (global payroll, $12B valuation)
- `founder_seed.txt` — Tom Ashworth, CEO at Recast (pre-seed, marketing attribution)

## Pipeline architecture

```
Input → Parse → Enrich (web) → Extract (Haiku) → Reason (Sonnet) → Synthesize (Sonnet) → Slop filter (Haiku) → Brief
```

Every insight in the output is grounded in specific evidence. A banned-word list and slop filter remove generic AI language before you see the brief.

## Storage

All briefs saved locally to `history.db` (SQLite). Nothing leaves your machine except Anthropic API calls.
