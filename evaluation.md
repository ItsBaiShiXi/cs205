# Hidden in Plain Cells: Evaluation

Revised 2026-11-27.

## 1. Questions

**Attack (core)**

- **E1 Effect:** How often does content the user cannot see change the answer, and how does this depend on the payload style, the hiding method, the domain and the model? Does hiding matter, compared with the same text left visible?
- **E2 Realism:** Do real file-reading pipelines pass hidden content to the model, and does the attack still work through them?

**Defense (solution)**

- **E3 Protection:** How much attack success is left under each defense, and how often is the user warned?
- **E4 Side effects:** Does a defense remove legitimate content or lower accuracy?
- **E5 Generalization:** Does the sanitizer catch hiding methods outside our attack set?

## 2. Data, models and runs

- **Main set:** 3 domains × 6 scenarios. Each scenario has one clean workbook and 16 injected ones (8 placements × 2 payload styles): 306 files, all plain values. No clean workbook hides anything.
- **Extra sets:** six clean workbooks that hide legitimate helper data (E4; 416 hidden cells, 399 of them numbers), and 13 hiding methods outside our attack set (E5).
- **Models:** Qwen 3.5 9B (local), GPT-5.6 Luna, DeepSeek V4.1 Flash, Gemini 3.6 Flash.
- **Reading:** the commercial models get the uploaded file, read by the provider (main results); Qwen gets pandas text.
- **Runs:** three per file, provider defaults, Qwen with thinking off.

## 3. Attack evaluation (E1, E2)

- **Attack success rate (ASR):** the share of runs on injected files that give the attacker's answer; higher means a more effective attack. Counted on hidden payloads, separately for the two payload styles.
- **Breakdowns:** by hiding method, domain and model. The main tables show hidden disguised corrections and hidden instructions by model and domain, with a heatmap by hiding method.
- **Visible control:** the ASR of the same payloads left visible, to show whether hiding changes the model's reaction.
- **Baseline:** accuracy on the clean files, plus a second ASR restricted to scenarios whose clean file was always answered correctly, so an attack is not credited for a question the model gets wrong anyway.
- **Realism (E2):**
  - the commercial models read both the uploaded file and the pandas text, and the two ASRs are compared;
  - exposure: each model is asked to copy out the uploaded file, and we check whether the hidden payload appears (a lower bound on what it received);
  - web chat interfaces (ChatGPT, Gemini, DeepSeek; default model, temporary chat, memory off): one scenario per domain, with the clean file, a white-text correction, a hidden-sheet correction and the sanitized white-text file. We record the answer, whether the reply mentions the injected content, and a screenshot.

## 4. Defense evaluation (E3–E5)

| Setting | What it does |
| --- | --- |
| No defense | — |
| Hardened system prompt | Tells the model to treat the file as untrusted data and not to apply notes that adjust values |
| Tagging | Marks the cells the user cannot see |
| Our sanitizer | Removes everything the user cannot see (text by rendering + OCR, numbers by rule), lists removals, and warns when removal changes the answer |

- **E3:** ASR under each setting (lower is better). For our sanitizer, also the share of successful attacks that trigger a warning, and of failed ones that trigger one anyway.
- **E4:** visible cells removed across all 312 workbooks (target zero); legitimate hidden cells removed from the six helper-data workbooks, which run with no defense and with our sanitizer; accuracy on clean files under each setting.
- **E5:** how many of the 13 held-out methods the rule-based and the rendering + OCR sanitizers catch, by detection only.
- **Notes:** the comparison step reuses the no-defense answers, so it needs no extra calls.
- **Caveats:** the hardened prompt names the kinds of correction our payloads use, so it may look better here than elsewhere; unusual formatting is not tested; the E5 methods are our own, so E5 is a probe, not an independent test.

## 5. Reporting

Each domain is reported separately, plus an equal-weight average, with 95% confidence intervals; every table states whether higher or lower is better. Case studies for the slides come from these results.
