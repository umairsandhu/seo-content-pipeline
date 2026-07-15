# AI Search — AEO / GEO

Search is shifting from a list of links to AI-written answers. In early 2026, AI Overviews
appear on 20%+ of Google searches and cut organic CTR ~58% at position 1 (scaling by rank),
and U.S. zero-click searches hit ~68%. Being *cited inside AI answers* is now its own goal.

- **AEO** (Answer Engine Optimization) — be the source an answer engine uses for a direct
  answer.
- **GEO** (Generative Engine Optimization) — appear inside answers a model writes, using your
  page as a reference.

Google's own line: AI features ride the **same core ranking + quality systems** — there's no
separate track. So AEO/GEO ≈ SEO **plus one new requirement: extractability.** Authority,
relevance, and freshness still matter; you additionally make each passage liftable.

## How the engines find you (and what to do)
| Engine | How it sources | Lever |
|---|---|---|
| Google AI Overviews | Retrieves + synthesizes at query time; cites | Rank well + FAQ/HowTo schema + short definitions + visuals |
| Perplexity | Retrieves live; always cites; prefers authoritative + original data | Original data/stats, clear citations, indexed fast |
| ChatGPT / Claude / Gemini | Mostly training data (+ live retrieval for some) | Be published, indexed, and recognized as authoritative *before* training; structured bullets/FAQs get lifted verbatim |

## The GEO checklist (what the tool measures)
1. **Don't block the AI crawlers.** If robots.txt `Disallow: /` for GPTBot / ClaudeBot /
   PerplexityBot / Google-Extended / CCBot, you're opting out of AI visibility.
   → **`audit`** flags this; **`logs`** shows which pages AI bots actually fetch (coverage).
2. **Be renderable.** AI bots are worse at JavaScript than Googlebot — client-rendered content
   can be invisible. → **`audit`** CSR detection; `render.enabled` for accurate SPA audits.
3. **Make every paragraph independently extractable** — front-load the answer, use headings
   and Q&A, keep passages self-contained and fact-rich. → editorial (write this way in
   `draft`); **`score`** shows the subtopics competitors cover that you miss.
4. **Add structured data** — FAQPage/HowTo/Article/Organization. → **`schema`** generates it.
5. **Strengthen E-E-A-T** — named authors, credentials, dates, citations to primary sources,
   original data/stats. → **`eeat`**.
6. **Build topical authority** — comprehensive, well-interlinked clusters. → **`authority`**.
7. **Publish an `llms.txt`** — a curated map for AI assistants (niche, not a Google factor).
   → **`llmstxt`**.

## Measuring AI-search visibility
- **First-party:** Google's Search Console "Generative AI performance" report (impressions in
  AI Overviews/AI Mode). Currently **UI-only — no API yet**, so the tool can't auto-ingest it
  (registered as `ai_search_visibility`, tier *future*). Meanwhile, **`logs` AI-crawler
  coverage** is the available proxy: are the AI bots even fetching your best pages?
- **Prompt tracking (manual/3rd-party):** pick 20–30 buyer prompts, run them across ChatGPT /
  Perplexity / Gemini / AI Overviews monthly, and record which sources get cited. Dedicated
  trackers (Profound, Otterly.ai, Peec AI, AthenaHQ) automate this.

## Timeline
Perplexity indexes fastest, so first citations show there; ChatGPT and AI Overviews follow.
Citation rate typically stabilizes after 3–6 months for the queries you target.

## Bottom line
Get the technical foundation clean (`audit`), unblock and confirm AI-crawler access (`audit` +
`logs`), write extractable + authoritative content (`draft` + `score` + `eeat`), mark it up
(`schema`), and interlink it into topics (`authority`). AEO/GEO is SEO done well, plus
extractability — the tool covers all of it except the (blocked) first-party AI-visibility feed.
