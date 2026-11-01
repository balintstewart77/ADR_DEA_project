"""Organisations first seen in the 2026-10-21 register snapshot.

Sectors follow researcher_sector_rule in analysis/register_reference.yaml:
structural or legal status, never behaviour.
"""

import pytest

from dashboard.institution_normalisation import (
    _normalise_institution,
    institution_sector_for,
)


# Spelling variants of organisations already in the reference. Left as written
# in the register, these open a second entry for one body.
VARIANTS = [
    ("London School of Hygiene & Tropical Medicine",
     "London School of Hygiene and Tropical Medicine (LSHTM)"),
    ("Liverpool University", "University of Liverpool"),
    ("Birkbeck University of London", "Birkbeck, University of London"),
    ("Massachusetts Institute of Technology Department of Economics",
     "Massachusetts Institute of Technology (MIT)"),
    ("Institute of the Motore Industry (IMI)", "Institute of the Motor Industry"),
    ("Universite de Lille", "Université de Lille"),
    ("Barnardos", "Barnardo's"),
    ("Nest", "National Employment Savings Trust (Nest)"),
]

# Organisations genuinely new to the register, with the sector their legal
# status gives them.
NEW_ORGANISATIONS = [
    ("Barnardo's", "third-sector"),              # registered charity
    ("Centre of Expertise on Child Sexual Abuse", "third-sector"),  # hosted by Barnardo's
    ("National Employment Savings Trust (Nest)", "government"),     # public corporation, DWP
    ("Perinatal Institute", "third-sector"),     # company limited by guarantee, not-for-profit
    ("University of West London", "academic"),   # UK HEI
    ("Université de Lille", "academic"),         # French public university
]


@pytest.mark.parametrize("raw, canonical", VARIANTS)
def test_register_spellings_fold_into_one_organisation(raw, canonical):
    assert _normalise_institution(raw) == canonical


@pytest.mark.parametrize("canonical, sector", NEW_ORGANISATIONS)
def test_new_organisations_carry_their_structural_sector(canonical, sector):
    assert institution_sector_for(canonical) == sector


def test_every_queued_organisation_now_matches_the_reference():
    # The refresh marks an organisation unmatched when its sector is
    # "unclassified", so each of these would otherwise return to the queue.
    queued = [raw for raw, _ in VARIANTS] + [
        "Centre of Expertise on Child Sexual Abuse",
        "Perinatal Institute",
        "University of West London",
        "Université de Lille",
        "DfE NI",
    ]
    unmatched = [
        raw for raw in queued
        if institution_sector_for(_normalise_institution(raw)) == "unclassified"
    ]
    assert unmatched == []


def test_northern_ireland_dfe_is_the_economy_department_not_education():
    # In Northern Ireland DfE is the Department for the Economy. Both it and
    # the English Department for Education appear in this register, so the
    # short form must not collapse into the English department.
    assert _normalise_institution("DfE NI") == "Department for the Economy (Northern Ireland)"
    assert institution_sector_for("Department for the Economy (Northern Ireland)") == "government"
    assert _normalise_institution("DfE") == "Department for Education (DfE)"


def test_nest_and_nesta_stay_separate_organisations():
    nest = _normalise_institution("Nest")
    nesta = _normalise_institution("Nesta")
    assert nest != nesta
    assert institution_sector_for(nest) == "government"
    assert institution_sector_for(nesta) == "third-sector"
