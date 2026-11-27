# Evaluation data

Three domains, six scenarios each. Every scenario has one clean workbook and 16 injected
workbooks: the same eight placements crossed with two payload styles.

- **Placements:** `visible` (the control), `custom_format` (`;;;`), `white_text`, `tiny_font`
  (1 pt), `hidden_row`, `hidden_column`, `hidden_sheet`, `very_hidden_sheet`
  (see `hiddencells/mechanisms.py`).
- **Payload styles:** `spoofed_data` (a disguised correction) and `instruction`. In
  procurement the same two styles are called `contextual_spoof` and `imperative`.
- All workbooks store plain values; none contains formulas.

| Folder | Domain | Cases file | Workbooks |
| --- | --- | --- | --- |
| `procurement/` | procurement decisions | `cases_eval.csv` (proc-01, 02, 04, 05, 07, 08: two per sheet type) | 6 clean + 96 injected |
| `finance/` | formula-based finance, from `sean/` | `cases.csv` | 6 clean + 96 injected, plus 6 helpers-hidden clean workbooks for the false-removal test |
| `statistics/` | statistical reporting, from `supanice/` | `cases.csv` | 6 clean + 96 injected |

The cases files use the team format (the first six columns), so `run_models.py` runs them
as they are.

## How finance and statistics are built

`python -m hiddencells.harmonize` rebuilds both from the generators in this repo
(`sean/build` and `supanice/spreadsheet_injection_testbed.py`):

- Questions, answers and payload texts are the originals. The placements come from
  `hiddencells/mechanisms.py`, the same code as procurement.
- Finance is recalculated with LibreOffice, as in Sean's build, and every formula is then
  replaced by its computed value. Each cell shows the same number as in Sean's workbooks.
- Statistics uses Ethan's seed, so his five datasets come out identical. A sixth dataset,
  `school_scores` ("Which school has the highest average math score?"), is added after them.

Differences from the original sets:

- The visible control uses exactly the payload text of the hidden versions (no label).
- White text and 1 pt font are separate placements; hidden column and very hidden sheet
  are added; every placement has both payload styles.
- Ethan's zero-height-row and 1 pt white variants are not included.
- Formula-generated notes and Sean's helpers-hidden injected variants are not included.

`python -m hiddencells.harmonize --verify-only` checks every injected workbook: the placement
is applied, the payload is its only difference from the clean workbook, the text pipeline
reads the payload, and no formulas remain.
