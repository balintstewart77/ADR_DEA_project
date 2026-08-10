# Source register provenance log

This operational log records source-publication events that affect provenance
without changing the frozen preregistration package. Entries here are not
protocol deviations unless they independently meet the deviation definition.

## 2026-08-10 — UKSA republication of the nominal 2026-06-01 register

On 10 August 2026, UKSA republished the nominal 1 June 2026 register at a new
URL with altered source bytes but no revised source date. The sole tabular
change affected project `2023/126`, an SRSA-only record excluded by the
prespecified DEA legal-basis filter. Re-cleaning both the original and
republished workbooks with identical current code produced byte-identical
1,308-record populations and deterministic-property tables. The classified
population, dashboard and validation sample were therefore unaffected.

- Original source URL: `https://uksa.statisticsauthority.gov.uk/wp-content/uploads/2026/06/01-06-2026-UKSA-Accredited-Research-Projects-Report-1.xlsx`
- Original retrieval date: 2026-06-11
- Republished source URL: `https://uksa.statisticsauthority.gov.uk/wp-content/uploads/2026/08/01-06-2026-UKSA-Accredited-Research-Projects-Report-1.xlsx`
- Republication observed: 2026-08-10
- Nominal source date for both: 2026-06-01
- Original raw XLSX SHA-256: `4f3851544846059c15b4df4dadc63b33079ca47a07e4eae41e98d5ddb3e452a3`
- Republished raw XLSX SHA-256: `33c8ba2abd2085a28b2e5ca5ba2913398c6edb96f59f31331e5c125c96661014`
- Original canonical LF CSV SHA-256: `abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d`
- Republished canonical LF CSV SHA-256: `918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd`
- Raw row counts: 1,450 original; 1,450 republished
- Affected record and field: project `2023/126`, `Researchers`
- Original field value: `Nikhil Datta, University of Warwick`
- Revised field value: `Nikhil Datta, University of London` followed by `Stephen Machin, The London School of Economics and Political Science` on a second line
- Unchanged legal basis: `Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021`
- Exclusion rule and stage: after required date/title checks and before duplicate handling, classification, sampling or dashboard use, retain only rows whose `Legal Basis` contains `Digital Economy Act`, case-insensitively
- Raw revision comparison: 0 projects added; 0 removed; 1 changed (`2023/126`, `Researchers`)
- Cleaned revision comparison: 0 projects added; 0 removed; 0 changed
- Original cleaned comparison SHA-256: `6b8d3c5f12e1bbe957fecbada4885c450f4c3ab41d1bd1ec2fa67170494abc5f`
- Revised cleaned comparison SHA-256: `6b8d3c5f12e1bbe957fecbada4885c450f4c3ab41d1bd1ec2fa67170494abc5f`
- Original deterministic-properties comparison SHA-256: `318bc4409a7d41c9c96b6d364e0e78b9c340165c1a0244f6243faf801565a43f`
- Revised deterministic-properties comparison SHA-256: `318bc4409a7d41c9c96b6d364e0e78b9c340165c1a0244f6243faf801565a43f`
- Outcome: `provenance-only; no analytical impact; not a deviation`

Methods-paper note: this is one observed instance of a statutory transparency
register being republished under an unchanged nominal date at a new URL. It
establishes existence, not frequency.
