# Chat-Johnson test log

Repo: colegleason1-jpg/chat-johnson @ claude/ai-nonlinear-logic-arch-jakbpm
Local read-only clone: /home/user/colegleason1-jpg/chat-johnson
READ ONLY — no writes to that repo. All artifacts under this scratchpad.

## Tests
- T1 GATE: do scrcae's 6 refusal reasons fire correctly on token-domain data?
- T2 CUSTODY: does provenance survive the Heavy Mode handoff?

## Entries

### T1 GATE — DONE. Verdict: partial generalization.

Ran scrcae's estimator on Chat-Johnson's exact token-domain transformation
(vendor_stress: market_price=calls/peak, disruption_rate=fails/calls, anchor=0.6).

- POWER: 91.7% — finds a real rate-limit effect. The machinery transfers.
- 4 of 6 reasons fire correctly (too-few-obs, no-variation, not-distinguishable, wrong-sign
  when the effect is genuinely inverted).
- DEFECT 1 — WRONG_SIGN is mis-ordered for this domain. Sign is checked on the point
  estimate BEFORE the interval is consulted, so a true null with a noise-negative slope
  reads as "wrong sign" (a claim about a real inverted effect) rather than "no effect".
  Fires on 39-46% of true nulls.
- DEFECT 2 — 12.0% false USABLE on a true null (nominal ~2.5%). Reports a usable
  elasticity where no relationship exists; that number then moves the token allocation.
- Diagnosis attempt 1 (WRONG): blamed the moving-block bootstrap's n**(1/3) block
  length (4h at n=60 vs 10h sessions). Forcing block=10 changed nothing: 12.0 -> 12.3%.
- Diagnosis attempt 2 (CONFIRMED): heteroskedasticity from the rate denominator.
  fails/calls from a 2-call bin is 0/0.5/1.0; from a 40-call bin it is 0.03+/-0.03. OLS
  weights them equally, and noise in y is largest exactly where x is smallest. The
  supply-chain domain has comparable deliveries per period, so equal weighting is fine
  there. Requiring >=5 calls/bin: 12.0 -> 5.0%. >=10 calls/bin: 4.0%. No vendors lost
  (300/300 still fittable) — the fix is free.
- CONCLUSION: the taxonomy has no concept of PER-OBSERVATION precision. It guards thin
  evidence in aggregate (MIN_OBSERVATIONS, MIN_PERIODS_ABOVE_ANCHOR) but not per point.
  This domain needs a 7th reason. Kill criterion was "if each new domain needs new
  reasons it is a checklist, not a product" — one domain needed 1 addition + 1 reorder.
  That is a pass, but a qualified one.

Scripts: t1_gate.py, t1b_null.py, t1c_persistence.py, t1d_block.py, t1e_hetero.py

### T2 CUSTODY — DONE (structural). My stripping claim was WRONG in mechanism.

Claim under test: "confidence language gets stripped at the first summarization step."

FINDING — nothing is stripped, because nothing was ever attached. Two channels:
  * METADATA: RouteDecision(provider, model, reason, solver, decision_vector, finish).
    Survives and ACCUMULATES — final_decision.reason concatenates the whole chain
    ("bounded heavy mode: draft -> review(X) -> synthesis; final=...").
  * CONTENT: json.dumps({"request", "context", "candidate", "review"}). Text only.
  The next agent sees ONLY the content channel. The critique agent cannot know which
  model wrote the draft, what it cost, or whether any number in it was measured.
  => Provenance is lost at the SERIALIZATION BOUNDARY, not at summarization. No
     summarizer is needed to lose it. This is a sharper claim than the one I made.

CORROBORATION, found independently by the author: CRITIQUE_CUT_NOTE (router.py:2187).
  When draft_decision.finish == "length", a sentence is appended to the CRITIQUE'S
  SYSTEM PROMPT saying the draft was truncated — because the critique was judging
  cut-off drafts as bad designs. That is one piece of upstream metadata, hand-bridged
  into the content channel as a string append, because no channel existed for it.
  This is the best evidence found for the custody thesis, and it is evidence of the
  PROBLEM, produced by someone not thinking about provenance.

ALSO: treasury provenance (fitted vs asserted) never enters the model context at all —
  grep for treasury/value_rows/stress_rows against message/prompt/content: zero hits.
  It is Streamlit-display-only. A model in this system can never reason about whether
  a number it was given was measured.

NOT TESTED (needs BYOK keys, which I did not ask for and would not use): whether a
  model, GIVEN provenance in the content channel, preserves it through synthesis.

### T3 ROUTING — step 1 of the measurement plan. Three findings.

Target: Cortex 2, the MILP routing controller. User's own hypothesis: "it looks at their
strong suits then uses key words in the user query to match to the best api", and
"I've had trouble getting multiple to work on problems."

T3a — THE MILP CANNOT CHANGE ANY DECISION IT IS ASKED TO MAKE.
  Structural proof: the constraint matrix is 6 rows x 3 endpoints, and exactly ONE row
  (row 0, sum(x)=1) touches more than one endpoint. Every other row is x_i <= c_i, an
  independent per-endpoint bound. A binary program of that shape has argmax over the
  feasible set as its optimum by inspection — there is no interaction to optimise over.
  Empirical: scipy.optimize.milp vs the Python fallback across 400 random states
  (varying task, size, usage, exclusions) — 400/400 identical, including the 15
  infeasible cases.
  Cost: 1.220 ms with the solver vs 0.192 ms without. 6.3x for zero decision value.
  NOTE — first run of this test was VACUOUS: scipy was not installed in the measurement
  container, so router.milp was already None and both arms ran the same fallback.
  Installed scipy 1.17.1 and re-ran; the solver path then genuinely executed (385/385).
  CONTRAST: treasury_plan's use of the same solver IS load-bearing — it has a shared
  token budget across activities, which is real coupling. The router has none.

T3b — THE CLASSIFIER COLLAPSES MOST TRAFFIC TO ONE ENDPOINT. This is the user's symptom.
  classify() is substring keyword matching. 24 realistic developer queries, labelled by
  intent: overall recall 46%. 54% fall through to "chat".
    test_fix 40% | code_patch 20% | reasoning 20% | quick_text 80% | context_load 75%
  Endpoints actually reached: groq 18, google_ai_studio 4, huggingface 2.
  So 75% of this traffic hits ONE endpoint — not because the router chose it, but because
  everything upstream classified as chat. Missed: "should I use a queue or a cron job"
  (reasoning), "add a retry to the upload handler" (code_patch), "tests are red after my
  last commit" (test_fix).
  CAVEAT: the 24 queries and their intent labels are MINE. The real validation is the
  vault's own route_log, which I do not have. Distribution of task_type in production is
  the number that settles it.

T3c — the user's model is half right. With healthy endpoints the choice is NOT a pure
  function of task_type (request size moves chat/code_patch/quick_text), and capacity
  pressure moves it off the keyword pick 42% of the time. Capacity IS load-bearing. The
  defect is upstream of routing, in classification.

Scripts: t3_milp.py, t3b_structure.py, t3c_keyword.py, t3d_classifier.py

### T4 CORTEX LEARNER — this one WORKS. The method discriminates.

Quality is Beta(2,2) per (endpoint, task_type), feeding utility as
QUALITY_WEIGHT * (mean - 0.5), i.e. at most +/-0.15 per endpoint.

T4a — CAN IT EVER CHANGE A DECISION? Yes, unlike the MILP.
  Two endpoints can swap only if their base utilities are within 0.30. Measured gaps:
    chat 0.191 YES | code_patch 0.160 YES | reasoning 0.149 YES | test_fix 0.038 YES
    context_load 0.357 NO | quick_text 0.332 NO
  4 of 6 task types are reachable. The learner is load-bearing where the MILP was not.
  The 2 unreachable ones are a real (small) finding: evidence accumulates in those cells
  forever and can never act, because the base table gap exceeds the weight's range.

T4b — DOES IT GET THE EVIDENCE? Mostly.
  2,000 sends, exploration 0.10 * 0.25 = 2.5% (pinkwave DEFAULT_GAIN = 0.25).
    as measured (54% chat):  17/18 cells touched, 8/18 with >=10 verdicts,
                             busiest cell groq/chat = 53% of all sends,
                             2/6 task types where the runner-up could overtake
    if classifier fixed:     17/18 touched, 6/18 with >=10, busiest 22%,
                             3/6 where the runner-up could overtake
  Verdicts a runner-up needs to overtake: test_fix 1, reasoning 4, code_patch 5, chat 8,
  context_load and quick_text unreachable at any evidence.
  CAVEAT: this assumes every send yields a verdict. Real verdicts come from the outcome
  log; sends with no recorded outcome contribute nothing, which slows all of the above
  proportionally. Not measurable without the production log.

### STEP 1 SCORECARD so far — 4 judgement points

  1. Elasticity gate (treasury)   DEFECT   13% false USABLE on a true null (nominal 2.5%)
  2. Cortex 2 MILP (routing)      DECORATION  0/400 decisions changed; 6.3x cost; proven
                                  structurally (1 coupling row in the constraint matrix)
  3. classify() (routing)         DEFECT   46% recall; 54% collapse to chat; 75% of
                                  traffic reaches one endpoint
  4. Cortex learner (routing)     SOUND    load-bearing on 4/6 task types, gets evidence
                                  in 17/18 cells

  The method found 2 real defects, 1 piece of decoration, and 1 sound component. That
  last one matters most for the thesis: a measurement method that only ever finds
  problems is not measuring, it is confirming. This one discriminates.

### T5 CORTEX 3 (Project Seth entropy probe) — load-bearing, but barely, and expensive.

penalty = 0.6*failure_rate + 0.3*min(1, latency/2) + 0.1*seth_term, entering utility as
-0.30*penalty. The first two terms are arithmetic on telemetry already recorded. The
third is the branded part: 1/f noise, Euler-Maruyama SDE, Shannon entropy gain over an
undriven baseline.

  utility reach   failure_rate 0.1800 | latency 0.0900 | seth 0.0300 (realised: 0.0114)
  whole penalty is load-bearing on 4/6 task types. That part works.

  COST: 3.3357 ms per decision with the seth term vs 0.0016 ms for the two telemetry
  terms alone. 2,052x.

  ANALYTICAL BOUND SAID 0/6 TASK TYPES. THE DIRECT TEST SAYS OTHERWISE — my bound was
  wrong. Running the real selector with and without the seth term across 1,500 telemetry
  states: 3 decisions changed (0.2%). All three on tight-gap task types (test_fix 0.038,
  reasoning 0.149) where telemetry had already brought two endpoints within ~0.01 utility
  of each other. The base gap is not the operative gap; the post-telemetry gap is.

  VERDICT: not decoration, unlike the MILP. It decides roughly 1 route in 500, purely as
  a tiebreak, for 3.3 ms of compute each time. Whether that trade is worth keeping is a
  judgement call, not a defect. What is overstated is the README's architecture diagram,
  which presents Cortex 3 as a co-equal third processor; the code's own docstring is
  accurate ("a bounded stochastic-shape component, never the majority of the penalty...
  a routing signal, not a physical claim").

  METHOD NOTE: this is the third time in this session that my reasoning was corrected by
  measurement — the bootstrap block length (wrong mechanism), "the fix is free" (wrong,
  density-dependent), and now this bound (too coarse). Each was caught by running the
  thing rather than bounding it. That is the argument for the measurement product, made
  against myself.

### STEP 1 SCORECARD — 5 judgement points

  1. Elasticity gate (treasury)   DEFECT      13% false USABLE on a true null (nom. 2.5%)
  2. Cortex 2 MILP (routing)      DECORATION  0/400 decisions; 6.3x cost; proven
                                              structurally (1 coupling row)
  3. classify() (routing)         DEFECT      46% recall; 54% collapse to chat
  4. Cortex learner (routing)     SOUND       load-bearing on 4/6; evidence in 17/18 cells
  5. Cortex 3 seth term           MARGINAL    0.2% of decisions, as a tiebreak, at 2,052x
                                              the cost of the arithmetic it sits beside

### T6 Verdict.limited_by — DEFECT, and it points users at the wrong remedy.

Chat-Johnson delegates "what bound this plan" to scrcae's AttainabilityReport.limited_by,
acting on it only when it starts with "resource:" (-> status "supply").

The engine decides it by fixed if/elif order: risk_cap -> resource -> budget -> structure.
Its own comment on the resource branch:
  "A resource row that is tight while some node is below its maximum is what stopped the
   portfolio, and 'more capital' is the wrong remedy for it: the supply is what has to
   grow. Checked before the budget for that reason."

The intent is right. The test is not. A resource counts as tight only when
  resource_use >= capacity - 1e-9
i.e. usage must REACH capacity. The treasury builds every intervention with
min_funding_scale = max_funding_scale = 1.0, so items are INDIVISIBLE and usage lands on
a multiple of item cost. Unless capacity is an exact multiple there is stranded headroom,
the resource never reads as tight, and limited_by falls through to "budget".

MEASURED — 5 indivisible items at 100,000 tokens each, budget effectively unlimited, so
vendor supply is the ONLY possible constraint:
    capacity 150,000 -> "budget"          (unlimited budget!)
    capacity 200,000 -> "resource:groq"   (exact multiple)
    capacity 250,000 -> "budget"
    capacity 300,000 -> "resource:groq"   (exact multiple)
    capacity 449,999 -> "budget"
  400 RANDOM capacities: supply binding 400/400 times, correctly named 0 times (0.0%).
  It fires only on exact multiples of item cost, which is measure-zero for real capacities.

CONSEQUENCE IN THE APP: verdict.status = "supply" essentially never fires, limited_by
stays empty, and Verdict.summary() reports "short by N tokens today" — telling the
operator to find more tokens when no amount of tokens would help, because a vendor's
rate limit is what stopped the plan. Same family as F19: the reason is computed, carried,
and wrong.

OWNERSHIP: this is scrcae's defect (optimization/diagnostics.py), not Chat-Johnson's.
The correct test for indivisible items is whether any unfunded item could still fit --
i.e. the resource is binding when use + min(unfunded usage) > capacity -- not whether
usage reached capacity exactly.

Scripts: t6_limitedby.py, t6b_indivisible.py

### STEP 1 SCORECARD — 6 judgement points, done

  1. Elasticity gate (treasury)   DEFECT      13% false USABLE on a true null (nom. 2.5%)
  2. Cortex 2 MILP (routing)      DECORATION  0/400 decisions; 6.3x cost
  3. classify() (routing)         DEFECT      46% recall; 54% collapse to chat
  4. Cortex learner (routing)     SOUND       load-bearing 4/6; evidence in 17/18 cells
  5. Cortex 3 seth term           MARGINAL    0.2% of decisions, at 2,052x the cost
  6. Verdict.limited_by           DEFECT      0/400 correct when supply binds; names
                                              "budget" under unlimited budget

  Three defects, one decoration, one marginal, one sound. Six for six produced a number
  nobody had. The bar set before starting was "two or three more with real numbers".
