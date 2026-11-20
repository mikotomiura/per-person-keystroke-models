# Summary of the pre-computation conditions documents

This file is an English guide to the conditions documents that the authors committed before each computation in these experiments. The Japanese originals are authoritative; this summary is only a reader's aid and adds nothing to them. Numbers and thresholds are copied from the originals; where a term is unclear, the original term is kept in parentheses. Commit times (UTC) are taken from `gse-commits.tsv`, a table built from the authors' private commit history (column `first_commit_utc`). Sections follow the order of the directory names (upstream experiments included): first the three experiments on public keystroke data that precede the per-writer learning experiments, then the per-writer learning experiments on CoAuthor and CS1, then the synthetic-data sensitivity experiments and the checks that reuse stored results. Several documents have dated addenda; the addenda that were written after earlier results had been seen say so themselves, and this summary notes them.

Common vocabulary. "Stall" (停滞) is a long net-output stop for the writer, not a judgement that the writer is stuck. `theta` is a writer's own 0.99-quantile of inter-key intervals, undefined below 100 intervals. An "onset" is a stall start produced by the replay tool (`gse-replay --features`). `p_stuck` and `ewma_x` are the two output signals of the keystroke estimator; `d_p_stuck` and `d_ewma_x` are their 30 s changes. AUC is the probability that a target-side value exceeds a control-side value (ties 0.5). From the 2026-11-03 experiments on, the estimator's output is quantized into a 26-symbol series (a 5 x 5 grid of bands of `ewma_x` and `ewma_y`, plus one symbol for backspace bursts) and a sequence model predicts the next symbol. "Own fit" (本人) is a model fitted on one writer's training units; "pooled fit" (共通) is fitted on the other writers' units; "r1" is the writer's own first-order Markov chain over symbols. `tau` (τ) is the strength of a prior that pulls the own fit toward the pooled fit (τ = ∞ is the pooled fit itself); the "mode" (最頻値) is the normalized expected counts of the pooled fit, the limit as τ grows. Results are per-writer differences in log-likelihood per symbol (nats/symbol), summarised by median, quartiles and the share of writers on the good side. "Panel" names such as P15, P30, C5 are sets of writers with enough sessions or tasks; `k` is the number of training units. "Selection by others" (他人で選ぶ) means a setting is chosen by the other writers' medians, never the target writer's own values. Raw data and per-writer values stay outside the repository; only aggregates are committed. "Gates" are checks that stop the run: some check the real-data pipeline or reproduce stored values, others are positive controls on synthetic data; "mutations" are deliberately broken code variants that must turn a named control red before the real run.

---

## experiments/20261031-coauthor-pre-request-signal/conditions.md

First commit: 2026-10-31T13:41:17Z.

Purpose. Whether the estimator's output sits closer to the "stuck" side just before a writer asks for a machine-generated suggestion (`suggestion-get`) than at times when no request was made, on CoAuthor (English co-writing, crowd workers). A preliminary basis for a later threshold; it sets no value.

Input. CoAuthor v1.0 (1,447 jsonl files; writer map from two sheets of 829 and 614 rows). Text is discarded in conversion; only single-character inserts, deletes and cursor moves become keystrokes; suggestion-origin insertions are removed. Key releases are synthesized as min(press + 100 ms, next press - 1 ms), with 60 ms and 140 ms as sensitivities.

Rules fixed beforehand.
- Signals: `p_stuck` and `ewma_x` (co-primary, value at the last snapshot at or before T); secondary: a stall onset in (T - 30 s, T], correction rate, count of pauses of 2 s or more.
- Requests count only if at least 60 s after session start, with no suggestion-related event in the previous 60 s and at least one user key in the previous 30 s. P is the pause before the request.
- Controls: matched (primary) = times inside key intervals of length at least P, up to 5 per request; unmatched (reference) = 5 times the number of requests, uniform.
- Decision unit: writers with at least 5 requests; per-writer AUC; bootstrap of the median over writers (2,000 resamples) with 95% and 97.5% intervals. For the matched control and the two primary signals, a 97.5% lower bound above 0.5 = "a signal appears"; interval containing 0.5 = "not visible"; upper bound below 0.5 = "reverse". A median above 0.6 is reported alongside.

Output. Counts first, then AUCs and intervals, then the release-time sensitivity.

Status. Preliminary description. Stated limits: the instructions tie the suggestion key to "being stuck", so requests are close to a self-report; releases are synthetic; no calibration per person; nothing is claimed for Japanese, IME input or the project's own participants.

---

## experiments/20261031-coauthor-pre-request-signal/conditions_round2.md

First commit: 2026-10-31T15:42:50Z.

Purpose. A second analysis of the same data; the first document is not rewritten. Three changes: a within-writer signal, a stall onset based on the writer's own distribution, and a stratum of requests after long pauses with a control matched on the delimiter type.

Rules fixed beforehand.
- Signals: `d_p_stuck(T)` and `d_ewma_x(T)` (co-primary). Secondary: onset within (T - 30 s, T], computed after chaining each writer's sessions in time order with 2,500 ms between them (longer than the 2,000 ms observation gap, shorter than the writer's `theta`); 16 overlapping session pairs are chained anyway, which differs from reality. If both requests and controls have zero onsets the secondary is "undecidable".
- Strata: L (primary) = requests with P of at least 2,000 ms; A = all requests. Delimiter type: the preceding key is a space, enter or sentence punctuation ("delimiter") or not ("mid-word").
- Controls: key intervals longer than P whose start key has the same delimiter type, up to 5 per request, same random seed as before; no unmatched control.
- Decision: per-writer AUC (higher = rising); a writer needs at least 3 requests with controls in stratum L (5 in A); bootstrap of 2,000 with 95% and 97.5% intervals; reading rules as in the first document; under 10 writers in L means "too few writers to judge".

Output. Counts before AUCs; then a check of the instrument (distribution of `p_stuck`, onsets per writer, `theta`).

Status. Second preliminary description. Stratum L is chosen by the length of the pause before the request; whether the writer was stuck is not recorded.

---

## experiments/20261101-klicke-early-stall-trigger/conditions.md

First commit: 2026-11-01T08:10:19Z.

Purpose. An exploration on KLiCKe (argumentative writing, 30 min, one session per writer, no suggestion feature). (1) Primary: if a prompt were fired early in a pause (when it reaches 0.5 or 0.75 times the writer's `theta`), how often per hour would it fire, and what share of firings lead to a stall onset; compared with the current trigger (`p_stuck` >= 0.60 for 30 s). (2) Secondary: replicate the pre-stall test (rise of the estimator's output before a stall vs before a short pause that did not become one).

Input. `WritingTask.zip`, stopped unless its SHA-256 matches; only the keystroke CSVs are read one by one (no text, scores, task prompts or demographics). Mouse-click rows are not keys. Sessions with fewer than 200 presses are dropped. Key mapping is fixed before counting values (alphabetic, numeric, space, enter, tab, punctuation classes, backspace/delete, modifiers, navigation, escape, function, other).

Rules fixed beforehand.
- Clock A (from the last character) fires at u + k * theta(u) for k = 0.5, 0.75; clock B (stall clock) fires at s + k * theta(s) if the net-output condition lasts that long. The current trigger is reproduced without its later caps; it is not fired after 180 s without a key.
- Python re-computations of `theta` and of confirmed onsets must match replay for every case or the run stops. Writers with under 10 min of eligible time are excluded from the primary tally.
- Reported: firings per hour (median, quartiles, 95% interval from 2,000 writer resamples); share of firings leading to a stall; share of stalls preceded by a firing; time from firing to onset; descriptive curves for k from 0.25 to 3.0 in steps of 0.25 and for fixed 2, 5, 10, 15, 20 s.
- Secondary: pooled-pairs AUC replaces the median of per-writer AUCs if fewer than 30 writers qualify; thresholds at the 80th, 90th and 95th control percentiles are shown with measured exceedance rates.

Status. Exploration, no thresholds, not a gate. Stated limits: a stall onset is a long net-output stop, not a judgement of being stuck; English, US adults, crowd workers, browser writing; one session per writer, so `theta` grows within the session.

---

## experiments/20261102-public-data-landscape/conditions.md

First commit: 2026-11-01T15:19:20Z.

Purpose. A descriptive overview (no tests, no thresholds) of KLiCKe and CoAuthor with six items: L1 basic pause and stall rates, L2 level of the estimator's output, L3 events other than characters around stalls, L4 receipt events and resumption, L5 within-writer variation (CoAuthor only), L6 phase within a session.

Input and holdout. KLiCKe (zip hash-checked, plus its stored intermediate; mouse clicks and pastes are read from the CSVs by time only) and CoAuthor (zip hash-checked, writer link by `worker_id` and `session_id` only). 30% of writers per dataset are set aside before any tally (random seed 20261102, and +1 for CoAuthor); only the count and a hash of the list are published, and the run stops if a held-out writer appears in the input. CoAuthor intermediates are built per session, so `theta` is per session.

Rules fixed beforehand.
- Definitions follow the previous experiment; writers with under 10 min of observation are excluded. "Near a machine suggestion" in CoAuthor = within 60 s of a suggestion event or an inserted machine-text event; the main figures use the ordinary stretches, except L4-L6, which use all time. A correction made before any value was seen: key-interval counts include intervals across observation gaps.
- L1: shares of key intervals of 2, 5, 10, 30, 60 and 180 s or more; last `theta`; stall onsets per hour; stall length; stalls with no resumption.
- L3: events in the window before [s - 30 s, t0] and after (t0, resumption).
- L4: receipt events (pastes in KLiCKe; accepted suggestions and multi-character inserts in CoAuthor), share of stalls with one before resumption or within 5 min, and breaks of 180 s or more.
- L5: writers with at least 5 sessions of 5 min or more; between- and within-writer spread and an intraclass share. L6: thirds of each session.

Status. Description. Stated limits: English crowd-worker data; KLiCKe pastes include cut-and-paste inside a document; the estimator is not calibrated on these groups, so level comparisons do not show how many "states" there are.

---

## experiments/20261103-coauthor-per-person/conditions.md

First commit: 2026-11-03T12:56:05Z.

Purpose. A learning curve for per-writer learning on CoAuthor: how a writer's own fitted sequence model compares with a pooled one as the number of training sessions k grows, and how a per-writer logistic model for a proxy label compares with baselines.

Not to be read as. The proxy label (a suggestion request in the next 60 s) is an event of working with a tool, not a cognitive state; learned states are not named; no thresholds, no tests; sessions of about 11 min are not days. An own fit beating the frozen estimator is nearly trivial, so the information is in the comparison with the pooled fit and with the symbol Markov chain.

Rules fixed beforehand.
- Units and panels: writer = person, session = unit (sessions with one observation interval, in time order); the last 5 sessions are the evaluation, training is the k sessions before them. P15 = writers with at least 20 sessions, k in {1, 2, 3, 5, 8, 12, 15}; P30 = at least 35 sessions, k up to 30; a secondary all-writer panel; a grid for the number of labelled sessions m. Seed 20261103.
- Model: 3-state HMM over 26 symbols, MAP-EM (pseudo-counts: emission 0.5, transition 1, initial 1), 5 starting points (the frozen one and 4 random), convergence at 1e-7 per symbol or 500 iterations.
- Opponents: pooled EM, two frozen-engine baselines (F-a, F-b), symbol frequencies (r0) and symbol Markov chain (r1), all +0.5.
- Proxy-label model: L2 logistic (lambda = 1) on three inputs (5 table features, the EM filter, recalibrated `p_stuck`); base-rate baselines; Brier, log loss, AUC, calibration intercept and slope; 2,000 writer resamples.
- Gates and mutations: configuration gates, a check that the display layer reproduces the stored `p_*` columns, synthetic recovery of an HMM, no-leakage checks, a split check. A second version, written after the synthetic control results had been seen but before any real values, reports coverage as a result with only a coarse gate (0.80) and replaces the single-draw negative control with the mean over 20 synthetic draws. The pooled calibration intervals may be narrower than the nominal 95% at this number of writers.

Status. Descriptive; no claim that a state was learned.

---

## experiments/20261104-coauthor-ml-improve/conditions.md

First commit: 2026-11-04T04:25:07Z.

Purpose. Continue the previous experiment on CoAuthor and CS1 2021 by improving the per-writer learning: richer structures, a prior that shrinks toward the pooled fit, and a logistic model shrunk toward pooled coefficients.

Not to be read as. Proxy labels (next-60-s suggestion request; next-60-s accepted lookup in CS1) are tool-use events, not states. Catching up with r1 means predicting a quantized series, not a cognitive structure. Nothing is carried to Japanese, IME or the project's participants.

Rules fixed beforehand.
- Units: CoAuthor sessions (evaluation = last 5) and CS1 2021 tasks (evaluation = last 1; panel C5 = writers with at least 6 tasks, k in {1, 2, 3, 5}). For the EM fits, τ chosen by others is primary and τ chosen on the writer's own time-ordered folds is secondary; for the logistic model it is the reverse: λ is chosen on the writer's own folds (falling back to the λ chosen by others when no fold applies), and the λ chosen by others is secondary.
- EM structures: plain HMM with K in {3, 6, 10} and AR(1)-HMM with K in {1, 2, 3}; MAP-EM whose pseudo-counts are a base plus tau times the pooled expected counts, tau in {0, 100, 1,000, 10,000}; fitting in chunks of 900 symbols; 10 starting points for the pooled fit.
- Logistic: five features; the writer's coefficients are pulled toward pooled coefficients with strength lambda in {0.1, 1, 10, 100, ∞}; baselines are the writer's and the pool's base rates.
- Main metric: within-writer concordance C over (positive, negative) pairs. Cells with fewer than 6 writers hide quartiles and shares (a 5-writer median hits the minimum with probability about 5.8%, 6 writers about 0.9%).
- Compute plan: about 9 hours; the order of cuts was fixed but not used.
- Gates: pipeline checks against earlier intermediates; eighteen synthetic controls (prior limit, leakage, AR vs r1, Simpson-type data); ten mutations that must turn named controls red. Three control definitions (P-AR, P-LAM, P-LINF) were changed after the synthetic controls had been run once, before any real data were seen.

Status. Descriptive. Values are compared with the earlier experiment only roughly, because the pooled set, standardisation and the head of r1 are defined differently.

---

## experiments/20261104-cs1-landscape/conditions.md

First commit: 2026-11-03T23:46:28Z.

Purpose. A descriptive overview (no tests, no decision thresholds) applying the earlier overview's items L1-L6 to the CS1 keystroke dataset (introductory programming course, English, Python). Not data from the authors' own participants.

Input. CS1 2019 (Dataverse v5.2) and 2021 (v7.0) `keystrokes.csv`, each stopped unless its SHA-256 matches (2019: `b54d8cf5...7955`; 2021: `950a587b...22b6`). Inserted text is used by length only; deleted text, run output, source locations and clipboard contents are not read. Single-character keys are read in memory only to assign a category.

Rules fixed before per-writer and per-task counts, time intervals and lengths were seen. The column names, the counts per event type and the format of the key-name values had already been seen, as the document records.
- Unit: writer = `SubjectID`; task = (subject, assignment). A task is cut into work blocks wherever adjacent events are 1,800,000 ms (30 min) or more apart. Blocks are replayed separately and merged per task, so `theta` grows within a task. Blocks with fewer than 2 presses are dropped.
- Conversion tables for 2019 (browser IDE, no completion, no navigation keys) and 2021 (PyCharm, completion, auto-closing brackets) were fixed before counts; multi-character insertions and edits without a key name go to an event table (`multi-insert`, `auto-edit`); pastes, runs and switches are events. In 2021 `X-Attention` lock-out and ON/OFF rows are read as a prompt and an answer (an inference).
- Holdout: 30% of writers per version (random seed 20261104, +1 for 2021); count and hash only; the run stops if any held-out writer appears.
- Definitions: the 2021 "near a prompt" split is used for headline numbers; writers under 10 min are excluded; per-writer values by median and quartiles.
- Items: L1 and L2 as before; L3 events near stalls; L4 receipt events (`paste`, and `multi-insert` in 2021); L5 task-level variation (at least 5 tasks with defined `theta` and 5 min); L6 task thirds; descriptive unit counts.

Output. Aggregates only.

Status. Description. Stated limits: one US university, English coursework; blocks are an estimate; the estimator is not calibrated on this group; 2021 `paste` cannot separate outside pastes from cut-and-paste in the same file.

---

## experiments/20261104-timeseries-tau-extend/conditions.md

First commit: 2026-11-04T13:57:04Z.

Purpose. Extend the grid of the prior strength `tau` and test a two-step form. (a) Does adding τ up to 10^6 and τ = ∞ resolve the sticking of selected τ at the top of the old grid? (b) Is the own fit's failure to reach the pooled fit due to the grid end or to a small writer-specific structure? (c) Choosing the pooled structure by others and then adding a small own step: how does the own gain change with k, for a weak (hmm3) and strong (ar1-ar3) structure? No labels are used; only one-step-ahead log-likelihood.

Changes from the previous experiment (everything else is as there).
- Structures: hmm3 and AR(1)-HMM K in {1, 2, 3}.
- tau grid: {0, 100, 1,000, 10,000, 30,000, 100,000, 300,000, 1,000,000, ∞}; τ = ∞ means no fitting, the pooled parameters excluding the writer.
- Two-step rows: (structure, tau) pairs (4 x 9 = 36) chosen jointly by the other writers' median of own minus r1; a variant picks the structure by others and tau by the writer's own folds (k of 3 or more).
- Extra opponent: pooled minus r1 per structure; training and evaluation symbol counts are reported.
- No logistic part. Random streams are kept so that overlapping cells must reproduce the earlier values.

Gates. A reproduction gate requires overlapping cells to equal the previous summary to relative 1e-9 (an off-cell means the code changed wrongly). New controls: τ = ∞ equals the pooled evaluation exactly; parameter distance shrinks with τ; the joint choice ignores the target writer; subset reproduction. Mutations m11-m15. An amendment before real data changed the limit test of the τ control (the pooled fit includes the base pseudo-counts, so the mode differs from it by a floor).

Compute. About 1 h 40 min estimated; the grid is not changed mid-run.

Status. The result is descriptive and is not used to decide whether a time-series model is adopted.

---

## experiments/20261106-tau-mode-candidate/conditions.md

First commit: 2026-11-06T09:01:38Z.

Purpose. Split the small own-minus-pooled differences at large tau into a part due to the writer's own records (a = own(τ) minus mode) and a part due to the difference between the mode and the pooled parameters (b = mode minus pooled), per writer, so a + b = own minus pooled. In particular: does the CoAuthor AR result (10^6 slightly above ∞) and the negative CS1 differences fall under form 1, 2 or 3 below?

Rules fixed beforehand.
- Mode = normalize(expected counts of the pooled fit excluding the writer); rows with sum 0 get a uniform 1/26; nothing is fitted. It is added only to fixed-τ rows and as a new opponent (`mode_same`); the choice rows are unchanged.
- If the mode gives a zero probability to an observed symbol, the writer's value is -∞ (and +∞ for own minus mode), kept in medians and quartiles; interval method is flagged when infinities appear; NaN stops the run.
- Reading forms (no thresholds): form 1 (mode side): |a| < |b| at 10^6 and b has the sign of own minus pooled; form 2 (own side): |a| > |b|, a > 0 and good-side share above 0.5; form 3: mixed; form 4: whether a falls toward 0 from 10^5 to 10^6; form 5: cells with ±∞ medians are not read by forms 1-2. Medians of a and b are never added.
- An amendment before real data adds a secondary tally over writers whose mode is finite, after a synthetic positive control went red (the mode was -∞ for most synthetic writers).

Gates. Reproduction of the earlier summary (every leaf, relative 1e-9); controls for mode construction, limits, a + b = c, ±∞ handling, interval with infinities, mode not entering selection, identical earlier fits, exact saving; mutations m16-m27.

Status. A descriptive decomposition; it is not used to decide whether a time-series model is adopted.

---

## experiments/20261107-structure-deficit-test/conditions.md

First commit: 2026-11-06T15:50:07Z.

Purpose. Test a hypothesis from the earlier experiment: that an own fit beat the pooled fit because a 3-state HMM cannot carry strong dependence on the previous symbol, and the own fit partly compensated. Part 1 (deficit is the cause): remove the dependence by shuffling symbol order within each series; does the own gain disappear, given that the number of parameters does not change? Part 2 (not person-specific): does another writer's own fit also beat the pooled fit on this writer?

Rules fixed beforehand.
- Quantization q in {3, 5, 7} (symbols q^2 + 1 = 10, 26, 50), same formula as the engine; 6 conditions (q x original or shuffled). Shuffling is uniform within each series, with a separate random stream, applied to training, evaluation, pooled and r1 alike.
- Structures: hmm3, hmm6, hmm10, ar1-ar3; tau grid as before; panels P15 (k in {1, 5, 15}), P30 (k = 30), C5 (k in {1, 5}); main cells are three CoAuthor cells, CS1 read separately.
- Quantities per writer: G = own (τ chosen by others) minus pooled; G0 = own at τ = 0 minus pooled; D = r1 minus pooled (the deficit); S0 = median over other writers of their τ = 0 own fit evaluated on this writer minus pooled (using τ = 0 only, so this writer's records cannot leak through the pooled fit). A later amendment uses the random-start solution for S0 and G0.
- Reading forms (cut points 1/2 and 1/10 only choose wording): part 1 "disappears" if for all three q the deficit D drops, G_o > 0 and G_p < G_o/2; "does not follow" if any q has D drop but G_p >= G_o; part 2 "wins for others too" if S0 > 0 and S0 > G0/10 for all three q. Forms A, A', B, C combine them; they are named only if all three main cells agree. Rank correlation across structures is descriptive only.

Gates. Reproduce earlier summaries for the unshuffled 26-symbol condition; a quantization gate; shuffle, width, D, other-writer and leakage controls; two synthetic form controls (strong dependence, strong person differences); mutations m31-m39.

Compute. About 10.7 hours (upper about 16 hours).

Status. Hypothesis test of a reading, stated to hold only for these two datasets, three quantizations and six structures.

---

## experiments/20261107-unsmoothed-residual-check/conditions.md

First commit: 2026-11-06T17:31:05Z.

Purpose. (a) Do the direction and size of two earlier results (the weak structure's own fit beats the pooled fit; the weak structure's own fit loses to r1 while the two-step choice beats r1) survive when the exponential smoothing of the symbolizer and the overlap of 30 s windows are removed? (b) How much dependence do the fitted models (pooled, own, two-step, r1) leave in one-step-ahead pseudo-residuals?

Series. o = the current symbols; u = symbols from the pre-smoothing values (same 5 x 5 grid formula; backspace burst symbol kept); n = u thinned to rows exactly 30 s x j after the series start (non-overlapping windows). n is not "all dependence removed"; its size is not compared with o or u.

Rules fixed beforehand.
- Panels: CoAuthor P15 with k in {1, 5, 15}, CS1 C5 with k in {1, 5}; main cells P15 k = 5 and 15, C5 k = 5. Structures, tau grid and random streams as in the earlier experiment.
- Pseudo-residuals: the predictive distribution is folded onto the x band and y band margins, randomized (shared uniform draws across models), mapped to normal scores (zx, zy); symbol-25 steps are missing; autocorrelation at lags 1-10 per writer (lag 1 is the one read); a secondary lag-1 value over pressed-window steps.
- Reading words (cut at 1/2 only fixes wording): for u, "remains" if same direction and |u| >= |o|/2, "shrinks" if smaller, "reversed" if opposite; for n only "same direction" or "reversed". A word is used only if the three main cells agree. For residuals: "AR carries it" if |r1(AR pooled)| < |r1(hmm3 pooled)| for both zx and zy; "AR still leaves it" if also |r1(AR pooled)| >= |r1(r1)|. A zero residual is not "the model is right".
- Amendments before real data fix tie wording and missing-cell wording.

Gates. Reproduce the earlier summary for o; a bit-exact check that the symbolizer reproduces the stored rows; controls for raw-value recovery, thinning, residual calibration and misspecification, shared draws, saved-parameter round trip; mutations m41-m51; pinned code hashes.

Status. Descriptive robustness check. The series are run in the order n, o, u; if the reproduction check on o fails, u is not run.

---

## experiments/20261110-per-person-sensitivity/conditions.md

First commit: 2026-11-10T01:46:00Z (addenda dated 2026-11-10 and 2026-11-11; the last was written after the first 27 replicates had been seen, as the document states).

Purpose. On synthetic data only, how sensitive is the selection procedure (structure and τ chosen by others, τ = ∞ allowed)? (a) Dose: does a planted per-writer difference of known size produce a positive own-minus-pooled result, and what is the smallest size picked up? (b) Null: how large is the positive remainder when nothing is planted? (c) Structure: a true structure outside the candidates (K = 5). (d) Distribution: only a quarter of writers differ.

Not to be read as an estimate of real writers' differences; one data-generating design (AR(1)-HMM with the transition rows mixed with a per-writer draw), not claimed to represent real data.

Rules fixed beforehand.
- Generation: shared parameters m0 per true K (diagonal 0.97; C rows mixed toward a sticky unit row); per-writer C = (1 - λ) C0 + λ D_w with D_w ~ Dirichlet(2 C0). The planted size is the gain g* in nats/symbol, g* in {0, 1e-3, 3e-3, 1e-2, 3e-2}; λ is calibrated by bisection on 40 writers x 20,000 symbols to within +-10%.
- Shapes: CoAuthor-like (17 writers x 20 sessions of 600-700 symbols, 26 shared-only writers, evaluation last 5) and CS1-like (23 writers x 6 tasks, 8 shared-only, evaluation last 1).
- Replicates: 20 CoAuthor and 7 CS1; later 6 more CS1 replicates (seed 1 at the four nonzero levels, seeds 3 and 4 at the null), giving 2 seeds per level and 5 null seeds (addendum of 2026-11-11, with the reading fixed before the new results).
- Reading: U = largest median among null seeds; a level is "picked up" if every seed has median above U and good-side share at least 0.8; the sensitivity floor is the smallest picked-up level above which all levels are picked up; "rises" if the seed-mean median does not decrease with the level. Cases for carrying the result into the write-up are prewritten.
- Time rule: cut order fixed if the estimate exceeds 24 hours.

Gates. Hash checks of the code, zero-plant equality, mean of D_w, calibration, group labels, split, small recovery, shared random draws; mutations v1-v6.

Status. Sensitivity description; limits as above.

---

## experiments/20261111-mode-in-selection/conditions.md

First commit: 2026-11-11T01:40:10Z.

Purpose. The own-minus-pooled remainder contains the difference between the mode and the pooled parameters. Put the mode itself (a smoothed pooled fit using none of the writer's data) both as a comparison column and among the candidates chosen by others, and see how the main table changes. No fitting is rerun: the per-writer values stored by the mode experiment are read after being checked to reproduce that experiment's summary.

Rules fixed beforehand.
- Candidate order: ∞, mode, 10^6, 3 x 10^5, ... , 0, with ties going to the earlier one. Two-step rows add the mode as a τ value (value = mode minus r1); τ-by-others rows use mode minus pooled. Selection uses the other writers' medians, never the writer's own. Rows that use the writer's own folds (τ by own folds, the two-step row with structure by others and τ by own folds, and K by own folds) are unchanged.
- Opponent columns: r1, pooled, mode. A writer who chose the mode has own minus mode exactly 0; one who chose ∞ has own minus pooled exactly 0. Rows without the mode are shown alongside as "before".
- Per cell: counts of chosen (structure, τ) regions (∞, mode, top finite end 10^6, inside the grid, bottom end 0).
- Reading forms (no thresholds), main cell CoAuthor P15, k = 1 to 15: form M (the mode is chosen for more than half the writers in more than half the k), form S (finite τ chosen for most writers and own-minus-mode median positive with good-side share above 0.5 in more than half the k), form N (finite τ but own does not beat the mode), otherwise values are listed. ∞ chosen by most writers is counted as exactly 0 and left out of the forms.

Gates. Reproduction of the earlier summary; old-order equality; candidate and order controls; zero-column exactness; ±∞ handling; mutations n1-n4.

Status. Descriptive. The mode-based reading is limited to these data and not carried to design decisions.

---

## experiments/20261111-objective-and-pause/conditions.md

First commit: 2026-11-11T13:28:59Z.

Purpose. (1) The selection objective (median over other writers of own minus chain) does not choose by predictive quality and rarely selects the mode; does the earlier finding (a chosen own fit does not beat the mode on the 15-session panel) depend on this objective? (2) What share of the evaluated symbols are seconds with no key press in the preceding 30 s window (pauses)?

Rules fixed beforehand.
- Replace the median objective by the mean over other writers (equal weights; the order then equals the order of the others' mean per-symbol log-likelihood). A single -∞ among the others makes a candidate -∞, and it is chosen only if all are. The main row uses the candidates of the previous experiment (with the mode); a secondary row removes the mode from the candidates. The median-objective values are shown in a column.
- Same panels, opponents and cells as the previous experiment; additionally mode minus pooled per structure.
- Pause share: per writer, the share of evaluation symbols whose pressed-window flag is 0; per panel, the pooled share and the per-writer median, quartiles, minimum, maximum and count. Reproduction gates check the stored values, the previous summary, the evaluation symbol counts and the code hashes.
- Reading forms (same as the previous experiment): N, M, S, or no form. Mode-minus-pooled and the pause share are values only.

Gates. A synthetic case where mean and median disagree; target-writer independence; -∞ handling; equality with the median selection when switched back; mutations o1-o3. Output files are written with LF line endings.

Status. A sensitivity to the selection objective; the mean objective is not "the correct objective".

---

## experiments/20261111-sensitivity-mode-decomposition/conditions.md

First commit: 2026-11-11T01:40:10Z.

Purpose. Apply the a/b/c decomposition (own minus mode, mode minus pooled, own minus pooled) to the synthetic sensitivity data. With nothing planted, does the decomposition return form 1? With planted differences of known size, does it return form 2 (own side), and from what size? That is, what size of difference is absent when the real-data decomposition gave form 1?

Rules fixed beforehand.
- Targets: the 20 CoAuthor-like replicates of the sensitivity experiment (13 dose, 5 structure, 2 distribution); CS1 replicates are excluded because the real CS1 two-step choice selected τ = ∞ for everyone (a = -b). k in {1, 5, 15}, main cells k = 5 and 15. All-symbol quantity only (pressed flags are all 1 in synthetic data).
- Computation: rebuild the synthetic writers, pooled fits and the mode (no new random draws, no own fits; own values are read from the stored replicates; the rebuilt pooled evaluations and planted gains must equal the stored ones bit for bit, and the rebuilt main median must equal the stored one). Rows: two-step choice (main) and τ = 10^6 of ar1-ar3 (secondary); a, b and c are per-writer differences; finite-mode-only tallies are added.
- Reading forms from the mode experiment, read on medians: form 1 |a| < |b| with b having the sign of c; form 2 |a| > |b|, a > 0, good-side share above 0.5; form 3 otherwise; form 5 for infinite medians (read on the finite subset, which needs at least 4 writers). Cells where more than half chose ∞ are not read. A level is "form 2" if both its seeds are; N1 = all 5 null seeds give form 1; the discrimination floor D is the smallest form-2 level above which all are form 2.
- Prewritten actions: keep, weaken or drop the claim that the real-data remainder is not read as an own gain, depending on N1 and D (k = 15 main, k = 5 added).

Gates. Hash checks, zero-probability evaluation equals the standard evaluation, mode uses the pooled fit excluding the writer, ±∞, a + b = c, selection ignores the target writer; mutations u1-u5.

Status. Synthetic only; stated limits as in the sensitivity experiment.

---

## experiments/20261112-selection-split-and-smoothing/conditions.md

First commit: 2026-11-11T15:20:12Z (last commit 2026-11-20T07:08:33Z). The document has four dated addenda: before the real run (2026-11-12), a symmetric version added after the first results had been seen (2026-11-12), a control and chosen-τ report (2026-11-19) and a swap control with a first-symbol check (2026-11-20); the first is an amendment made before any real data were seen, and each of the other three states that it was decided after earlier results had been seen.

Purpose. No fitting of own models is rerun for A; B refits only the pooled fits. A: the choice is made on other writers' medians, but the writers reported were also used in the choice; splitting writers into a choosing half and a reporting half, how much of the remainder is optimism of selection? B1: does choosing the base pseudo-count of the pooled fit (multiplier α in {0.03, 0.1, 0.3, 1, 3}) by others change the remainder when the resulting pooled fit is used as opponent and as the τ = ∞ candidate? B2: choosing the constant added to the own chain (β in {0.01, 0.03, 0.1, 0.3, 0.5, 1, 2}) by others.

Rules fixed beforehand.
- Rows: the two-step choice and τ by others per structure; panels P15 (17 writers), P30 (9), C5 (23).
- A: 1,000 random splits of each panel (about half and half), both directions (2,000 pairs); honest value h (chosen on S, reported on R), same-half value i, optimism o = i - h; P30 values only listed.
- B1 (CoAuthor): refit the pooled fits per multiplier, α chosen by others per writer and structure; the first reproduction gate is α = 1.
- Reading forms: A and B1 are read by the majority of the seven k of P15 ("remains", "shrinks", "vanishes"; B1 also "1x"); B2 "chain finding remains" requires every k in both P15 and C5, and a single failing cell means "changes". Writing actions are prewritten.
- Addenda: a symmetric version refits the own fits with the same multiplier (ar3 only; the multiplier chosen for all 17 writers was the grid's lower end 0.03); a control compares the remainder with a mode-based control (mode at multiplier 0.03 minus pooled) and reports the chosen τ and weight N/(N + τ); a swap control replaces the writer's k units with another writer's k units under the same prior and the same τ; a second check removes the first symbol of each evaluation series. Reading words "exceeds / ties / falls short" and "carries / partly / does not carry" and "remains / shrinks / vanishes" are fixed in advance.

Gates. Split, selection independence, hand-computed h/i/o, floor, scaling of the prior, equality with earlier pooled fits, reproduction gates against stored values; mutations s1-s10, y1-y5, z1-z5, f1-f9.

Status. A series of checks of how much of a small remainder is selection optimism or prior smoothing; limits (grid lower end, ar3 only, no synthetic verification of the symmetric comparison, added after results) are prescribed for the write-up.

---

## experiments/20261112-sensitivity-ten-seeds/conditions.md

First commit: 2026-11-11T15:20:12Z.

Purpose. With only 2 seeds per level, the sensitivity experiment could not state a detection rate or false-alarm rate. Raise the dose-axis (CoAuthor-like, true K = 3) to 10 seeds per level, add 10 more null seeds, and output the detection rate and false-alarm rate of its rule.

Rules fixed beforehand.
- Replicates (55): null levels g* = 0 with seeds 0-4 (threshold) and 5-14 (false alarms); levels 1e-3, 3e-3, 1e-2, 3e-2 with seeds 0-9. Numbers 0-12 are rerun on a second machine so that all 55 use the same machine and versions; their values on the first machine are only compared. λ values are those of the sensitivity experiment's calibration, not recalibrated.
- Rule: U = largest median of null seeds 0-4; a replicate is detected if its median exceeds U and its good-side share is at least 0.8; FA = share of seeds 5-14 detected; DR(g) = share of seeds 0-9 detected at a level; L80 = smallest level with DR of at least 0.8 above which all levels have at least 0.8 (or "none"). Listed only: level medians, recovery ratio, null medians, how many null seeds exceed the real-data range, the old rule on seeds 0-1.
- Write-up actions are prewritten, including for FA above 0.2 ("detection no higher than FA cannot be told from a false alarm") and for no L80.
- Time rule: first-replicate time x 55; above 24 hours, cuts in a fixed order (false-alarm null seeds reduced to 5-9, then planted seeds 8-9 dropped, then 6-7).

Gates. Hash checks, plan equality with the old plan for numbers 0-12 and non-overlap of new numbers 33-74, rule hand-counted, null-detection pairing; mutations e1-e8; a machine-difference record (not a gate).

Status. Detection and false-alarm rates for this generator, this record length and this rule; not a general limit of the procedure; CS1 is not extended.

---

## experiments/20261113-null-from-shared/conditions.md

First commit: 2026-11-13T07:10:46Z.

Purpose. The earlier synthetic null does not reproduce how smoothing acts on real data (the mode beats the pooled fit on real data, but loses on the synthetic one), so a real-data "detection" was not read as detection. Here the true generator is the real pooled fit itself (CoAuthor, ar3, at one prior multiplier chosen so that the mode beats it), and the same rule is applied. The document states that it was added after earlier results (post hoc). Does the real-data remainder then satisfy the rule?

Rules fixed beforehand.
- Data handling: only the pooled fit over all CoAuthor writers (excluding evaluation units) is taken from real data; its parameters (4 multipliers: 1, 0.3, 0.1, 0.03) stay outside the repository and only a hash and aggregates from synthetic data are committed. All synthetic writers share the same m0; heterogeneity enters only through the planted difference.
- Gate: for each multiplier, synthetic zero-difference data (3 gate seeds 100-102, 17 writers) give b = mode minus pooled; the chosen multiplier is the one whose 3-seed median of b is positive for all seeds and closest in log ratio to a real-data b quoted in the earlier experiment; if no multiplier qualifies the run stops and the write-up is unchanged.
- Replicates: the same 55-row plan as the ten-seed experiment, same random streams, λ recalibrated for the chosen m0 (g* in {1e-3, 3e-3, 1e-2, 3e-2}).
- Rule: as in the ten-seed experiment (U', FA', DR', L80'); usable only if FA' is at most 0.2 (2 of 10 seeds); the real-data remainder (median and good-side share, k = 5 and 15) is judged by the same detection formula.
- Readings: G0 gate stop; R1 both k usable and detected; R2 usable and not detected; R3 mixed or unusable; each with a prewritten wording. Recovery ratio is not used to compare planted and returned sizes.

Gates. Code hashes, plan equality, the shape and normalisation of m0 (K = 3, row sums 1 within 1e-9), that the passed m0 is used, sparse-row draws, b hand-checked, selection cases, the real remainder values, reading cases, smoke run; mutations n1-n8. Addendum (before the main run): further hash and write-safety checks.

Status. One synthetic design with no writer heterogeneity in the null; not an estimate of real writers' differences.
