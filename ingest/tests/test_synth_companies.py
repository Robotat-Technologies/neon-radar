import re

import pytest

from neonradar_ingest.synth import words
from neonradar_ingest.synth.companies import CompanyNames, name_key
from neonradar_ingest.synth.names import is_denied

# Stems of the wording lint (PHASE-1.md 7.1) plus words that suggest a verdict on a company.
LINT = re.compile(
    r"launder|criminal|crime|guilty|fraud|suspic|suspect|illicit|illegal|dirty|corrupt|brib"
    r"|terroris|mule|shell|front|conceal|evad|evasion|risk|accomplice|wrongdo|offshore",
    re.IGNORECASE,
)


def test_name_key_ignores_case_punctuation_and_legal_forms() -> None:
    names = ["Ochre Tarn Freight Ltd", "OCHRE TARN FREIGHT LIMITED", "Ochre-Tarn Freight, Ltd.",
             "ochre tarn freight"]  # fmt: skip
    assert {name_key(n) for n in names} == {"ochre tarn freight"}
    arabic = "الصفصاف والكهرمان للتجارة العامة"
    assert name_key(f"{arabic} ذ.م.م") == name_key(arabic)
    assert name_key("ООО Ромашка") == "ромашка"


@pytest.mark.parametrize(
    ("jurisdiction", "forms"),
    [("gb", ("Ltd", "LLP")), ("vg", ("Limited",)), ("cy", ("Ltd",)), ("ae", ("ذ.م.م",))],
)
def test_names_carry_the_legal_form_of_their_jurisdiction(
    jurisdiction: str, forms: tuple[str, ...]
) -> None:
    names = CompanyNames(seed=3)
    drawn = [names.draw(slot, jurisdiction)[0] for slot in range(40)]
    assert all(name.endswith(forms) for name in drawn)
    assert len({name_key(name) for name in drawn}) == 40
    assert not any(is_denied(name) for name in drawn)


def test_a_taken_name_is_never_drawn_again() -> None:
    first, attempt = CompanyNames(seed=3).draw(0, "gb")
    other, later = CompanyNames(seed=3, taken={name_key(first)}).draw(0, "gb")
    assert name_key(other) != name_key(first)
    assert later > attempt


def test_word_lists_are_neutral_and_unique() -> None:
    lists = [words.COMPANY_FIRST, words.COMPANY_SECOND, words.COMPANY_ACTIVITY,
             words.ARABIC_NOUNS, words.STREET_TYPES]  # fmt: skip
    for items in lists:
        assert len(set(items)) == len(items)
        assert not [item for item in items if LINT.search(item)]
    assert not LINT.search(words.AGENT_ACTIVITY + " " + words.LENDER_ACTIVITY)
