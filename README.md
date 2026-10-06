# TECHi Traffic Analysis

## Purpose

This repository contains my analysis for the TECHi Data Analyst assessment, investigating whether TECHi traffic is actually increasing and whether the reported growth reflects real reader growth or an analytics measurement change.

## Files

- `techi_articles.csv` — Part 1 article-level dataset containing 120 rows.
- `analysis.xlsx` — Excel analysis with raw traffic, calculations, Part 1 findings, notes checks, and charts.
- `method.txt` — Reproducible methodology and assumptions.
- `memo.md` — Final assessment memo with conclusions and recommendations.

## Part 1: Article collection

The article dataset contains the 20 newest articles from each of six TECHi sections:

- AI
- Markets
- Crypto
- Breakthroughs
- Policy
- Guides

There are 120 rows total, with 20 rows per section.

Articles were not deduplicated across sections because the task asks for the 20 newest articles per category. The same article can therefore appear in more than one category.

The `date_shown` field was preserved verbatim.

## Part 2: Traffic analysis

The supplied traffic table was treated as invented assessment data and kept separate from the public article dataset.

Monthly total sessions were calculated by summing the six section values.

The supplied data does not include the previous year's traffic, so a true YoY calculation cannot be performed.

The February 2026 analytics implementation change was treated as a measurement discontinuity. A rough measurement factor was estimated using non-Guides traffic from January to February.

## Key findings

1. The “up 30% YoY” claim cannot be verified with the supplied data.
2. Reported sessions increased sharply in February 2026, consistent with the analytics implementation change.
3. The estimated underlying increase from January to August is approximately 8.3%, after adjusting August using the estimated measurement factor.
4. Crypto had a large one-off November 2025 spike.
5. Guides traffic declined by approximately 80.4% from January to August 2026.

## Decisions and tradeoffs

I kept duplicate article URLs across categories because deduplicating them would conflict with the requirement to collect the 20 newest articles per section.

The underlying traffic adjustment is explicitly presented as an estimate rather than a precise correction because the analytics implementation details are not available.

Guides are recommended to be retired as a standalone publishing priority rather than deleted entirely, allowing useful evergreen content to remain available.

## Checks

The article dataset was checked for:

- 120 total rows
- 20 rows per section
- Missing or blank values
- Author-profile URLs
- Obvious non-article URLs

The traffic calculations were checked by summing section-level sessions and comparing the totals with the supplied table.

## Limitations

The article dataset is a current snapshot and cannot establish historical monthly publishing volume.

The traffic data does not include the prior-year comparison required for a true YoY calculation.

The February analytics change makes raw pre/post session counts difficult to compare directly.

The Guides recommendation cannot be assigned an exact financial impact because revenue and advertising-value data were not supplied.

## Future improvement

The most useful additional data would be monthly unique users by section before and after the February analytics change, along with documentation of the implementation change. This would allow a cleaner separation of real audience growth from measurement changes.
