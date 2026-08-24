# Evaluation and Presentation Measurements

![CarryCheck RAG performance summary](assets/performance-summary.svg)

## What Was Measured

The August 7, 2026 presentation reported retrieval and decision results for 10 curated questions. Token efficiency was measured separately with one identical request against `furiosa-ai/Qwen3-32B-FP8`. These are prototype measurements, not a production benchmark or a measurement of the repository's current `gpt-oss-120b` default.

## Retrieval Quality

![Grouped bar chart showing Recall at 3 and MRR for Dense, BM25, and Hybrid retrieval](assets/retrieval-evaluation.svg)

### Exact results

- **Dense —** Recall@3 `1.00` · MRR `0.80`
- **BM25 —** Recall@3 `1.00` · MRR `0.95`
- **Hybrid RRF —** Recall@3 `1.00` · MRR `0.933`, rounded to `0.93` on the slide

### How to read them

**Recall@3** asks whether a relevant rule appeared among the first three results. **MRR** rewards placing the first relevant rule closer to rank one. Every method found a relevant rule within the top three for all 10 questions, while BM25 produced the strongest first-result ranking on this set.

> Hybrid retrieval did not outperform BM25 MRR in this experiment. Its architectural purpose is complementary coverage: embeddings handle paraphrases, while BM25 protects exact numbers, units, and identifiers.

## Decision Integrity

> **100% transport-status match**
> Carry-on and checked-baggage statuses matched the expected result for all 10 questions.

> **10/10 guardrails passed**
> Generated statuses matched deterministic results and every cited source ID belonged to the retrieved evidence.

Retrieval quality and decision correctness were measured separately. Finding the correct rule does not prove that arithmetic, policy gates, or generated explanations were applied correctly; the deterministic engine and Harness cover those later stages.

## Token Efficiency

![Horizontal bars comparing 4,396 full-context tokens with 2,699 agent-loop tokens](assets/token-comparison.svg)

- **Full-rule context:** `4,396` total tokens
- **Agent Loop:** `2,699` total tokens
- **Saved:** `1,697` tokens, or `38.6%`
- **Trajectory:** one `search_rules` call → two iterations → verified status and sources

The comparison used an actual API usage log from one identical request. It supports the design claim that retrieving evidence before generation can reduce context, but it does not establish an average cost, latency, or saving rate.

## Recorded Web Demonstration

### Input

- Asiana Airlines, domestic route, Japan to Japan, no transit country
- Two power banks, each `20,000mAh` at `3.7V`
- Deterministic calculation: `20,000 × 3.7 ÷ 1000 = 74.0Wh` per battery

### Result

- Overall: **conditional**
- Carry-on: **conditional**
- Checked baggage: **prohibited**
- Sources: `ASIANA-POWER-BANK` and `JP-MLIT-POWER-BANK-2026`
- Displayed verification date: August 5, 2026

### Recorded model telemetry

- Model: `furiosa-ai/Qwen3-32B-FP8`
- Usage: `2,557` tokens
- Iterations: `2`

The reasons shown were that `74.0Wh` and two batteries were within the applicable limits, while power banks were prohibited in checked baggage. Conditions included terminal protection, direct carriage, no onboard use or charging, no charging from cabin power, and observable storage outside the overhead bin. Airline approval was shown for the `100–160Wh` band; unreadable capacity markings and additional China-departure requirements were shown as cautions.

The Japan notice was displayed as effective April 24, 2026: no more than two power banks at or below `160Wh`, carry-on only, with onboard storage and use restrictions. The screenshot's `2,557` tokens and the controlled comparison's `2,699` tokens belong to different executions and must not be compared as duplicate runs.

## Limitations

- Only 10 curated questions were evaluated, so the results do not establish generalization to real passenger language.
- The provided presentation did not include raw questions, relevance judgments, or per-query rankings; aggregate retrieval scores cannot yet be reproduced from this repository alone.
- Recall@3 saturation makes the set too small to distinguish retrievers reliably.
- The token result is a single request and varies with model, prompt, evidence, and provider accounting.
- Historical Qwen3-32B-FP8 measurements must not be attributed to the current gpt-oss-120b default.

For the design decisions behind these measurements, see [CarryCheck Architecture](ARCHITECTURE.md).
