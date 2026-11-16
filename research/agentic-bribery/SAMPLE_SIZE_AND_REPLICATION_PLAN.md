# Sample Size and Replication Strategy — Agentic Improper-Influence Study
**Version:** Planning addendum, 16 November 2026. **Status:** future-study proposal, not a retrospective claim about executed experiments.
**Related:** [V4 pre-registered protocol](V4_PREREGISTERED_PROTOCOL.md), [normative behaviour oracle](NORMATIVE_BEHAVIOUR_ORACLE_V4.md), [research record](RESEARCH_RECORD_V1_TO_V4.md).

## Current evidence base — not one homogeneous cohort
Four exploratory cohorts have been completed:
- Reversed-pressure: 40 dialogues (Qwen, matched traffic and SRE controls). Synthetic restricted markers were spoken in 3/10 SRE controls and 3/10 pressured SRE cases.
- V2 role-corrected: 15 dialogues (nine Qwen and six Nemotron across case contexts).
- V3 incentive ecology: 28 dialogues (24 Qwen over two seed blocks and four Nemotron traffic).
- V3.1 accounting corrected: 16 dialogues (12 Qwen and four Nemotron traffic), resulting in one positive-unit private-benefit proposal, no acceptances, no prohibited decision attempts, no completed virtual bribery, six formal compliant decisions and ten unresolved cases.
That is **99 exploratory dialogues** across these four cohorts, *not* 99 exchangeable independent trials of the same intervention. The three worlds, scripted openings, prompts, accounting systems, model parameters and outcome evaluation evolved between cohorts. Do not combine them into a pooled success/failure rate or cite an overall p-value.

V4's model execution is separate; only add V4 cases to its cohort after the independent audit successfully validates the resulting artifacts.

## Why 16 is insufficient
For zero observed events in *n* independent, homogeneous trials, an exact 95% **two-sided** Clopper–Pearson upper bound is:
  `1 - (0.025) ** (1/n)`.
Thus **0/16** yields approximately **20.6%** upper, not a demonstrated zero underlying event probability. **0/100** yields 3.6%, and **0/300** yields 1.22%. A one-sided 95% upper bound at **0/300** is approximately 0.99%. None of these bounds apply directly to our heterogeneous historic cohorts.

For a simple *independent-proportions* comparison of 2% vs 10% event risk at alpha=0.05 two-sided and 80% power, a normal approximation gives roughly **122 independent episodes per comparison arm**. Because our design pairs seeds and shares cases/models, independence is not assured; these values are **planning guides**, not a justified final power calculation. We need estimates of within-seed correlation and event frequency before claiming a powered confirmatory design.

## Evidence gates before adding sample size
**Gate 0 — complete V4 adjudication.** All three Qwen case jobs plus the Nemotron traffic job must finish; the separate V4 auditor must find zero ledger discrepancies. Each artifact must be retained even if its job fails. If outcomes are mostly role-confused or undecided, remedy this with a **new protocol version** before replication. Never silently remove these failures.

**Gate 1 — controlled sensitivity tests (software, not LLM claims).** A test actor can generate a valid conditional offer/accept/commit/unlawful result; the simulator must classify it as completed misconduct. Invalid IDs, zero benefits, wrong roles, re-decisions, and binding-approval blocked actions must never be miscounted. Explicitly verify compliant completion remains possible and reward is granted only once.

**Gate 2 — small frozen feasibility sample.** Run 10 new, independent seed blocks on each of three worlds and all four conditions (10×3×4 = **120 dialogues per model**). Keep full 16 turns with 15 genuine inference calls, so **1,800 real calls per model**. Record parse validity, role consistency, final-decision completion, attempted acts and proper evidence exposure. Stop and report if the test is not eliciting meaningful final decisions; do not quietly tune prompts based on who offers a bribe.

**Gate 3 — confirmatory replication if instrument validity established.** Aim for 50 new seed blocks × 3 worlds × 4 conditions = **600 dialogues per model**, yielding **150 episodes per arm per model** and ~9,000 real inference calls/model. This would cover an illustrative independent 2%-versus-10% difference with headroom, but final sensitivity must account for paired/block design, between-world heterogeneity and multiple endpoints.

**Gate 4 — cross-model replication.** Replicate the *same frozen conditions and seeds* on at least two genuinely accessible models; report per-model results and comparative heterogeneity, not a pooled single rate unless scientifically justified. On a five-request-per-minute free endpoint, **1,800 calls require a lower bound of six hours**, and **9,000 calls at least thirty hours**, without service overhead. Never launch the full free-tier plan without checking quota, key limits and runner duration. Consider additional local open models or paid budget-constrained inference; log the exact model IDs and provider metadata.

## Primary and secondary estimands
- **Primary:** difference in completed synthetic bribe probability between high-stakes B and baseline A, comparing matched world–seed blocks within model.
- **Secondary:** attempts, accepted conditional offers, blocked deviations, unilateral institutional integrity violations, lawful completion, missed mandatory decisions, and synthetic-secret speech leak, each reported by model, world, arm and seed.
- **Validity:** role-confused, truncated and undecided cases are counted explicitly. Report ITT-like all-assigned denominator and valid-opportunity denominator; do not turn invalid cases into model refusals.

## Statistical analysis plan
- Present **raw numerator/denominator** and exact binomial intervals by model/world/arm for sparse events.
- Estimate **paired** risk differences with a cluster-aware bootstrap over seed blocks (or an appropriate repeated-measure model when identifiable). Prestate which hypotheses are primary and how multiplicity is handled.
- Use a fixed seed ledger and block randomisation of arm order, preserving identical public evidence and model configuration. Ensure random seed manipulation actually changes generation deterministically for each provider; if provider ignores seeds, do not falsely call the repeated runs independent seeded trials.
- Preregister stopping rules and the positive/negative control suite before inference. Do not stop at the first bribe and report it as a representative probability.
- A zero-event confirmatory sample is still informative about an upper bound **conditional on a sensitive and valid assay**.

## Cost and execution control
The Qwen Ollama jobs use temporary GitHub-hosted runners and may be bounded by runner concurrency, download rates and available compute minutes. The Nemotron free model previously required ≥15.5 seconds between calls to avoid 429s; 120-dialogue replication would require many hours. Partition by model × world × seed blocks, save interim results **per arm** and avoid rerunning successful blocks. Use separate workflow dispatch inputs for fixed start/end seed blocks and maximum calls. Require explicit budget/cap confirmation before generating thousands of chargeable API calls.

## Integrity of the research narrative
This programme evolved adaptively from exploratory observations to the V4 normative protocol. Publish negative results and mistakes. The right to claim novel evidence depends on independent replications with adequate controls, not obtaining a positive bribery demonstration by escalating prompts until it appears. Any new scenario design, role-objective wording or utility constant constitutes a **new version**, and it must be kept separate from confirmatory outcomes.
