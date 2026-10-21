# NeonRadar phase 3: evaluation and alert design

Research date: Sunday 18 October 2026. Every fact was checked on 2026-10-18 and carries a tag [V1] to [V58] from the Sources list; web pages and PDFs were read with the web fetch tool (it returns summaries and short quotes, because arXiv, regulator and publisher sites refuse direct downloads from this machine), GitHub repositories were cloned read-only and read with git, numbers tagged [V30] were computed here by scripts in Python 3.14 (cross-checked against statsmodels 0.15.0 and scipy 1.18.1), "Inference" marks my reasoning, "Proposal" marks a design suggestion, and UNVERIFIED marks what could not be confirmed.

## 0. Answers for the spec writer

1. **Unit and matching rule.** Score recall per planted scenario and precision per alert, separately for each typology. Never score transactions or accounts as the headline. Match an alert only to scenarios of its own typology, by kind: payment patterns by the overlap (intersection over union, IoU) of the alert's payment edge ids with the scenario's labelled `tx_id`s, matched when IoU is at least 0.5 (the PASCAL VOC convention [V21]); `shell_chain` by the IoU of the chain's entities, at least 0.5; `sanctions_exposure` by the same exposed subject plus the planted sanctioned party in the evidence; `mass_registration_address` (and later agent and director hubs) by the same hub id. Assign one to one, best overlap first, ties broken by `alert_id` then `scenario_id`. A tested reference matcher is in 1.7 [V30].
2. **Counting.** Each alert is exactly one of: true (matched to an illicit scenario), duplicate (overlaps an illicit scenario that another alert already took), look-alike (matched to a planted benign look-alike) or background. Precision is true divided by all alerts, so duplicates count against it, as in VOC [V21]. Recall is detected illicit scenarios divided by planted ones. Publish all four alert counts, the look-alikes alerted out of those planted, and the planted mix. Macro figures are the unweighted mean over typologies; name the macro F1 formula, because two are in use [V25]. Precision with no alerts is undefined: publish n = 0, never 0 or 1 [V24].
3. **What the benchmarks publish.** AMLworld reports transaction-level minority-class F1 only, with no per-pattern results [V6]. SAML-D reports transaction-level TPR, FPR and AUC in figures only, with no per-typology results [V10]. AMLGentex reports account-level average precision above recall 0.6, averaged over 10 seeds with no spread, and no per-typology results [V11]. Tide states "we did not disaggregate performance by pattern type" [V17]. Only Egressy et al. publish per-pattern F1, for GNNs on node labels [V13]. None of these publishes per-typology precision and recall with intervals for rule-based detectors.
4. **How many scenarios.** Reuse the Wilson interval of `er-splink.md` section 9 [V2]. A half-width of 10 points needs 93 scenarios when the observed rate is 0.5, 60 at 0.8 and 37 at 0.9. A half-width of 5 points needs 381, 245 and 141. With 20 scenarios the half-width is 14 to 20 points for observed rates between 0.5 and 0.9. Plan **100 illicit and 100 look-alike scenarios per core typology** on the test seeds (half-width at most 10 points), and 400 later if 5 points are wanted [V30].
5. **Seeds and honesty.** Tune on 10 dev seeds, publish from 10 different test seeds, 10 scenarios per typology per seed. Publish the pooled Wilson interval and a t interval across seeds, and headline the wider one. In a simulation, Wilson alone covered only 69 to 80 percent when seeds differ strongly, a seed bootstrap undercovered with 5 to 10 seeds, and the wider-of-two rule covered 92 to 98.5 percent [V30]. No bootstrap is needed. Freeze parameters before the first test run; log every test run; if parameters change after a look, retire those test seeds and draw new ones [V28][V29].
6. **CI gates.** Build the matcher and the `eval` job in the first week of Phase 3 with `circular_flow`, the only detector that exists, so each new detector lands with its numbers. Three layers. (a) Handcrafted fixtures with exact expected alerts, as M1.9b already does [V1]. (b) A new `eval` job on a committed one-seed fixture `data/fixtures/eval-ci/` (10 illicit and 10 look-alike scenarios per core typology): per-typology counts must equal `eval/baselines/ci.json` exactly (a pull request that changes them updates the file and explains why), recall at least 0.9, zero duplicates, two identical runs, and runtime under budget. (c) The statistical suites: dev seeds nightly and informational; test seeds only by manual dispatch. Stability comes from a committed fixture, `ORDER BY` with an id tie-break before every `LIMIT` [V35], rounded `pattern_strength`, a `PYTHONHASHSEED` test [V34], and a separate Dependabot group for numpy and Faker, whose upgrades may change generated data [V33].
7. **Queue.** Order by priority band, then `pattern_strength` descending, then `alert_id`. Each typology documents its `pattern_strength` as a weighted mean of three or four "closeness to the definition" terms (table in 4.2); it is not comparable across typologies and is never called a risk score [V1]. Dedup: identical evidence already gives an identical id (C4). Proposal: merge same-typology alerts on the same anchor with overlapping windows, keep only maximal paths, raise one alert per subject or hub, and link what still overlaps with an optional `group_id`. Cap the view at 3 alerts per subject per typology and 10 per subject; never cap before evaluation. Publish precision by priority band to show whether the ordering helps.
8. **False positive figures.** Regulators publish SAR counts, not transaction monitoring false positive rates [V39][V40]. The quoted 90 to 98 percent figures come from consultancies (PwC 2010, McKinsey 2019) or from papers citing each other [V36][V37][V19][V47]. The few empirical points (a 2018 bank association survey: about 16 million alerts and over 640,000 SARs; one bank's filtered study sample: about 4 percent reported; one vendor study: under 3 percent of alerted accounts) suggest a few percent of alerts become reports, but their units differ [V38][V45][V46]. Never compare NeonRadar's synthetic precision with them.
9. **Explanations.** C4 already carries the evidence subgraph and its query, ordered steps with edge ids, versions and parameters [V1]. Proposal: add, as optional C4 1.1.0 fields, `explanation.conditions` (each rule with observed value, threshold, margin and a "would not have been raised if" sentence) and `explanation.strength_terms`. Test every counterfactual by re-running the detector with the parameter set just past the observed value. Guidance asks for this kind of traceability: FCA FCG 3.2.5A, Wolfsberg 2025, SR 11-7 and SR 21-8, PRA SS1/23, FATF 2021 [V51][V43][V48][V49][V50][V40].
10. **Is publishing unusual?** Yes. Of six open-source transaction monitoring engines checked, only Osprey publishes measured precision and recall: transaction-level, on the PaySim fraud simulator, added the day before this research, with its own caution [V56][V58]. None publishes per-typology figures with intervals. Screening tools do publish matching accuracy (Watchman) [V57]. Safe wording: "As far as we could find (18 October 2026), no other open-source AML transaction monitoring project publishes per-typology precision and recall, with confidence intervals, measured against labelled scenarios." Do not say "first" or "only".

## 1. Measuring a pattern detector against planted scenarios (question 1)

### 1.1 What the benchmark papers actually report

| Benchmark | Unit scored | Metric | Per pattern or typology? | Runs and spread |
|---|---|---|---|---|
| AMLworld, Altman et al., NeurIPS 2023 Datasets and Benchmarks [V6][V7] | Transaction: "detection of illicit transactions is an edge classification problem" | Minority-class F1 (Table 2); precision and recall in Appendix E; 60-20-20 split after ordering by timestamp | No. Only overall F1 and per-bank F1 (Figure 6). Table 7 counts pattern instances in LI-Large (259 to 298 per pattern), not detections | Table 2 shows plus-or-minus values; the caption does not say what they are. Appendix C mentions training "four models initialized with different random seeds" |
| SAML-D, Oztas et al., ICEBE 2023 [V10] | Transaction | TPR, TNR, FPR, FNR and AUC, shown only in Figures 4 to 6; SVM, naive Bayes, decision tree, random forest; "70-15-15 stratified" split on "a representative subset" | No, although each suspicious transaction carries a typology label | Not stated |
| AMLGentex, Östman et al., 2025 [V11][V12] | Account (node classifiers; `is_sar` per account) | Average precision at recall above 0.6, "P@R>0.6" | No | "averaged over 10 independent seeds"; no standard deviation or interval |
| Elliptic, Weber et al., 2019 [V14] | Transaction | Illicit precision, recall and F1, plus micro F1; "70:30 temporal split" (34 time steps train, 15 test) | No | Not found in what was read (UNVERIFIED) |
| Elliptic2, Bellei et al., 2024 [V15] | Subgraph: 121,810 labelled, 2,763 suspicious | Micro F1, PR-AUC, ROC-AUC | No | One random 80:10:10 split; no repeated runs reported |
| Egressy et al., AAAI 2024, synthetic pattern tasks [V13][V9] | Node, one binary label per pattern | Minority-class F1 per pattern: degree, fan-in, fan-out, cycles of length 2 to 6, scatter-gather, biclique | **Yes**, per pattern | "averaged over five runs"; standard deviations omitted "in favor of readability" |
| FlowScope, Li et al., AAAI 2020 [V16] | Account: accounts in injected dense multi-step flows | F-measure curves and the area under them | Per injected group shape | Not stated |
| Tide, van den Beukel et al., 2026 [V17] | Transaction (inferred from the method; the paper does not say it in one sentence) | PR-AUC "primary"; F1, precision, recall at Youden's J | No: "we did not disaggregate performance by pattern type" | Mean and standard deviation over five runs; for example LightGBM 70.47 plus or minus 27.91 |
| AMLNet, Huda et al., 2025 [V18] | Transaction | F1 0.90, precision 0.84, recall 0.97; ROC AUC 0.88 | No | Ablation by 10-fold cross-validation; no intervals |
| SynthAML, Jensen et al., Scientific Data 2023 [V19] | Alert: 20,000 alerts, about 17 percent reported | ROC AUC | No | Not stated |
| Starnini et al., ECML PKDD 2021, smurf motifs in bank data [V20] | Candidate motifs | None: running time and examples only; thresholds withheld "for security reasons" | Runtime per motif type only | Not applicable |

Two lessons. First, the ML benchmarks score transactions or accounts and report one aggregate number per dataset. Second, pattern-level labels exist in most of them but are rarely used for scoring: AMLworld ships per dataset "A text file list of laundering transactions following one of 8 particular patterns" and warns that "not all laundering in the data follows one of these 8 patterns" [V8]; SAML-D labels every suspicious transaction with its typology [V10]; AMLGentex can split "by pattern ID to prevent data leakage", keeping all nodes of a pattern in one split [V12].

Matching conventions from other fields:

- Object detection (PASCAL VOC): a detection is correct when "the overlap ratio ... must exceed 0.5 (50%)", and "Multiple detections of the same object in an image were considered false detections", for example "5 detections of a single object counted as 1 correct detection and 4 false detections" [V21].
- Time-series ranges: Tatbul et al. define range recall as alpha times an existence reward plus (1 - alpha) times an overlap reward, with a cardinality factor because detecting one real range with one prediction "may be more valuable than doing so with multiple different ranges ... in a fragmented manner" [V22].
- The warning case: crediting a whole anomaly range when any point is hit ("point adjustment") "has a great possibility of overestimating the detection performance"; "even a random anomaly score can easily turn into a state-of-the-art" method [V23]. Inference for NeonRadar: never mark a scenario detected because one of its payments appears in some alert.

### 1.2 Unit of analysis

Proposal:

- **Recall unit: the planted scenario.** A scenario is one pattern instance with a `scenario_id` (M1.8e `labels/scenarios.csv`) [V1].
- **Precision unit: the alert.** An alert is one review decision in the queue.
- **Transactions only decide matches** for payment patterns. Entities decide matches for structure patterns.

Why not transactions or accounts as the headline (Inference): transaction scoring weights a 40-payment fan-in ten times more than a 4-hop cycle and rewards partial evidence; account scoring counts an account twice when it plays two roles and hides which payments raised the alert; and neither matches what the queue shows. For comparison with the ML papers, add one secondary column per payment typology: the share of labelled illicit payments that appear in the evidence of a matched alert.

### 1.3 Matching rule per kind of typology

| Kind | Typologies | Compare | Match when | Why |
|---|---|---|---|---|
| Payment pattern | `structuring`, `rapid_pass_through`, `layering_chain`, `circular_flow`, `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation` (later `cash_commingling`) | The alert's `evidence.edge_ids` restricted to payment (`PAID`) ids, against the scenario's `tx_id`s in `labels/transactions.csv` | IoU at least 0.5 | The alert claims "these payments form the pattern". Payment ids are exact and already labelled. IoU 0.5 is the VOC convention [V21] and tolerates a window that catches most but not all deposits. Non-payment evidence (a `DIRECTOR_OF` edge for dormant reactivation) is ignored |
| Ownership chain | `shell_chain` | Subjects with chain roles (`layer`, `owner`) against scenario participants with the same roles | IoU at least 0.5 | The claim is "these companies and this owner form a layered chain". A chain found from either end, or one layer short, still matches |
| Ownership exposure | `sanctions_exposure` (later `pep_exposure`) | The subject with role `subject`, and the participant with role `sanctioned` (or `pep`) | Same subject, and the planted party is in `evidence.node_ids` | The claim is a pair: "this subject is exposed to that party". Several valid paths can exist, so path overlap would punish a correct alternative path |
| Hub | `mass_registration_address` (later `formation_agent_cluster`, `recycled_directors`) | The subject with role `hub` (address, agent or director) | Same hub id | The claim is about the hub. Member lists are long and may be cut by `LIMIT`, so member overlap is not a stable test |

Generator requirements this implies (Proposal; the label files are generator outputs, not frozen contracts [V1]):

- Write `labels/participants.csv` (`scenario_id, entity_id, role`) next to the existing files, with the role vocabulary of each typology. Keep the `participants` column for compatibility.
- Give every look-alike scenario the same rows and roles as an illicit one (`is_lookalike = true`), and label its payments in `labels/transactions.csv` with `is_illicit = false`.
- Within one seed, do not let two scenarios of the same typology share accounts in overlapping windows, unless a variant tests that on purpose and says so.
- Keep the matching rules in `eval/rules.yaml` keyed by typology slug, not in `detect/typologies/*.yaml`, whose shape is fixed by section 5.4 [V1]. Give the rules a version and print it in every report.

### 1.4 Counting rules

- **Several alerts per scenario.** Only the best-overlapping alert is credited. The others are duplicates and count against precision, as VOC counts them as false detections [V21]. Publish them in their own column, so a reader can see a fragmentation problem rather than a wrong detection.
- **Several scenarios per alert.** The alert is credited to at most one scenario. An over-merged alert that covers two similar planted scenarios has IoU of at most about 0.5 with each, so at most one is detected (Inference). This pushes detectors towards one alert per instance, which is what the queue needs.
- **Look-alikes.** A planted benign look-alike (loan drawdown and repayment, payroll run, registered agent address; section 7.2 [V1]) that draws an alert gives a look-alike false positive. AMLSim's typology-shaped "false alerts" (`is_sar=False`) are the same idea [V3]. Publish "look-alikes alerted / look-alikes planted" per typology. That rate does not depend on the planted mix (2.4).
- **Plain background.** An alert that matches nothing is a background false positive. In a fully synthetic benchmark there are no hidden positives, because the generator plants every illicit scenario; the AMLworld authors make the same point, that with synthetic data "the ground truth labels are complete" [V6]. Inference: a chance pattern in background activity is exactly the false positive a typology file documents.
- **Other typologies.** An alert of typology T on a scenario of typology U counts as a background false positive for T, because T's alerts are matched only against T's scenarios. Also publish a cross-typology table (alerts of T that would match scenarios of U), because the typologies overlap by design (a layering chain contains pass-through accounts).
- **External benchmarks** (optional user downloads such as AMLworld [V3]): use the Patterns file attempts as scenarios. Alerts that land on labelled laundering outside any pattern [V6][V8] need a fifth class, "illicit, not in a pattern", or precision is understated.

### 1.5 Per-typology and macro figures

Columns of the published table, per typology (Proposal):

| Column | Meaning |
|---|---|
| planted, detected, recall, 95% interval | Illicit scenarios on the test seeds and how many were matched |
| alerts, true, precision, 95% interval | All alerts of the typology and the matched ones |
| duplicate, look-alike, background | The three kinds of non-true alerts |
| look-alikes alerted / planted | The rate that does not depend on the mix |
| payment coverage | Secondary: share of labelled illicit payments inside matched evidence |

Rules:

- **Macro** recall and precision: the unweighted mean of the per-typology values, which "does not take label imbalance into account" [V24]. Macro precision averages only typologies with at least one alert, and says how many.
- **Micro** (pooled counts) is reported too, but typologies with many alerts dominate it [V24].
- **Macro F1**: two formulas are in use (mean of per-class F1, or F1 of macro precision and macro recall), and they can differ by "as high as 0.5" [V25]. Use the mean of per-typology F1 and say so.
- **Undefined values**: scikit-learn returns 0 by default when there are no predicted positives, and can return 1 or NaN instead [V24]. NeonRadar should publish "no alerts (n = 0)".
- **Sensitivity**: in an appendix, recompute recall and precision at IoU 0.3 and 0.7. If a figure moves a lot, say so next to it.
- **Caveat**: print the README limitations text next to the table. It already says "Detection rates measured on synthetic data say nothing about how NeonRadar would perform on real data" [V1].

### 1.6 Worked example

On the test seeds a typology has 100 planted scenarios; 92 are detected; there are 130 alerts: 92 true, 8 duplicates, 20 on look-alikes and 10 on background. Recall 92/100 = 0.920 [0.850, 0.959]; precision 92/130 = 0.708 [0.624, 0.779] [V30].

### 1.7 Reference matcher (tested)

Proposal, standard library only. `test_matcher.py` in the [V30] scripts folder runs against this exact code and checks exact matches, a duplicate, an unmatched partial alert, look-alike and background alerts, and the exposure, hub and chain kinds; all assertions pass [V30].

```python
"""Reference matcher for the NeonRadar phase 3 evaluation (proposal; standard library only).

alert:    {"alert_id", "typology", "edge_ids", "node_ids", "subjects": {entity_id: role}}
scenario: {"scenario_id", "typology", "is_lookalike", "tx_ids", "participants": {id: role}}
"""
from collections import Counter

RULES = {  # eval/rules.yaml in the repository; roles come from the typology docs and the generator
    "structuring": {"kind": "payment"}, "rapid_pass_through": {"kind": "payment"},
    "layering_chain": {"kind": "payment"}, "circular_flow": {"kind": "payment"},
    "fan_in_collection": {"kind": "payment"}, "fan_out_distribution": {"kind": "payment"},
    "dormant_reactivation": {"kind": "payment"},
    "shell_chain": {"kind": "chain", "roles": {"layer", "owner"}},
    "sanctions_exposure": {"kind": "exposure"},
    "mass_registration_address": {"kind": "hub"},
}
MIN_IOU = 0.5


def iou(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def with_role(members: dict, roles: set) -> set:
    return {i for i, r in members.items() if r in roles}


def overlap(alert: dict, sc: dict, payment_ids: set) -> float:
    rule = RULES[sc["typology"]]
    if rule["kind"] == "payment":    # IoU over payment edges; other evidence edges are ignored
        return iou(set(alert["edge_ids"]) & payment_ids, set(sc["tx_ids"]))
    if rule["kind"] == "chain":      # IoU over the entities of the ownership chain
        return iou(with_role(alert["subjects"], rule["roles"]), with_role(sc["participants"], rule["roles"]))
    if rule["kind"] == "exposure":   # same exposed subject, and the planted party is in the evidence
        same = with_role(alert["subjects"], {"subject"}) == with_role(sc["participants"], {"subject"})
        return 1.0 if same and with_role(sc["participants"], {"sanctioned"}) <= set(alert["node_ids"]) else 0.0
    return 1.0 if with_role(alert["subjects"], {"hub"}) == with_role(sc["participants"], {"hub"}) else 0.0


def evaluate(typology: str, alerts: list, scenarios: list, payment_ids: set) -> dict:
    al = sorted((a for a in alerts if a["typology"] == typology), key=lambda a: a["alert_id"])
    sc = sorted((s for s in scenarios if s["typology"] == typology), key=lambda s: s["scenario_id"])
    look = {s["scenario_id"] for s in sc if s["is_lookalike"]}
    pairs = [(overlap(a, s, payment_ids), a["alert_id"], s["scenario_id"]) for a in al for s in sc]
    pairs = sorted((p for p in pairs if p[0] >= MIN_IOU), key=lambda p: (-p[0], p[1], p[2]))
    match, taken = {}, set()                      # greedy one-to-one, best overlap first
    for _, aid, sid in pairs:
        if aid not in match and sid not in taken:
            match[aid] = sid
            taken.add(sid)
    near = {}                                     # every scenario each alert overlaps
    for _, aid, sid in pairs:
        near.setdefault(aid, set()).add(sid)
    out = Counter()
    for a in al:
        aid = a["alert_id"]
        if aid in match:
            out["fp_lookalike" if match[aid] in look else "tp"] += 1
        elif near.get(aid, set()) - look:
            out["duplicate"] += 1                 # overlaps an illicit scenario another alert took
        elif near.get(aid):
            out["fp_lookalike"] += 1
        else:
            out["fp_background"] += 1
    planted = [s["scenario_id"] for s in sc if s["scenario_id"] not in look]
    detected = sum(s in taken for s in planted)
    return {
        "typology": typology, "alerts": len(al),
        **{k: out[k] for k in ("tp", "duplicate", "fp_lookalike", "fp_background")},
        "planted": len(planted), "detected": detected,
        "lookalikes": len(look), "lookalikes_alerted": len(look & taken),
        "precision": out["tp"] / len(al) if al else None,   # None: no alerts, publish n = 0
        "recall": detected / len(planted) if planted else None,
    }
```

## 2. Statistics for small samples (question 2)

### 2.1 The interval

Use the Wilson score interval exactly as `er-splink.md` section 9 gives it (formula, z = 1.959964, NIST e-Handbook 7.2.4.1, Wilson 1927; the handbook cites Agresti and Coull 1998 and Brown, Cai and DasGupta 2001 for preferring it to Wald) [V2]. That function, copied unchanged, agrees with `statsmodels.stats.proportion.proportion_confint(method="wilson")` to within 4.5e-16 for every k and n up to 400 [V30]. It behaves at the edges: 20/20 gives [0.839, 1.000] and 0/20 gives [0.000, 0.161]; Clopper-Pearson gives the slightly wider [0.832, 1.000] and [0.000, 0.168] [V30]. Use the same formula for recall (k detected out of n planted) and precision (k true out of n alerts). For precision, n is the number of alerts, which NeonRadar does not control, so plant enough scenarios to produce enough alerts.

### 2.2 Half-widths and sample sizes

Wilson half-width in percentage points, by number of scenarios n and observed rate p [V30]:

| n | p = 0.50 | 0.60 | 0.70 | 0.80 | 0.90 | 0.95 | 0.99 |
|---|---|---|---|---|---|---|---|
| 20 | 20.1 | 19.7 | 18.7 | 16.8 | 13.7 | 11.4 | 8.8 |
| 30 | 16.8 | 16.5 | 15.6 | 13.9 | 11.1 | 8.9 | 6.5 |
| 50 | 13.4 | 13.1 | 12.3 | 10.9 | 8.5 | 6.6 | 4.4 |
| 75 | 11.0 | 10.8 | 10.2 | 8.9 | 6.9 | 5.3 | 3.2 |
| 100 | 9.6 | 9.4 | 8.8 | 7.8 | 6.0 | 4.5 | 2.6 |
| 150 | 7.9 | 7.7 | 7.3 | 6.4 | 4.8 | 3.6 | 2.0 |
| 200 | 6.9 | 6.7 | 6.3 | 5.5 | 4.2 | 3.1 | 1.6 |
| 400 | 4.9 | 4.8 | 4.5 | 3.9 | 3.0 | 2.2 | 1.1 |

Smallest n for a given half-width (Wald formula in brackets, for comparison) [V30]:

| Observed p | Half-width 10 points | Half-width 5 points |
|---|---|---|
| 0.50 | 93 (97) | 381 (385) |
| 0.60 | 89 (93) | 366 (369) |
| 0.70 | 78 (81) | 320 (323) |
| 0.80 | 60 (62) | 245 (246) |
| 0.90 | 37 (35) | 141 (139) |
| 0.95 | 25 (19) | 83 (73) |
| 0.99 | 17 (4) | 43 (16) |

The 5-point column matches `er-splink.md` (381, 245, 141) [V2]. Near p = 1 the Wald formula asks for far too few, which is one reason not to use it.

Recommendation (Proposal): plan for the worst case, p = 0.5, because a new detector's rate is unknown. 100 illicit scenarios per typology guarantees a half-width of at most 9.6 points; 400 guarantees 4.9. For Phase 3 use 100 per typology on the test seeds (1,000 illicit scenarios across the ten core typologies) plus the same number of look-alikes. With 20 scenarios a typology's figure is only indicative (half-width 14 to 20 points for rates between 0.5 and 0.9); say so if a typology ships with fewer.

### 2.3 Generator seeds: pooled Wilson, across-seed t interval, or bootstrap

Scenarios planted in the same seed share background activity, so their outcomes may be correlated. Field and Welsh show that resampling whole clusters (the cluster bootstrap) "gives consistent estimates under both the transformation and the random-effect model" [V26]. Data sampling is a large source of benchmark variance in general [V27]. For a deterministic rule-based detector, the generator seed is the only random input (Inference).

Inference: bootstrapping individual scenarios ignores the shared background and gives intervals about as narrow as Wilson, so if anything is resampled it should be whole seeds. I simulated recall with S seeds and m scenarios of one typology per seed, base recall 0.8, and a seed effect on the logit scale with standard deviation 0, 0.5 or 1.0 (400 repetitions, 1,000 bootstrap resamples; Monte Carlo error about 1 point) [V30]. Coverage of a nominal 95 percent interval:

| Seeds x scenarios | Seed effect | Pooled Wilson | Seed bootstrap (percentile) | t interval across seeds |
|---|---|---|---|---|
| 5 x 20 | none | 0.940 | 0.858 | 0.945 |
| 5 x 20 | strong (1.0) | 0.693 | 0.833 | 0.920 |
| 10 x 10 | none | 0.935 | 0.912 | 0.948 |
| 10 x 10 | moderate (0.5) | 0.882 | 0.870 | 0.905 |
| 10 x 10 | strong (1.0) | 0.802 | 0.875 | 0.932 |
| 20 x 10 | strong (1.0) | 0.795 | 0.910 | 0.940 |

Headlining the wider of the pooled Wilson and the across-seed t interval covered 92 to 98.5 percent in all 18 settings tried (base recall 0.8 and 0.95; 10 x 10, 10 x 20 and 20 x 10; three seed effects; 1,000 repetitions) [V30].

Recommendation (Proposal):

1. Per typology, publish the pooled Wilson interval and the t interval across seeds (mean of per-seed recall, t quantile 2.262 for 10 seeds [V30]), clipped to [0, 1]. Headline the wider and keep both in the detailed report.
2. Publish a per-seed table (`eval/reports/<run>/per_seed.csv`: seed, typology, planted, detected, alerts, true, duplicate, look-alike, background) and the minimum, median and maximum per-seed recall.
3. Do not bootstrap: with 10 seeds the percentile seed bootstrap undercovered (87 to 91 percent) [V30]. For macro figures, compute the macro value per seed and use the same t interval across seeds.
4. Worked example: per-seed recall 1.0, 0.9, 1.0, 0.8, 0.9, 1.0, 0.9, 0.9, 1.0, 0.8 (92 of 100): pooled Wilson [0.850, 0.959], t interval [0.864, 0.976]; the t interval is wider, so it is the headline [V30].

### 2.4 Precision depends on the planted mix

Precision on synthetic data is a property of the detector and of the generator's mix. Inference: with N illicit and L look-alike scenarios, recall r, look-alike alert rate a, D duplicates and B background alerts, expected precision is about r x N / (r x N + a x L + D + B). Halving the look-alikes raises precision without any change to the detector. So publish N, L, a and B with every precision figure, and keep the mix fixed across releases (Proposal: one look-alike per illicit scenario).

### 2.5 Holdout seeds and how to document them

- **Why**: choosing parameters on the same data that is then reported produces "a form of selection bias" in the evaluation [V28]. The FCA warns about "firms optimising their systems to detect the specific typologies embedded in the dataset", says users "should not treat the dataset as exhaustive", and varied its typologies so "suspicious behaviour does not appear in identical forms each time" [V29].
- **Seeds file** (Proposal):

```yaml
# eval/seeds.yaml
ci: [1001]                   # the committed eval-ci fixture; a dev seed
dev: [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]
test: [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010]
test_frozen_at: null         # commit sha of detect/typologies/ when parameters were frozen
retired_test_sets: []        # earlier test lists, each with the date and the reason
```

- **Rules** (Proposal): `neonradar eval run --suite test` refuses to run unless `test_frozen_at` is set and `detect/typologies/` is unchanged since that commit. Every test run is appended to `docs/eval/tuning-log.md` (date, commit, who, why). If a parameter changes after a test run, move the seeds to `retired_test_sets` and draw new ones; with a generator, fresh seeds are free.
- **Held-out variants** (Proposal, following `synthetic-docs-mcp.md` A5 [V3]): each typology has at least one generator variant (for example a different hop count or timing) that appears only in test seeds. The typology researcher defines it; detector authors do not see its parameters before the freeze.
- **What the README states**: "Parameters tuned on dev seeds 1001 to 1010. Figures measured on test seeds 2001 to 2010, first run on <date> after parameters were frozen at <sha>. Generator <version>, detectors <versions>, matching rules v<n>."

## 3. Regression gates in CI (question 3)

### 3.1 Three layers

| Layer | Data | Purpose | When |
|---|---|---|---|
| Unit fixtures | Handcrafted cases with `expected.json` (M1.9b cases A to F) [V1] | The query encodes the definition: must-find and must-not-find cases | Every pull request (`integration` job) |
| `eval-ci` | Committed fixture `data/fixtures/eval-ci/`: one dev seed, 10 illicit and 10 look-alike scenarios per core typology, plus background | Regressions in counts, determinism, runtime | Every pull request (new `eval` job) |
| Statistical suites | Generated in CI from `eval/seeds.yaml` | Dev suite: track progress. Test suite: the published table | Dev: nightly, informational. Test: manual `workflow_dispatch` only |

The plan asks for "One script, one table, run in CI" [V4]; the table comes from the test suite, the gate from `eval-ci`.

### 3.2 What to gate, and tolerances

| Gate on `eval-ci` | Rule | Tolerance |
|---|---|---|
| Per-typology counts (alerts, true, duplicate, look-alike, background, planted, detected) | Equal `eval/baselines/ci.json` | Zero. The data and the detectors are deterministic, so any change is real. A pull request that changes a count updates the baseline in the same pull request and explains the change; CODEOWNERS puts the Detection squad on `eval/baselines/` |
| Recall per core typology | At least 0.9 (at most one of ten missed) | Floor, a starting point for the detect mentor |
| Duplicates | 0 | None |
| Determinism | Two runs give the same sorted alert ids and identical alert files apart from `run_id` and `created_at` | None |
| Runtime | Each detector within its budget in `eval/budgets.yaml` | Fail above the absolute budget; warn above twice the baseline time |

Do not gate precision floors tightly: precision depends on the planted mix (2.4). Do not gate on statistical intervals in pull requests: 9 of 10 gives [0.596, 0.982] [V30], too wide to separate a regression from noise, while exact counts on fixed data catch every change.

### 3.3 Runtime budgets

- Runner: until launch the repository may be private (M1.6 plan limitation [V1]). A standard private Linux runner has 2 CPUs and 8 GB RAM; a public one has 4 CPUs and 16 GB [V31]. Set budgets for the private runner.
- Proposal: `eval` job `timeout-minutes: 15`; the eval-ci run (Neo4j start, load, ten detectors, matching) under 10 minutes; each detector under 30 seconds on eval-ci. Measure in the first Phase 3 week and write the measured times into `eval/budgets.yaml` (UNVERIFIED until measured).
- Run every detector query with a driver timeout, as Phase 2 does for API queries with `neo4j.Query(text, timeout=5.0)` [V5], so a runaway variable-length match fails the test instead of the job.
- The plan's "every demo query returning in under 2 seconds" [V4] is for interactive queries. Batch detection at the scale target needs its own figure, published with the hardware (UNVERIFIED until measured).

### 3.4 Keeping gates stable

- **Commit the eval-ci fixture.** NumPy promises the same stream only "on the same build of numpy, in the same environment, on the same machine", and allows `Generator` changes on feature releases [V33]. A committed fixture makes the gate independent of that. A separate test regenerates the fixture with the locked dependencies and compares SHA-256, like the M1.8e determinism test [V1].
- **Dependabot**: the Phase 1 config groups all Python minor and patch updates [V1]. Proposal: a separate group for `numpy` and `faker`, so their upgrades arrive alone and regenerate the fixtures and baselines in the same pull request.
- **Ordering**: "Unless ORDER BY is used, Neo4j does not guarantee the row order of a query result" [V35]. Every detector query that uses `LIMIT` (M1.9b requires one [V1]) must `ORDER BY` a total order ending in an id, or different runs may keep different rows.
- **Hash order**: if `PYTHONHASHSEED` is unset, "a random value is used to seed the hashes of str and bytes objects" [V34], so set iteration order varies between processes. Test: run the generator and the runner under two different `PYTHONHASHSEED` values and compare outputs byte for byte. Do not hide the problem by fixing the variable in CI.
- **Floats**: round `pattern_strength` half up to 4 decimals before banding and storing, as Phase 2 rounds effective shares to 4 decimals before filtering [V5]. NumPy notes that CPUs differ in floating-point edge cases [V33].
- **Pins**: Neo4j image `neo4j:5.26.32-community` as in Phase 1 CI [V1]; Python and packages from `uv.lock`; versions recorded in every report.
- **Scheduled runs**: GitHub's `schedule` event "can be delayed during periods of high loads", queued jobs "may be dropped", it runs on the default branch only, and in a public repository scheduled workflows "are automatically disabled when no repository activity has occurred in 60 days" [V32]. Keep the nightly suite informational, never a required check.

### 3.5 The job (fragment for `.github/workflows/ci.yml`)

```yaml
# add under jobs: in .github/workflows/ci.yml (same pinned actions as Phase 1)
eval:
  runs-on: ubuntu-24.04
  timeout-minutes: 15
  steps:
    - uses: actions/checkout@v7
    - name: ICU headers for PyICU
      run: sudo apt-get update && sudo apt-get install -y --no-install-recommends pkg-config libicu-dev
    - uses: astral-sh/setup-uv@v10.3.0
      with:
        enable-cache: true
    - run: uv python install 3.14
    - run: uv sync --all-packages --locked
    - run: uv run neonradar eval run --suite ci --compare eval/baselines/ci.json --budgets eval/budgets.yaml
      env:
        NR_NEO4J_IMAGE: neo4j:5.26.32-community
```

Add `eval` to the required checks in `scripts/setup_repo_protection.sh` (M1.6) [V1].

## 4. Alert queue design (question 4)

### 4.1 Ordering

C4 fixes the bands: `pattern_strength` of at least 0.75 is high, at least 0.5 medium, else low, unless a typology documents its own rule; and `pattern_strength` is "Never called a risk or suspicion score" [V1]. Proposal: order by band, then `pattern_strength` descending, then `alert_id`, so the order is total and repeatable [V35]. The query assumes the M1.9b loader copies `priority` and `pattern_strength` onto `:Alert`:

```cypher
MATCH (a:Alert)
RETURN a.alert_id AS alert_id, a.typology AS typology, a.priority AS priority, a.pattern_strength AS pattern_strength
ORDER BY CASE a.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, a.pattern_strength DESC, a.alert_id
LIMIT 50
```

Each typology has its own formula, so values are comparable within a typology, not across typologies (Inference). Publish the band counts per typology; if one typology fills the high band, give it a documented priority rule.

### 4.2 Pattern strength per typology

Proposal. The circular-flow formula of M1.9b is the template: a weighted mean of terms in [0, 1], each measuring closeness to the typology's definition in section 7.2, clipped to [0, 1], documented in the detector docstring and the typology document [V1]. Parameter names are placeholders for the typology researcher; weights are starting points, not findings.

| Typology | Terms (each in [0, 1]) | Weights |
|---|---|---|
| `structuring` | deposits: min(1, n / (2 x min_deposits)); closeness: mean of (amount / threshold - (1 - band)) / band; branches: min(1, (branches - 1) / 2); daily total above the threshold: 1 or 0 | 0.3, 0.3, 0.2, 0.2 |
| `rapid_pass_through` | pass-through: min(1, outflow / inflow) within the dwell window; speed: 1 - median dwell / max_dwell; sender spread: min(1, senders / (2 x min_senders)) | 0.4, 0.4, 0.2 |
| `layering_chain` | length: min(1, (hops - 2) / 4); retention: last amount / first amount; speed: 1 - duration / max_window; shared context: share of intermediate holders sharing an address, agent or director with another holder in the chain | 0.25 each |
| `circular_flow` | M1.9b: return ratio; 1 - duration / window; min(1, (cycle length - 1) / 4) | 0.5, 0.3, 0.2 |
| `fan_in_collection` | senders: min(1, senders / (2 x min_senders)); novelty: share of senders with no earlier payment to the collector; speed: 1 - window used / max_window; onward: min(1, onward outflow / inflow) | 0.3, 0.3, 0.2, 0.2 |
| `fan_out_distribution` | recipients: min(1, recipients / (2 x min_recipients)); novelty: share of recipients with no earlier relationship; similarity: 1 - coefficient of variation of amounts; onward: share of recipients that withdraw cash or pay on soon after | 0.3, 0.3, 0.2, 0.2 |
| `dormant_reactivation` | gap: min(1, gap_days / (2 x min_gap_days)); burst: min(1, burst payments / (2 x min_burst)); speed: 1 - burst duration / max_burst_window; control change: 1 if a `DIRECTOR_OF` or `OWNS` relationship on the holder started shortly before the burst | 0.3, 0.3, 0.2, 0.2 |
| `shell_chain` | layers: min(1, (layers - 1) / 3); jurisdictions: min(1, (jurisdictions - 1) / 2); nominees: share of chain companies with a nominee director or a director above the appointments parameter; end: 1 if the chain ends at a company with no recorded owner or loops back, 0.5 if it ends at a person | 0.25 each |
| `mass_registration_address` | registrations: min(1, registered companies / (2 x min_registrations)); internal payments: share of those companies that pay or are paid by another company at the address; burst: largest share incorporated within one 90-day span | 0.4, 0.4, 0.2 |
| `sanctions_exposure` | share: largest effective share (lower bound) held by a sanctioned owner; distance: 1 - (hops - 1) / 6; control: 1 if a `CONTROLS` or `DIRECTOR_OF` link to the sanctioned party is in the evidence. Documented priority rule: high whenever the OFAC-style pass-down flag of section 7.2 holds | 0.6, 0.2, 0.2 |

Check that the heuristic helps (Proposal): publish precision per band on the test suite. If high-band precision is not above low-band precision, the formula is not ordering the queue usefully and should be revised on dev seeds. The AMLGentex code offers the related "Precision@K" as an "alert budget" metric [V12]; publish precision in the top 10 and top 50 of the mixed queue as well.

### 4.3 Deduplication, merging and linking

- **Identical evidence**: C4's `alert_id` is SHA-1 over typology, detector version, sorted edge ids and sorted node ids, so re-running gives the same ids and the loader MERGEs on them [V1]. Ids change when the detector version changes, so the evaluation matches on evidence, never on ids.
- **Merge at the source** (Proposal; no contract change; the evaluation sees the merged output, which is what the queue shows):
  - Payment patterns with one anchor account (`structuring`, `rapid_pass_through`, `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation`): merge alerts of one typology on the same anchor whose windows overlap. Recompute metrics and `pattern_strength` on the union; the union evidence gives the new id.
  - Path patterns (`layering_chain`, `circular_flow`): keep only maximal paths. Drop an alert whose payment edges are a subset of another alert's of the same typology. The time-ordering rule already finds each cycle once [V1].
  - Ownership and hub typologies: one alert per subject (or hub) per run, with all qualifying paths in the evidence up to the evidence limits.
- **Link what still overlaps** (Proposal, optional C4 1.1.0 field): same-typology alerts that share at least one evidence edge form a group; `group_id` is `grp-` plus the first 20 hex characters of SHA-1 over the sorted member `alert_id`s joined with `|`, mirroring the alert id rule. The UI shows one row per group. Fallback without a contract change: group by subject at query time through the existing `FLAGS` relationships.
- **Across typologies**: never merge; different typologies are different statements. The queue can show "also matches the graph pattern of ..." from shared subjects.

The C4 additions in this note (`group_id`, `explanation.conditions`, `explanation.strength_terms`) are additive and optional, so they fit a minor version, 1.1.0, through a `contract-change` issue approved by the tech lead [V1].

### 4.4 Caps per entity

Proposal: the queue view shows at most 3 alerts per (subject, typology) and 10 per subject, best first, with "n more" behind a link. Caps apply in the API, never in the detector, so recall and precision are measured before caps, and precision in the top K after caps. Inference: caps also limit how many structural-pattern alerts sit next to one large real company, whose generated background activity can form payroll-like fan-outs.

### 4.5 What is known about alert volumes and false positives

| Source | Kind of source | What it says | Basis |
|---|---|---|---|
| FCA, analysis of REP-CRIM data 2017 to 2020, 7 October 2021 [V39] | UK regulator | 2019/20: 1,028,260 internal suspicious activity reports and 480,202 external SARs; external reports "are a subset" of internal ones (about 47 percent, my arithmetic). No alert counts, no false positive rates | Firms' regulatory returns |
| FATF, Opportunities and Challenges of New Technologies for AML/CFT, July 2021 [V40] | Standard setter | No figure for false positive rates or alert volumes; reductions of false positive alerts appear as case outcomes (for example Brazilian institutions) | Consultation of members and firms |
| HKMA, AML/CFT Regtech Case Studies and Insights Volume 2, September 2023 [V41] | Regulator publishing bank case studies | Bank self-reported effects, for example one bank auto-closes "7% of TM alerts", "subject to sample checking"; no HKMA measurement | Bank self-reports |
| Wolfsberg Group, Statement on Effective Monitoring for Suspicious Activity, Part I (2024) and Part II (2025) [V42][V43][V44] | "an association of 12 member banks" | "alert productivity, or alert-to-SAR/STR ratios" are limited by "their focus on the quantity, as opposed to the usefulness"; "There are many reasonable explanations for models to have low productivity" | Expert statement |
| Bank Policy Institute, Getting to Effectiveness, 29 October 2018 [V38] | Bank industry association survey | "In 2017, survey participants reviewed approximately 16 million alerts, filed over 640,000 suspicious activity reports" (19 banks; about 4 SARs per 100 alerts, my arithmetic); a median of 4 percent of SARs led to law enforcement follow-up | Member survey |
| Jullum et al., Journal of Money Laundering Control, 2020 [V45] | Academic, with co-authors from the bank (DNB) | Training data: 603 reported out of 14,385 alerted transactions (about 4 percent, my arithmetic), after filtering to one alerted transaction per case | One bank, filtered sample; not a population rate |
| Naser Eddin et al., arXiv 2021 [V46] | Vendor-authored (Feedzai, with the University of Porto) | Suspicious accounts are "less than 3% of the alerted ones" among about half a million alerted transfers over about a year | One bank, account level |
| PwC, September 2010 [V36] | Consultancy | "90 percent to 95 percent of all alerts generated by AML alert engines are false positives" | "PwC analysis"; method not given |
| McKinsey compendium (article dated September 2019) [V37] | Consultancy | Transaction monitoring models "often exhibit false positive rates of over 98 percent" | No basis given |
| SynthAML (2023), citing Gerlings and Constantiou (HICSS 2023), citing Han et al. (2020) [V19][V47] | Academic papers citing each other | "false positive rates can be 95% to 98%"; "over 90% of all alerts generated are false positives" | Ends at a literature review whose own source was not read (UNVERIFIED) |
| AMLGentex (2025) [V11] | Academic | False positive rates "often as high as" 90 to 98 percent, citing PwC 2010 and McKinsey; 0.98 used as a calibration target, citing a PwC Luxembourg survey | Consultancy sources |

What follows (Inference):

- No regulator source found publishes a measured, industry-wide false positive rate for transaction monitoring. Regulators publish SAR counts.
- The 90 to 98 percent figures should be quoted only with their consultancy origin.
- The empirical points (BPI, DNB sample, Feedzai bank) are consistent with a few percent of alerts becoming reports, but they count different things: alerts, alerted transactions, alerted accounts.
- In industry usage, an alert closed without a report counts as a false positive even when the pattern was really present and benign. NeonRadar's synthetic precision measures something else: whether the alert sits on a planted illicit scenario. The two must never appear in one comparison.

## 5. Explanations (question 5)

### 5.1 What guidance asks for

- UK FCA, Financial Crime Guide FCG 3.2.5A, good practice: "records of decision making and rationales for thresholds are documented and accessible". Poor practice: "A firm using an automated system lacks an understanding of what the system is detecting and why", and a poorly calibrated rule-driven system where "the firm struggles to articulate the rationale for particular rules and scenarios". FCG 3.2.5B (case study): "certain thresholds set made it almost impossible for the relevant scenarios to identify potentially suspicious activity" [V51].
- Wolfsberg Part II (2025): "there is always a need to explain why an alert was generated in the first place"; "Explainability to demonstrate transparency in coverage and effectiveness"; "evidencing risk coverage involves mapping risk indicators to typologies and scenarios" [V43]. The 2022 AI/ML principles: "ensure that results can be adequately explained or proven given the data inputs" [V52].
- US SR 11-7 (Federal Reserve and OCC, 4 April 2011): "documentation of model development and validation that is sufficiently detailed"; effective challenge is "critical analysis by objective, informed parties that can identify model limitations and produce appropriate changes"; outcomes analysis means "comparing model outputs to corresponding actual outcomes" [V48]. SR 21-8 (9 April 2021; Federal Reserve, FDIC and OCC): the guidance "does not have the force and effect of law"; "While some BSA/AML systems may constitute models under this description, others may not"; "Stand-alone, simple tools that flag transactions based on a singular factor" may not be models; prudent practice "involves periodically reviewing and testing the filtering criteria and thresholds" [V49].
- UK PRA SS1/23 (published 17 May 2023, effective 17 May 2024, revised version dated 23 April 2026; it applies to banks with internal-model approval for regulatory capital and is not AML guidance): explainability is "the degree to which the workings of a model can be understood in nontechnical terms"; documentation should let a third party "identify the key model assumptions and limitations" [V50].
- FATF (2021): "Regulated entities must be able to explain, and remain responsible for, the principles and technical details" [V40].
- Research: explanations "are contrastive", "sought in response to particular counter-factual cases" (Miller, Artificial Intelligence 267, 2019) [V53]; counterfactual explanations "describe the smallest change to the world that can be made to obtain a desirable outcome" (Wachter, Mittelstadt and Russell, Harvard Journal of Law and Technology 31(2), 2018) [V54]. In a bank's transaction monitoring case study, a capacity planner feared investigators would "spend time scratching their heads over why TMM gave a high score" [V47].

Inference: for a rule-based detector the counterfactual is exact and cheap, because the rule is a conjunction of thresholds. That is a real advantage of NeonRadar's approach and the explanation should show it.

### 5.2 Checklist for a NeonRadar alert explanation

| Element | In C4 v1.0.0? [V1] | Rule |
|---|---|---|
| Evidence subgraph | Yes: `evidence.node_ids`, `edge_ids`, optional `window` | Only what the rule used; the UI draws exactly this |
| Reproducible query | Yes: `evidence.query` (`cypher`, `parameters`) | Re-running it returns the same evidence |
| Ordered steps | Yes: `explanation.steps` with `edge_ids`, at most 280 characters each | One step per hop or event, in time order; each cites its edges |
| Parameters and versions | Yes: `evidence.query.parameters`, `detector.version`, `typology_version` | Every threshold that applied, with its value |
| Conditions and counterfactual | No | Proposal: optional `explanation.conditions` (C4 1.1.0): each predicate with observed value, comparator, threshold, margin and one "would not have been raised if" sentence |
| Pattern strength breakdown | No | Proposal: optional `explanation.strength_terms`: name, value, weight, contribution |
| Look-alikes | Yes: `false_positive_notes` | From the typology file |
| Data provenance | Yes: `data_flags`, `wording_class`, `disclaimer_id` | Unchanged |

Fallback without a contract change: put margins in `metrics` (typology-documented numbers) and the counterfactual sentence in `summary`. Every sentence passes the wording lint of section 7.1 [V1].

### 5.3 Example: the C4 circular-flow alert

For the C4 example (return ratio 0.96, 151.7 hours, 4 hops, window 14 days) the strength terms are 0.4800 + 0.1646 + 0.1500 = 0.7946, shown as 0.79 [V30][V1]:

```json
{
  "conditions": [
    {"name": "duration_days", "observed": 6.32, "comparator": "<=", "threshold": 14, "parameter": "max_window_days", "margin": 7.68,
     "text": "Would not have been raised if the funds had taken more than 14 days to return; they took 6.3 days."},
    {"name": "return_ratio", "observed": 0.96, "comparator": ">=", "threshold": 0.8, "parameter": "min_return_ratio", "margin": 0.16,
     "text": "Would not have been raised if less than 80 percent had returned; 96 percent did."},
    {"name": "cycle_length", "observed": 4, "comparator": "between", "threshold": [2, 6], "parameter": "min_hops, max_hops", "margin": 2,
     "text": "Would not have been raised with more than 6 transfers in the cycle; there were 4."},
    {"name": "time_order", "observed": true, "comparator": "==", "threshold": true, "parameter": null, "margin": null,
     "text": "Would not have been raised if any transfer had happened before the previous one."}
  ],
  "strength_terms": [
    {"name": "return_ratio", "value": 0.96, "weight": 0.5, "contribution": 0.48},
    {"name": "speed", "value": 0.5485, "weight": 0.3, "contribution": 0.1646},
    {"name": "length", "value": 0.75, "weight": 0.2, "contribution": 0.15}
  ]
}
```

### 5.4 Tests that keep explanations checkable

- **Evidence test**: re-run `evidence.query` with its parameters; it must return exactly the evidence ids.
- **Counterfactual test** (Proposal, property test on the unit fixtures): for each numeric condition, re-run the detector with the parameter moved just past the observed value (for example `max_window_days = 6` for a 6.3-day cycle); the alert must disappear, and must stay when the parameter moves the other way. When the needed value lies outside the parameter's allowed range in the typology file, the sentence says the alert cannot be removed within the allowed settings.
- **Step test**: every step's `edge_ids` are a subset of `evidence.edge_ids`, and steps are in time order.
- **Strength test**: the contributions add up to `pattern_strength` after the documented rounding.

## 6. What open-source AML detection projects publish about accuracy (question 6)

### 6.1 Projects checked

Method: the top 20 repositories by stars on the GitHub topics `anti-money-laundering` (151 repositories) and `transaction-monitoring` (162) [V55], two curated lists, and the engines they name. Each was cloned and its README and documentation searched for precision, recall, accuracy, false positive and benchmark [V56][V57][V58].

| Project | Licence | What it is | Detection accuracy published? |
|---|---|---|---|
| Jube | AGPL-3.0 | Real-time AML and fraud monitoring with rules, ML and case management | No figures found; the documentation covers threshold setting and software tests [V58] |
| Marble | Elastic License 2.0 (source-available; describes its core as open source) | Decision engine for monitoring, screening and cases | No [V58] |
| Tazama | Apache-2.0 | Real-time monitoring with rules and typologies | Lists "Performance Analytics" for "detection accuracy and false positive rates" as a feature; its published benchmarks measure throughput (ArangoDB set-ups) [V58] |
| ezrules | Apache-2.0 | Rule engine with backtesting | Computes precision, recall and F1 per rule from the user's own labels; publishes no figures of its own [V58] |
| blnk watch | Apache-2.0 | Language for monitoring rules | No [V58] |
| Osprey | Apache-2.0 | CEL rule engine with FATF-inspired typologies (50 commits since January 2026) | **Yes**: transaction-level precision and recall of its rule sets on all 6,362,620 PaySim rows (a mobile-money fraud simulator); its PaySim rules reach 97.6 percent recall at 100 percent precision, its FATF rules 0.3 percent recall at 0.2 percent precision; added on 17 October 2026 in an unreleased change, with "CAUTION: These numbers do not show quality on real traffic" and "A fair test of the FATF rules needs an AML dataset" [V56] |
| Watchman (screening, not monitoring) | Apache-2.0 | Sanctions screening service | **Yes**: precision and recall on 472,477 labelled pairs from the OpenSanctions Pairs benchmark; at its default cut-off of 0.80 precision 0.99 with recall 0.69 [V57] |

Research code publishes model scores, not detector accuracy per typology: IBM Multi-GNN computes binary F1 on transactions (`sklearn.metrics.f1_score`) [V9]; AMLGentex reports account-level average precision [V11][V12]; GARG-AML reproduces AUC-ROC and AUC-PR tables [V58]; Egressy et al. report per-pattern F1 for GNNs on synthetic node labels [V13]; a rule-like motif paper on real bank data reported running time only [V20]. Generators such as SantanderAI's gen-fraud-graph publish pattern metadata but no detector results [V58].

### 6.2 What NeonRadar can say

- The plan's claim that "almost no project in this space publishes" precision and recall [V4] holds, with one nuance: a small rule engine started publishing transaction-level PaySim figures one day before this research [V56].
- Suggested README wording: "As far as we could find on 18 October 2026, no other open-source AML transaction monitoring project publishes per-typology precision and recall, with confidence intervals, measured against labelled synthetic scenarios. Research datasets publish model scores at transaction or account level, and screening tools publish matching accuracy."
- Avoid "first" and "only": the search covered GitHub topics and named projects, not every repository.
- Re-run the search before launch (Phase 6), because Osprey and Tazama are active.

## Sources

- [V1] NeonRadar build spec, Phase 1, `/home/claude/neonradar-phase1/doc/PHASE-1.md`: 5.0 contract rules, 5.4 C4 alert v1.0.0 and the typology file shape, M1.6 CI (ci.yml, Dependabot, plan limitation), M1.8e label files, M1.9b circular-flow detector and `pattern_strength`, 7.1 wording, 7.2 typology catalog. Read 2026-10-18.
- [V2] NeonRadar phase 2 research note `/home/claude/neonradar-phase2/research/er-splink.md`, section 9 (Wilson interval, sample sizes), with its sources NIST/SEMATECH e-Handbook 7.2.4.1 https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm and Wilson (1927) https://doi.org/10.1080/01621459.1927.10502953 . Reused, not re-verified, 2026-10-18.
- [V3] NeonRadar phase 1 research note `/home/claude/neonradar-phase1/kit/research/synthetic-docs-mcp.md`, part A (AMLworld, SAML-D, AMLGentex, Tide, FCA synthetic data; written 2026-10-16). Read 2026-10-18.
- [V4] NeonRadar project plan `/home/claude/neonradar-phase1/kit/neonradar-project-plan.md` (lines 102, 157, 318, 379 to 380). Read 2026-10-18.
- [V5] NeonRadar build spec, Phase 2, `/home/claude/neonradar-phase2/doc/PHASE-2.md` (M2 ownership queries: `neo4j.Query(text, timeout=5.0)`, rounding to 4 decimals). Read 2026-10-18.
- [V6] Altman et al., "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models", arXiv 2306.16424v3 (2024-01-25): https://arxiv.org/abs/2306.16424v3 ; https://arxiv.org/pdf/2306.16424v3 . Checked 2026-10-18.
- [V7] NeurIPS 2023 Datasets and Benchmarks proceedings page: https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f38404edff6f3f642d6fa5892479c42-Abstract.html . Checked 2026-10-18.
- [V8] Kaggle API metadata, IBM Transactions for Anti Money Laundering (AML), version 8, updated 2025-07-08: https://www.kaggle.com/api/v1/datasets/view/ealtman2019/ibm-transactions-for-anti-money-laundering-aml . Checked 2026-10-18.
- [V9] IBM/Multi-GNN, read-only clone at 252b025 (2024-02-13): `README.md`, `train_util.py`, `training.py`: https://github.com/IBM/Multi-GNN . Checked 2026-10-18.
- [V10] Oztas et al., "Enhancing Anti-Money Laundering: Development of a Synthetic Transaction Monitoring Dataset", ICEBE 2023, accepted manuscript: https://eprints.bournemouth.ac.uk/40982/1/Full_IEEE_Dataset_Conference_Paper%20%284%29.pdf . Checked 2026-10-18.
- [V11] Östman et al., "AMLgentex: Mobilizing Data-Driven Research to Combat Money Laundering", arXiv 2506.13989v2 (2025-09-25), including references [7], [22], [23], [32]: https://arxiv.org/abs/2506.13989 ; https://arxiv.org/pdf/2506.13989v2 . Checked 2026-10-18.
- [V12] aidotse/AMLGentex, read-only clone at 4b9a69d (2026-02-22): `src/ml/metrics/metrics.py` (`constrained_utility_metric`, Precision@K as "alert budget"), `README.md` (per-account features, `is_sar`, pattern-based split): https://github.com/aidotse/AMLGentex . Checked 2026-10-18.
- [V13] Egressy et al., "Provably Powerful Graph Neural Networks for Directed Multigraphs", AAAI 2024 (venue per [V9] README), arXiv 2306.11586: https://arxiv.org/pdf/2306.11586 . Checked 2026-10-18.
- [V14] Weber et al., "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics", arXiv 1908.02591: https://arxiv.org/abs/1908.02591 ; https://arxiv.org/pdf/1908.02591v1 . Checked 2026-10-18.
- [V15] Bellei et al., "The Shape of Money Laundering: Subgraph Representation Learning on the Blockchain with the Elliptic2 Dataset", arXiv 2404.19109v3: https://arxiv.org/abs/2404.19109 ; https://arxiv.org/pdf/2404.19109v3 . Checked 2026-10-18.
- [V16] Li et al., "FlowScope: Spotting Money Laundering Based on Graphs", AAAI 2020: https://ojs.aaai.org/index.php/AAAI/article/view/5906 ; https://ojs.aaai.org/index.php/AAAI/article/view/5906/5762 . Checked 2026-10-18.
- [V17] van den Beukel, Rožanec and Varbanescu, "Tide: A Customisable Dataset Generator for Anti-Money Laundering Research", arXiv 2603.01863: https://arxiv.org/pdf/2603.01863 . Checked 2026-10-18.
- [V18] Huda et al., "AMLNet: A Knowledge-Based Multi-Agent Framework to Generate and Detect Realistic Money Laundering Transactions", arXiv 2509.11595: https://arxiv.org/pdf/2509.11595 . Checked 2026-10-18.
- [V19] Jensen et al., "A synthetic data set to benchmark anti-money laundering methods", Scientific Data 10, 661 (2023): https://pmc.ncbi.nlm.nih.gov/articles/PMC10539331 . Checked 2026-10-18.
- [V20] Starnini et al., "Smurf-Based Anti-money Laundering in Time-Evolving Transaction Networks", ECML PKDD 2021, LNAI 12978: https://www.isi.it/wp-content/uploads/2024/01/smurf-based-anti-money-laundering-in-time-evolving-transaction-networks_Starnini2021_Chapter_Smurf-BasedAnti-moneyLaunderin.pdf . Checked 2026-10-18.
- [V21] Everingham et al., "The Pascal Visual Object Classes (VOC) Challenge", International Journal of Computer Vision 88 (2010), section 4.2, DOI 10.1007/s11263-009-0275-4: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/PascalVOC_IJCV2009.pdf ; https://www.microsoft.com/en-us/research/publication/the-pascal-visual-object-classes-voc-challenge/ . Checked 2026-10-18.
- [V22] Tatbul et al., "Precision and Recall for Time Series", NeurIPS 2018 (Advances in Neural Information Processing Systems 31): https://arxiv.org/pdf/1803.03639v3 ; https://proceedings.neurips.cc/paper/2018/hash/8f468c873a32bb0619eaeb2050ba45d1-Abstract.html . Checked 2026-10-18.
- [V23] Kim et al., "Towards a Rigorous Evaluation of Time-series Anomaly Detection", arXiv 2109.05257 (venue not confirmed here): https://arxiv.org/abs/2109.05257 . Checked 2026-10-18.
- [V24] scikit-learn, `sklearn.metrics.precision_score` (average, zero_division): https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html . Checked 2026-10-18.
- [V25] Opitz and Burst, "Macro F1 and Macro F1", arXiv 1911.03347: https://arxiv.org/abs/1911.03347 . Checked 2026-10-18.
- [V26] Field and Welsh, "Bootstrapping clustered data", Journal of the Royal Statistical Society Series B 69(3), 369 to 390 (2007), DOI 10.1111/j.1467-9868.2007.00593.x (abstract): https://ideas.repec.org/a/bla/jorssb/v69y2007i3p369-390.html . Checked 2026-10-18.
- [V27] Bouthillier et al., "Accounting for Variance in Machine Learning Benchmarks", arXiv 2103.03098 (abstract): https://arxiv.org/abs/2103.03098 . Checked 2026-10-18.
- [V28] Cawley and Talbot, "On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation", JMLR 11, 2079 to 2107 (2010) (abstract): https://www.jmlr.org/papers/v11/cawley10a.html . Checked 2026-10-18.
- [V29] FCA, Research Note "Synthetic Data and Anti-Money Laundering" (project report), 15 April 2026: https://www.fca.org.uk/publications/research-notes/research-note-synthetic-data-anti-money-laundering-project-report ; https://www.fca.org.uk/publication/research-notes/synthetic-data-anti-money-laundering-project-report.pdf . Checked 2026-10-18.
- [V30] Verified by running scripts in CPython 3.14 (uv-managed, `python -I`), kept in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-eval/scripts/` with outputs in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-eval/out/`: `wilson_tables.py` (half-widths, sample sizes, worked intervals), `crosscheck.py` (statsmodels 0.15.0 `proportion_confint`, scipy 1.18.1 t quantiles, Clopper-Pearson), `cluster_sim.py` and `cluster_sim2.py` (coverage simulations, fixed seeds), `examples.py` (worked examples, C4 strength terms), `matcher.py` and `test_matcher.py` (reference matcher and its tests). Run 2026-10-18.
- [V31] GitHub Docs, GitHub-hosted runners (standard Linux runner specifications): https://docs.github.com/en/actions/reference/runners/github-hosted-runners . Checked 2026-10-18.
- [V32] GitHub Docs, Events that trigger workflows, `schedule`: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows . Checked 2026-10-18.
- [V33] NumPy, Random sampling compatibility policy: https://numpy.org/doc/stable/reference/random/compatibility.html . Checked 2026-10-18.
- [V34] Python documentation, command line and environment, `PYTHONHASHSEED`: https://docs.python.org/3/using/cmdline.html . Checked 2026-10-18.
- [V35] Neo4j Cypher Manual 5, ORDER BY: https://neo4j.com/docs/cypher-manual/5/clauses/order-by/ . Checked 2026-10-18.
- [V36] PwC, "From source to surveillance: the hidden risk in AML monitoring system optimization", September 2010: https://www.pwc.com/us/en/anti-money-laundering/publications/assets/aml-monitoring-system-risks.pdf . Checked 2026-10-18.
- [V37] McKinsey and Company, "Transforming approaches to AML and financial crime" compendium, article "Network analytics and the fight against money laundering" (dated September 2019): https://www.mckinsey.com/~/media/mckinsey/business%20functions/risk/our%20insights/transforming%20approaches%20to%20aml%20and%20financial%20crime/transforming-approaches-to-aml-and-financial%20crime-vf.pdf . Checked 2026-10-18.
- [V38] Bank Policy Institute, "Getting to Effectiveness: Report on U.S. Financial Institution Resources Devoted to BSA/AML and Sanctions Compliance", 29 October 2018: https://bpi.com/?p=16846 . Checked 2026-10-18.
- [V39] FCA, "Financial crime analysis of firms' 2017 to 2020 REP-CRIM data", published 7 October 2021: https://www.fca.org.uk/data/financial-crime-analysis-firms-2017-2020/printable/print . Checked 2026-10-18.
- [V40] FATF, "Opportunities and Challenges of New Technologies for AML/CFT", July 2021: https://www.fatf-gafi.org/content/dam/fatf-gafi/guidance/Opportunities-Challenges-of-New-Technologies-for-AML-CFT.pdf . Checked 2026-10-18.
- [V41] HKMA, "AML/CFT Regtech: Case Studies and Insights Volume 2", September 2023: https://www.hkma.gov.hk/media/eng/doc/key-functions/banking-stability/aml-cft/AMLCFT_Regtech-Case_Studies_and_Insights_Volume_2.pdf . Checked 2026-10-18.
- [V42] Wolfsberg Group, "Statement on Effective Monitoring for Suspicious Activity, Part I: Moving Beyond Automated Transaction Monitoring" (2024): https://wolfsberg-group.org/resources/innovation/168 . Checked 2026-10-18.
- [V43] Wolfsberg Group, "Statement on Effective Monitoring for Suspicious Activity, Part II: Transitioning to Innovation" (2025; exact date UNVERIFIED, a news item dated 29 August 2025 reports its release): https://wolfsberg-group.org/resources/202 ; https://wolfsberg-group.org/resources/innovation ; https://www.plenitudeconsulting.com/news-insights/wolfsberg-group-releases-part-ii-on-suspicious-activity-monitoring . Checked 2026-10-18.
- [V44] Wolfsberg Group, About: https://wolfsberg-group.org/about . Checked 2026-10-18.
- [V45] Jullum, Løland, Huseby, Ånonsen and Lorentzen, "Detecting money laundering transactions with machine learning", Journal of Money Laundering Control 23(1), 173 to 186 (2020), DOI 10.1108/JMLC-07-2019-0055: https://publ.nr.no/1583921963/jullum_et_al_2020_money_laundering.pdf . Checked 2026-10-18.
- [V46] Naser Eddin et al., "Anti-Money Laundering Alert Optimization Using Machine Learning with Graphs", arXiv 2112.07508v3: https://arxiv.org/abs/2112.07508 ; https://arxiv.org/pdf/2112.07508v3 . Checked 2026-10-18.
- [V47] Gerlings and Constantiou, "Machine Learning in Transaction Monitoring: The Prospect of xAI", HICSS-56 (2023), arXiv 2210.07648: https://arxiv.org/pdf/2210.07648 . Checked 2026-10-18.
- [V48] Federal Reserve, SR 11-7 "Guidance on Model Risk Management", 4 April 2011 (cover letter page): https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm . Checked 2026-10-18.
- [V49] Federal Reserve, SR 21-8 "Interagency Statement on Model Risk Management for Bank Systems Supporting Bank Secrecy Act/Anti-Money Laundering Compliance", 9 April 2021: https://www.federalreserve.gov/supervisionreg/srletters/SR2108.htm ; https://www.federalreserve.gov/supervisionreg/srletters/SR2108.pdf . Checked 2026-10-18.
- [V50] PRA, SS1/23 "Model risk management principles for banks": https://prarulebook.co.uk/guidance/supervisory-statements/ss01-23--model-risk-management-principles-for-banks/4---model-risk-management-principles-for--banks/17-05-2024?p=1 ; https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss . Checked 2026-10-18.
- [V51] FCA Handbook, Financial Crime Guide FCG 3.2 (3.2.5, 3.2.5A, 3.2.5B): https://handbook.fca.org.uk/handbook/FCG/3/2.html . Checked 2026-10-18.
- [V52] Wolfsberg Group, "Principles for Using Artificial Intelligence and Machine Learning in Financial Crime Compliance" (2022): https://wolfsberg-group.org/resources/innovation/93 . Checked 2026-10-18.
- [V53] Miller, "Explanation in artificial intelligence: Insights from the social sciences", Artificial Intelligence 267, 1 to 38 (2019): https://arxiv.org/pdf/1706.07269v3 ; https://api.crossref.org/works/10.1016/j.artint.2018.07.007 . Checked 2026-10-18.
- [V54] Wachter, Mittelstadt and Russell, "Counterfactual Explanations Without Opening the Black Box: Automated Decisions and the GDPR", Harvard Journal of Law and Technology 31(2) (2018): https://arxiv.org/abs/1711.00399 ; https://jolt.law.harvard.edu/assets/articlePDFs/v31/Counterfactual-Explanations-without-Opening-the-Black-Box-Sandra-Wachter-et-al.pdf . Checked 2026-10-18.
- [V55] GitHub topic pages sorted by stars, rendered 2026-10-18: https://github.com/topics/anti-money-laundering?o=desc&s=stars ; https://github.com/topics/transaction-monitoring?o=desc&s=stars .
- [V56] opensource-finance/osprey, read-only clone (50 commits, first 2026-01-08, last 2026-10-17 at b58cb79; tags v0.1.0 and v0.1.1): `docs/STARTER_KIT.md` ("Measured Quality"), `CHANGELOG.md` (Unreleased): https://github.com/opensource-finance/osprey . Checked 2026-10-18.
- [V57] moov-io/watchman, read-only clone at 1d31b00 (2026-10-18): `README.md`, `docs/opensanctions-pairs.md`, `research/opensanctions-pairs/RESULTS.md`: https://github.com/moov-io/watchman . Checked 2026-10-18.
- [V58] Read-only clones searched for accuracy terms, 2026-10-18: jube-home/aml-fraud-transaction-monitoring at 0930cd8 https://github.com/jube-home/aml-fraud-transaction-monitoring ; checkmarble/marble at 9d8ec5f https://github.com/checkmarble/marble ; tazama-lf/docs at 7d85f21 https://github.com/tazama-lf/docs (also tazama-lf/rule-executer and tazama-lf/typology-processor) ; sofeikov/ezrules at 62ad9d7 https://github.com/sofeikov/ezrules ; blnkfinance/watch at 090ac19 https://github.com/blnkfinance/watch ; B-Deprez/GARG-AML at efbcb01 https://github.com/B-Deprez/GARG-AML ; RongLiu-AML/EvoAML at 58d4487 https://github.com/RongLiu-AML/EvoAML ; SantanderAI/gen-fraud-graph at 8665b9e https://github.com/SantanderAI/gen-fraud-graph ; curated lists https://github.com/ishandutta2007/Awesome-AML-Transaction-Monitoring and https://github.com/SKR-35/Awesome-Financial-Crime .
