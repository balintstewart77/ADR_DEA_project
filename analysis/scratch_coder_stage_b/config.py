from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'analysis/outputs_validation_scratch_stage_b_20260825'
RAW=ROOT/'preregistration_restricted/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv'
BASE=ROOT/'preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv'
HARD=ROOT/'preregistration_restricted/sampling/official_draw_20260724/hard_active.csv'
CROSS=ROOT/'preregistration_restricted/sampling/official_draw_20260724/formal_assignment_crosswalk.csv'
SEED, ATTEMPTS=20260714,2000
RAW_MOD='6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299'
LF_MOD='9827fc9f01b9e1f3e9b58fe8f41b59eb5a569c77aacb77d5140628ec04f5eeab'
OVERRIDE={'POST-009':BASE,'POST-011':HARD,'POST-019':CROSS}
SETS=('Research Domains','Analytical Purposes')
TAGS=('Demographic disparities / equity','COVID-19 & Pandemic')
