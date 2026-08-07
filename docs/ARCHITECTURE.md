# CarryCheck Architecture

## Design Forces

Airline baggage guidance combines semantic language, exact numerical limits, carrier-specific approval, departure security, and destination law. A single generative prompt cannot reliably preserve all of those boundaries, and a single retrieval method is weak either at paraphrases or at exact units. CarryCheck therefore uses application-controlled orchestration: retrieval selects evidence, deterministic engines own statuses, and the LLM owns wording only.

## Component Decisions

### 1. Validation and Structured Item Parsing

**Why:** A threshold engine cannot distinguish `20,000mAh` safely without voltage, and values such as `NaN`, infinity, or unsupported fields can bypass ordinary comparisons.

**Role:** The HTTP layer validates the request shape and accepted overrides. The domain parser extracts item type, route, `mL`, `mAh`, `V`, `Wh`, weight, quantity, battery condition, packaging, and exception flags. Missing values remain explicit and lead to `needs_information` when they are required for a safe decision.

**Effect:** The system fails closed on ambiguous capacity and rejects non-finite or unknown overrides before policy evaluation.

### 2. Hybrid Retrieval

**Why:** Dense retrieval handles paraphrases such as “portable charger” and “power bank,” while BM25 is stronger for exact strings such as `100Wh`, `160Wh`, `100mL`, and rule IDs. Their raw scores have different scales.

**Role:** API mode uses Qwen3 embeddings through the Furiosa endpoint; local mode substitutes character TF-IDF. Both paths run alongside Okapi BM25, and Reciprocal Rank Fusion combines rank positions without score calibration.

**Effect:** Dense, BM25, and Hybrid all reached Recall@3 of 1.00 on the 10-question presentation set. Their MRR values were 0.80, 0.95, and 0.933 respectively, so the small evaluation did not demonstrate a ranking gain from fusion; its architectural value is complementary retrieval behavior that needs a larger test set.

### 3. Deterministic Baggage Engine

**Why:** Battery and liquid policies contain arithmetic, inclusive boundaries, quantity caps, and approval bands that an LLM can restate incorrectly.

**Role:** The engine calculates `Wh = mAh × V / 1000`, selects the applicable airline rule, applies capacity and count boundaries, and produces carry-on, checked-baggage, conditions, exceptions, and missing-information fields. Retrieved chunks support the decision but cannot directly set a status.

**Effect:** Carry-on and checked-baggage outputs matched all 10 expected presentation cases. Boundary and missing-information behavior is covered by regression tests rather than model prompts.

### 4. Independent Country Policy Gates

**Why:** Airline carriage, departure security, transit screening, customs declaration, quarantine, and import prohibition are different legal or operational questions.

**Role:** Country evaluators apply origin, destination, and transit context after the airline decision. Journey status conservatively combines applicable gates, while the response preserves aviation and entry results separately.

**Effect:** A declaration requirement does not become an aviation prohibition, and an item accepted by an airline can still be rejected by destination import rules.

### 5. Compact Verified Context

**Why:** Passing the full regulation corpus increases token use and introduces irrelevant rules into the generation context.

**Role:** The application compacts the fixed decision, reasons, conditions, missing information, and a bounded set of retrieved rules before calling the Chat model.

**Effect:** The presentation comparison fell from 4,396 to 2,699 total tokens, saving 1,697 tokens or 38.6%.

### 6. Verified Answer Agent

**Why:** An explanation model can contradict a rule engine, cite a nonexistent source, emit malformed JSON, or follow instructions embedded in retrieved text.

**Role:** The prompt treats retrieved text as data, not instructions. The model must return a structured envelope containing the carry-on, checked-baggage, and journey statuses plus cited rule IDs. The application accepts the answer only when all statuses match and every cited ID belongs to the verified context; strict API mode exposes failure instead of presenting an unverified template as model output.

**Effect:** All 10 presentation guardrail cases passed. Regression tests also cover plain-text output, empty output, malformed structures, unknown citations, and status mismatch.

### 7. Shared Adapters and Observable Runtime Profiles

**Why:** Duplicated local and serverless decision paths cause response drift, and silent fallback makes API demonstrations impossible to audit.

**Role:** Local HTTP and the Vercel FastAPI adapter call the same request validator and `build_response_payload` function. The `api` profile requires both Furiosa credentials and does not silently switch to local retrieval or a local Chat model.

**Effect:** Integration tests enforce a shared response shape, while `/api/health` exposes the active retrieval and Chat modes.

## End-to-End Data Flow

```text
request
  -> schema and numeric validation
  -> structured item profile
  -> dense retrieval + BM25
  -> RRF-ranked evidence
  -> deterministic airline decision
  -> origin / destination / transit policy gates
  -> compact verified context
  -> optional Chat explanation
  -> status and source-ID validation
  -> separated decision, country_checks, and ai_answer response
```

## Safety Invariants

1. Only deterministic code can set transport or journey statuses.
2. Unknown items and missing critical measurements cannot become `allowed` by inference.
3. Air carriage and destination entry remain separate response fields.
4. Every applied or cited rule ID must resolve to a committed official source.
5. Duplicate JSON keys, duplicate rule IDs, invalid dates, and non-HTTPS sources fail during dataset loading.
6. Local HTTP and Vercel use one response assembly path.
7. Chat failures never alter or remove the deterministic result.

## Performance Interpretation

The current measurements prove prototype behavior only on 10 curated questions. Recall@3 saturation means the set is too small to distinguish retrievers, and Hybrid MRR being below BM25 means fusion should not be described as a measured ranking improvement. The clearest measured architecture benefit is the 38.6% token reduction, while decision and guardrail correctness require a larger versioned evaluation set before production claims are justified.

## Presentation Snapshot vs Current Implementation

| Concern | August 2026 presentation | Current public implementation |
| --- | --- | --- |
| Semantic retriever | `furiosa-ai/Qwen3-Embedding-8B` | Same API default; character TF-IDF in local mode |
| Explanation model | `furiosa-ai/Qwen3-32B-FP8` | Configurable; `.env.example` selects `furiosa-ai/gpt-oss-120b` |
| Orchestration | Model-selected `search_rules` call followed by Harness validation | Application-controlled retrieval, deterministic evaluation, and compact context before Chat |
| Validation scope | Tool use, statuses, numerical claims, and source IDs | Status and source-ID envelope; numerical authority remains in deterministic output |
| Failure behavior | Retry or safely substitute the rule-based response | Keep the rule result and expose Chat failure as `ai_answer.status=error` in strict API mode |
| Evidence | 10-question evaluation and one token-comparison request | Historical results are documented but not claimed as current-model benchmarks |

The presentation architecture and current implementation preserve the same trust boundary: retrieval and generation may assist, but deterministic code owns the decision. The mapping above documents later engineering changes without rewriting the historical experiment. Full metrics and the recorded UI execution are available in [Evaluation and Presentation Measurements](EVALUATION.md).
