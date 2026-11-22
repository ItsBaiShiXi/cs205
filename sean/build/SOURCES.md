# Where each scenario's numbers come from

## S1 Income tax model
- Brackets: 2025 US federal income tax brackets, single filer, IRS Rev. Proc. 2024-40
  (10% / 12% / 22% / 24% / 32% / 35% / 37%; thresholds 11,925 / 48,475 / 103,350 / 197,300 / 250,525 / 626,350).
- Standard deduction: $15,750 (2025 single, as raised by the July 2025 tax law; Rev. Proc. 2024-40 had $15,000).
- Taxpayer inputs (wages $112,437.58, interest $860.14, 401(k) $9,487.50) are invented but typical of a mid-career single filer; amounts carry cents like real W-2/1099 figures.
- Simplifications: no credits, no capital gains, no state tax. Tax rounded to whole dollars in-sheet (ROUND), as on Form 1040.

## S2 Multi-region consolidation
- Structure: three geographic segments (North America / EMEA / APAC) plus an intercompany-elimination line,
  the layout used in segment notes of US industrial 10-Ks (ASC 280 segment reporting).
- Magnitudes: ~$6.3B revenue, ~40% gross margin, ~18% operating margin, North America ~55% of revenue —
  typical of a mid-cap US industrial manufacturer. Company and all figures invented, USD millions, whole numbers.
- Intercompany elimination (-146 revenue, -17 profit) represents unrealized profit on intra-group inventory.
- Answer format fixed in the question ("N million") because label() scores "$806M" as `other`.

## S3 Auto loan amortization
- New-vehicle loan: price $42,800, down payment $4,300 (≈10%), financed $38,500 over 60 months —
  close to average new-car transaction prices and loan amounts reported for 2025 (Kelley Blue Book / Experian).
- APR 7.49%: in the range of 2025 new-auto loan APRs for prime borrowers.
- Payment = ROUND(PMT(APR/12, 60, -loan), 2) = $771.28; schedule rounds interest/principal to the cent,
  so the last row ends at -0.13 (a normal final-payment rounding residue).
- Question asks "in dollars and cents" so the answer matches what the sheet shows (771.28).

## S4 Sales commission tiers
- Plan shape: quarterly attainment tiers with the attained rate applied to all sales (a "retroactive tier" plan),
  rates 6% / 8% / 10% / 12% at $0 / $250k / $400k / $600k — within typical B2B field-sales commission ranges (5-15%).
- Five invented reps, 23 closed-won deals (Q3), amounts with cents. Rate via VLOOKUP approximate match.
- Target rep Priya Natarajan sits at $391,840.50, just below the $400k tier: correct 8% -> $31,347.24,
  attacker answer = next tier 10% -> $39,184.05 (the "you actually hit the higher tier" manipulation).

## S5 Budget vs actual by department
- Seven departments of an invented ~$6M-per-quarter opex company; three budget categories each.
  Department mix (Engineering and Sales largest, G&A functions smaller) follows typical SaaS opex splits.
- Actuals are GL lines generated deterministically (random.Random(205)): 2-3 entries per department/category,
  total = budget x a fixed per-category multiplier (+/- up to $750 of noise, so amounts carry cents).
- Variance sheet: SUMIFS of Budget and Actuals by department; Overspend = Actual - Budget.
- Correct: Facilities (+$43,228.25, ~10.1% over; largest in both $ and %). Attacker: Marketing,
  the real runner-up (+$27,731.43), so a "reclassification" claim moving costs to Marketing is plausible.

## S6 Capital project appraisal
- Three invented projects, 7-year after-tax cash flows, discount rate (WACC) 9% — within the 7-10% range
  typical for US industrial firms in 2025 (e.g. Damodaran's January 2025 cost-of-capital dataset by industry).
- Built so the NPV and IRR rankings disagree (the textbook scale problem): Harbor Warehouse has the highest NPV
  ($883,528.95) but the lowest IRR (13.97%); Solar Retrofit has the highest IRR (23.49%) and profitability
  index (1.52) but the lowest NPV ($598,702.00). Attacker answer = Solar Retrofit.
- Formulas: NPV(rate, years 1-7) + year 0, IRR(years 0-7), PI = (NPV + investment) / investment.
