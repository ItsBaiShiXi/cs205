# Hidden in Plain Cells: Approach

Draft for the team, revised 2026-11-27.

**In one sentence:** We systematically measure how content that a user cannot see in a spreadsheet changes an AI assistant's answer, across hiding methods, payload styles, reading pipelines and models; as a mitigation, we make the model read only what the user can see.

## 1. Threat model

- **User:** has checked the workbook in Excel and accepts what they can see.
- **Attacker:** adds content the user cannot see, for example through a supplier's quote sheet, imported data or a shared template.
- **Attack success:** the assistant gives the answer the attacker wants.
- **Correct answer:** the answer based on what the user can see, i.e. the clean workbook's answer.
- **Out of scope:** visible notes (our control), edits to the visible numbers, and formulas (future work).

## 2. Attack (core)

We ask whether hidden content changes the assistant's answer, and which factors decide how often.

- **Scenarios:** three domains (procurement, finance, statistical reporting), six scenarios each. Each scenario asks one question with a single correct answer, so success is unambiguous.
- **Hiding methods:** seven, all of which leave the content in the file while Excel does not show it:
  - number format: `;;;`;
  - visual: white text, 1 pt font;
  - structural: hidden row, hidden column, hidden sheet, very hidden sheet.
- **Visible control:** the same text in an ordinary cell. Comparing it with the hidden versions shows whether hiding changes how the model reacts, or only what the user can see.
- **Payload styles:**
  - **Disguised correction (core):** reads like part of the data, such as "the first four quotes exclude a 45% import tariff". It gives no instruction, so it is hard to tell from a genuine note.
  - **Explicit instruction:** the classic injection, such as "answer Everest Industrial".
- **Reading pipelines:** what the model receives depends on how the file is read, so we test three:
  - the provider reads the uploaded file (main setting for the commercial models);
  - a developer converts it to text with pandas (Qwen, and a comparison for the others);
  - web chat interfaces, as case studies in real products.
- **Models:** a local open model (Qwen 3.5 9B) and three commercial models (GPT-5.6 Luna, DeepSeek V4.1 Flash, Gemini 3.6 Flash).

## 3. Defense (solution)

- **Idea:** make what the model reads match what the user sees. The defense judges visibility, never truth.
- **Our sanitizer:** Excel renders the workbook and Tesseract OCR checks which text a person can read; numbers hidden by structure, number format, colour or size are found by rule. Everything the user cannot see is removed and listed for the user. If removing something changes the answer, the user is warned and decides.
- **Compared against:** a hardened system prompt and tagging hidden cells. The rule-based sanitizer from our proposal appears only in the generalization test.
- **Limitations:** hidden numbers are found by rules, so a new way of hiding a number could get through; rendering needs Excel.

## 4. How this differs from past work

- **Attacks (main contribution):** past work studied hidden text in web pages, emails and PDFs [2], or reported single product vulnerabilities. We measure spreadsheets systematically: seven hiding methods, two payload styles, three domains, three reading pipelines and four models. The main threat is the disguised correction, which all four models follow, rather than the explicit instruction, which the commercial models mostly ignore.
- **Defenses:** detection [3] and training [4] look for instructions, and prompting [1] relies on the model, so falsified data is hard for all three. Ours decides by visibility, so it never has to tell a real correction from a fake one. Its comparison step follows MELON [5] and AgentSentry [6].

## References

1. Hines et al. Defending Against Indirect Prompt Injection Attacks With Spotlighting. 2024.
2. Greshake et al. Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. AISec 2023. arXiv:2302.12173.
3. Nasr et al. The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against LLM Jailbreaks and Prompt Injections. USENIX Security 2026. arXiv:2510.09023.
4. Chen et al. SecAlign: Defending Against Prompt Injection with Preference Optimization. arXiv:2410.05451.
5. Zhu et al. MELON: Provable Defense Against Indirect Prompt Injection Attacks in AI Agents. ICML 2025. arXiv:2502.05174.
6. AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification. arXiv:2602.22724.

## Still to agree as a group

- Disguised corrections as the core attack.
- Visible notes as the control.
- Attack as the main focus, with the defense as the solution.
