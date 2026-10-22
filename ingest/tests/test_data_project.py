"""The Phase 3 and 4 keys of the project file, read through the model (PHASE-3.md 1.3, M3.0;
PHASE-4.md 1.3, M4.0)."""

from datetime import date
from typing import Any

import pytest
import yaml

from neonradar_ingest.data.project import DEFAULT_PROJECT_FILE, load_project


def _write(data_env: Any, data: dict[str, Any]) -> None:
    data_env.project.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_the_phase_3_keys_are_read(data_env: Any) -> None:
    _write(
        data_env,
        {
            "people": {"freeze_deciders": ["@ana", "@bo", "@cy"]},
            "access": {"real_overlay_profiles": ["uk-tiny"], "real_registry_alerts": True},
            "schedule": {
                "phase_3_start": date(2026, 10, 26),
                "assignment_4_due": date(2026, 11, 6),
                "detection_freeze": date(2026, 11, 9),
                "holdout_run": date(2026, 11, 10),
                "teach_back_detection": date(2026, 11, 12),
            },
        },
    )
    project = load_project()
    assert project.access.real_overlay_profiles == ["uk-tiny"]
    assert project.access.real_registry_alerts is True
    assert project.people.freeze_deciders == ["@ana", "@bo", "@cy"]
    assert project.schedule.detection_freeze == date(2026, 11, 9)
    assert project.schedule.teach_back_detection == date(2026, 11, 12)


def test_missing_phase_3_keys_fail_closed(data_env: Any) -> None:
    _write(data_env, {"other": 1})
    project = load_project()
    assert project.access.real_overlay_profiles == []
    assert project.access.real_registry_alerts is False  # G12's stricter option
    assert project.people.freeze_deciders == []
    assert project.schedule.detection_freeze is None


@pytest.mark.parametrize(
    ("access", "message"),
    [
        ({"real_registry_alerts": "yes"}, "real_registry_alerts"),
        ({"real_overlay_profiles": "uk-tiny"}, "real_overlay_profiles"),
    ],
)
def test_malformed_phase_3_keys_fail(data_env: Any, access: dict[str, Any], message: str) -> None:
    _write(data_env, {"access": access})
    with pytest.raises(ValueError, match=message):
        load_project()


def test_the_committed_project_file_has_the_phase_3_keys() -> None:
    project = load_project(DEFAULT_PROJECT_FILE)
    assert isinstance(project.access.real_registry_alerts, bool)
    assert all(isinstance(name, str) for name in project.access.real_overlay_profiles)
    assert len(project.people.freeze_deciders) == 3
    assert isinstance(project.schedule.detection_freeze, date)


def test_the_phase_4_keys_are_read(data_env: Any) -> None:
    dates = {
        "phase_4_start": date(2026, 11, 2),
        "contracts_1_3_0": date(2026, 11, 3),
        "assignment_5_due": date(2026, 11, 10),
        "heldout_run": date(2026, 11, 11),
        "teach_back_copilot": date(2026, 11, 12),
    }
    _write(data_env, {"people": {"heldout_owner": "@ana"}, "schedule": dates})
    project = load_project()
    assert project.people.heldout_owner == "@ana"
    assert {key: getattr(project.schedule, key) for key in dates} == dates
    _write(data_env, {"other": 1})
    assert load_project().people.heldout_owner is None
    assert load_project().schedule.heldout_run is None


def test_the_committed_project_file_has_the_phase_4_keys() -> None:
    project = load_project(DEFAULT_PROJECT_FILE)
    assert project.people.heldout_owner  # "@TODO" until the operator names one (OD-25)
    assert isinstance(project.schedule.phase_4_start, date)
    assert isinstance(project.schedule.heldout_run, date)
