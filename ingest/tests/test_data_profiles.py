"""Profiles and the project file (PHASE-2.md M2.2 deliverables 1 to 3)."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from neonradar_ingest.data import layout, profiles
from neonradar_ingest.data.profiles import ProfileError, load_profile, profile_names
from neonradar_ingest.data.project import DEFAULT_PROJECT_FILE, REPO_ROOT, load_project


def test_the_committed_profiles_load_and_say_what_they_are(data_env: Any) -> None:
    assert profile_names() == ["demo", "uk-sample", "uk-tiny"]
    demo, tiny, sample = (load_profile(name) for name in ("demo", "uk-tiny", "uk-sample"))
    assert (demo.real_data, tiny.real_data, sample.real_data) == (False, True, True)
    assert demo.options("nr_synthetic").fixtures == ["data/fixtures/demo-mini"]
    assert tiny.options("gb_companies_house").companies.max_companies == 400
    assert sample.sources["icij_offshore_leaks"].options["mode"] == "district-linked"
    assert sample.resolution.config == "resolve/config/er.yaml"


def test_enabled_sources_follow_the_profile_and_the_project_file(data_env: Any) -> None:
    tiny = load_profile("uk-tiny")
    project = load_project()  # NR_PROJECT_FILE: the OD-22 lists, no PEP source
    enabled = ["gb_companies_house", "gleif_lei", "gb_fcdo_sanctions", "us_ofac_sdn", "eu_fsf"]
    assert tiny.enabled_sources(project) == enabled
    assert tiny.refused_sources(project) == {
        "un_sc_sanctions": "un_sc_sanctions is not in access.sanctions_lists",
        "gb_parliament_members": "gb_parliament_members is not in access.pep_sources",
    }
    data_env.write_project(sanctions_lists=["us_ofac_sdn"], pep_sources=["gb_parliament_members"])
    project = load_project()
    assert tiny.enabled_sources(project) == [
        "gb_companies_house", "gleif_lei", "us_ofac_sdn", "gb_parliament_members",
    ]  # fmt: skip
    sample = load_profile("uk-sample")
    assert "opensanctions_default" not in sample.enabled_sources(project)  # disabled in the file
    assert project.access_refusal("gb_companies_house") is None
    assert project.access_refusal("gb_companies_house", "officers") == (
        "access.companies_house_key",
        "the officers API needs access.companies_house_key: available",
    )


def test_the_project_file_comes_from_nr_project_file_and_is_fingerprinted(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = load_project()
    assert project.path == data_env.project
    fields = project.summary_fields()
    assert fields["project_file"] == "(outside the repository) project.yaml"
    assert len(fields["project_sha256"]) == 64
    monkeypatch.delenv("NR_PROJECT_FILE")
    assert load_project().summary_fields()["project_file"] == "docs/build/project.yaml"
    assert DEFAULT_PROJECT_FILE == REPO_ROOT / "docs" / "build" / "project.yaml"


def test_a_malformed_project_file_fails(data_env: Any) -> None:
    data_env.project.write_text("access:\n  data_protection_filed: 'yes'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="data_protection_filed"):
        load_project()
    data_env.project.write_text("access:\n  sanctions_lists: [un_list]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sanctions_lists"):
        load_project()
    data_env.project.write_text("- a list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a YAML mapping"):
        load_project()
    data_env.project.write_text("other: 1\n", encoding="utf-8")  # missing keys fail closed
    access = load_project().access
    assert (access.real_data_profiles, access.data_protection_filed, access.sanctions_lists) == (
        [], False, [],
    )  # fmt: skip


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"sources": {"nr_synthetic_x": {"enabled": True}}}, "unknown dataset 'nr_synthetic_x'"),
        ({"extra": 1}, "Extra inputs are not permitted"),
        ({"real_data": "no"}, "real_data"),
        ({"profile": "Other"}, "lower-case words"),
        ({"profile": "other"}, "says profile: other"),
        (
            {"sources": {"nr_synthetic": {"enabled": True, "fixtures": ["data/cache/x"]}}},
            "not a folder under data/fixtures/",
        ),
        (
            {"sources": {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/../x"]}}},
            "not a folder under data/fixtures/",
        ),
        ({"sources": {"gleif_lei": {"scope": "slice"}}}, "enabled"),
        (
            {"sources": {"gleif_lei": {"enabled": True}}},
            "real_data is false, so the profile may enable only nr_synthetic; it enables gleif_lei",
        ),
        ({"profile": "all-profiles"}, "reserved for the data manager"),
    ],
)
def test_profile_validation_errors(data_env: Any, change: dict[str, Any], message: str) -> None:
    data = {
        "profile": "broken",
        "description": "x",
        "real_data": False,
        "sources": {"nr_synthetic": {"enabled": True, "fixtures": ["data/fixtures/demo-mini"]}},
        "resolution": {"enabled": False, "config": "resolve/config/er.yaml"},
    }
    path = data_env.profiles / "broken.yaml"
    path.write_text(yaml.safe_dump(data | change), encoding="utf-8")
    with pytest.raises(ProfileError, match=message):
        load_profile("broken")


def test_unknown_or_unsafe_profile_names_fail(data_env: Any) -> None:
    with pytest.raises(ProfileError, match="no profile 'nope'; profiles: demo, uk-sample"):
        load_profile("nope")
    with pytest.raises(ProfileError, match="not a profile name"):
        load_profile("../demo")


def test_a_registered_model_checks_the_source_block(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Gleif(BaseModel):
        model_config = ConfigDict(extra="forbid")
        enabled: bool
        scope: str

    monkeypatch.setitem(profiles._SOURCE_MODELS, "gleif_lei", Gleif)
    assert load_profile("uk-tiny").options("gleif_lei") == Gleif(enabled=True, scope="slice")
    data_env.write_profile(
        "bad-block", real_data=True, sources={"gleif_lei": {"enabled": True, "scop": "slice"}}
    )
    with pytest.raises(ProfileError, match="scop"):
        load_profile("bad-block")
    with pytest.raises(ValueError, match="not a dataset"):
        profiles.register_source_model("gleif", Gleif)


def test_record_dirs(data_env: Any) -> None:
    project = load_project()
    assert load_profile("demo").record_dirs(project) == [REPO_ROOT / "data/fixtures/demo-mini"]
    tiny = load_profile("uk-tiny")
    dirs = tiny.record_dirs(project)
    assert dirs[0] == layout.records_dir(tiny, "gb_companies_house")
    assert all(
        Path(d).is_relative_to(data_env.cache / "real" / "records" / "uk-tiny") for d in dirs
    )
    assert len(dirs) == len(tiny.enabled_sources(project)) == 5


def test_a_synthetic_profile_may_list_a_real_dataset_only_disabled(data_env: Any) -> None:
    data_env.write_profile(
        "quiet", real_data=False, sources={"gleif_lei": {"enabled": False, "scope": "slice"}}
    )
    assert load_profile("quiet").enabled_sources(load_project()) == []
