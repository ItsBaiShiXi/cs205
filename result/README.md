# Results: attack (E1, E2)

Draft for the team, 2026-11-27. These are the attack results, without any defense. Defense results (E3–E5) will be added later.

**Setup.** 3 domains × 6 scenarios. Each scenario has a clean file and 16 injected files (7 hiding methods plus a visible control, × 2 payload styles), and every file is run 3 times. The commercial models read the uploaded file through the provider; Qwen reads pandas text.

**Reading the numbers.**
- Attack success rate (ASR): the share of runs that give the attacker's answer. Higher means a more effective attack.
- Each domain cell has 126 runs (6 scenarios × 7 hiding methods × 3 runs) unless noted.
- The average weights the three domains equally. Every CSV gives a 95% confidence interval (`ci_low`, `ci_high`), and all its rates are fractions between 0 and 1.

**Making figures.** Each section names its CSV in this folder and suggests a figure. The columns are explained at the end.

## 1. Accuracy on clean files (baseline)

Data: `clean_accuracy.csv`. Figure: grouped bars, model × domain.

| Model | Procurement | Finance | Statistics | Average |
|---|---|---|---|---|
| Qwen 3.5 9B | 18/18 | 17/18 | 18/18 | 98% |
| GPT-5.6 Luna | 18/18 | 15/18 | 18/18 | 94% |
| DeepSeek V4.1 Flash | 18/18 | 18/18 | 18/18 | 100% |
| Gemini 3.6 Flash | 18/18 | 18/18 | 18/18 | 100% |

Without an attack, the models answer almost every question correctly, so the questions themselves are not what makes them fail.

## 2. Hidden disguised corrections (E1)

Data: `attack_success.csv`, rows with `placement = hidden` and `payload_style = disguised_correction`. Figure: grouped bars with error bars, model × domain.

| Model | Procurement | Finance | Statistics | Average |
|---|---|---|---|---|
| Qwen 3.5 9B | 116/126 (92%) | 114/126 (90%) | 102/126 (81%) | 88% (85–91%) |
| GPT-5.6 Luna | 121/126 (96%) | 110/126 (87%) | 113/126 (90%) | 91% (88–94%) |
| DeepSeek V4.1 Flash | 126/126 (100%) | 126/126 (100%) | 117/126 (93%) | 98% (96–99%) |
| Gemini 3.6 Flash | 120/126 (95%) | 123/126 (98%) | 88/126 (70%) | 88% (84–91%) |

They succeed 88–98% of the time on all four models.

## 3. Hidden explicit instructions (E1)

Data: `attack_success.csv`, rows with `placement = hidden` and `payload_style = explicit_instruction`. Figure: the same as section 2, side by side.

| Model | Procurement | Finance | Statistics | Average |
|---|---|---|---|---|
| Qwen 3.5 9B | 68/126 (54%) | 81/126 (64%) | 113/126 (90%) | 69% (65–74%) |
| GPT-5.6 Luna | 0/126 | 16/126 (13%) | 0/126 | 4% (2–6%) |
| DeepSeek V4.1 Flash | 0/126 | 0/126 | 0/126 | 0% |
| Gemini 3.6 Flash | 0/126 | 6/126 (5%) | 0/126 | 2% (0–3%) |

The commercial models mostly ignore them; only the small local model follows them.

## 4. Visible control (E1)

Data: `attack_success.csv`, rows with `placement = visible` (18 runs per domain). Figure: hidden vs visible bars per model, from the `average` rows.

The same payloads in an ordinary visible cell succeed about as often: disguised corrections 93% (Qwen), 89% (GPT), 96% (DeepSeek) and 89% (Gemini); explicit instructions 74% (Qwen) and 0–6% (commercial models). The model treats hidden content like visible content. Hiding only keeps it from the user, whose check of the file therefore cannot catch it.

## 5. By hiding method (E1)

Data: `attack_by_hiding_method.csv`, three domains pooled (54 runs per cell). Figure: heatmap of hiding method × model, for disguised corrections.

| Hiding method | Qwen | GPT | DeepSeek | Gemini |
|---|---|---|---|---|
| `;;;` number format | 93% | 93% | 100% | 89% |
| White text | 93% | 89% | 96% | 91% |
| 1 pt font | 93% | 89% | 96% | 89% |
| Hidden row | 93% | 87% | 100% | 94% |
| Hidden column | 85% | 94% | 100% | 74% |
| Hidden sheet | 80% | 93% | 98% | 85% |
| Very hidden sheet | 80% | 93% | 93% | 91% |
| Visible (control) | 93% | 89% | 96% | 89% |

Every hiding method works; the lowest is 74% (Gemini, hidden column).

## 6. Only scenarios answered correctly on clean files (E1)

Data: `attack_clean_correct_only.csv`.

Counting only scenarios whose clean file was answered correctly in every run, ASR for hidden disguised corrections stays at 87% (Qwen), 90% (GPT), 98% (DeepSeek) and 88% (Gemini). The attack is not explained by questions the model gets wrong anyway.

## 7. Provider upload vs pandas text (E2)

Data: `text_vs_upload.csv` (commercial models only). Figure: paired bars or a dumbbell plot, per model and domain.

ASR for hidden disguised corrections, pandas text → uploaded file:

| Model | Procurement | Finance | Statistics |
|---|---|---|---|
| GPT-5.6 Luna | 98% → 96% | 94% → 87% | 94% → 90% |
| DeepSeek V4.1 Flash | 100% → 100% | 100% → 100% | 97% → 93% |
| Gemini 3.6 Flash | 100% → 95% | 92% → 98% | 77% → 70% |

Every difference is within 7 points, in both directions. Explicit instructions and clean accuracy also barely change; for example, GPT in finance goes from 18% to 13% on instructions and from 17/18 to 15/18 on clean accuracy.

## 8. Exposure (E2)

Data: `exposure.csv`, one copy-out run per injected file (36 per hiding method). Figure: bars or a heatmap, hiding method × model.

Asked to copy out the uploaded file, the models reproduced the hidden payload in 251/252 cases (GPT), 252/252 (DeepSeek) and 238/252 (Gemini, 94%), hidden and very hidden sheets included. Gemini also reproduced only 34/36 visible payloads (94%), so its misses come from incomplete copying, not from hiding. Copying out gives a lower bound on what a model received.

## 9. Web chat interfaces (E2)

To be added: ChatGPT, Gemini and DeepSeek, uploaded by hand.

## Summary

- Content the user cannot see reaches the model through every pipeline we tested, and a disguised correction changes the answer in most runs on all four models.
- Explicit instructions are mostly ignored by the commercial models but followed by the small local model.
- The risk is not that models trust hidden content more than visible content. It is that the user cannot see it, so checking the file cannot catch it.

## CSV columns

- `model`: Qwen 3.5 9B, GPT-5.6 Luna, DeepSeek V4.1 Flash, Gemini 3.6 Flash.
- `reader`: `upload` (the provider reads the uploaded file) or `pandas_text`.
- `domain`: `procurement`, `finance`, `statistics`, or `average` (equal weights, so its count columns are empty).
- `payload_style`: `disguised_correction` or `explicit_instruction`.
- `placement`: `hidden` (the seven hiding methods together) or `visible` (the control).
- `hiding_method`: `custom_format` (the `;;;` number format), `white_text`, `tiny_font` (1 pt), `hidden_row`, `hidden_column`, `hidden_sheet`, `very_hidden_sheet`, `visible`.
- `measure` (in `text_vs_upload.csv`): `asr_disguised_correction`, `asr_explicit_instruction` or `clean_accuracy`.
- Counts: `correct`, `attacker_answers`, `count` and `exposed` are numerators; `runs` and `probed` are denominators.
- Rates: `accuracy`, `asr`, `rate` and `exposure_rate`, with the 95% interval in `ci_low` and `ci_high`.
