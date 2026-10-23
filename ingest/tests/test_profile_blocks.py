"""The overlay and detection blocks of the Phase 2 profiles (PHASE-3.md 7.11, M3.4)."""

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from neonradar_ingest.data.profiles import PROFILES_DIR, Profile, load_profile


def test_the_phase_2_profiles_load_with_their_blocks() -> None:
    demo, tiny, sample = (load_profile(name) for name in ("demo", "uk-tiny", "uk-sample"))
    assert demo.overlay is not None and not demo.overlay.enabled
    assert demo.detection is not None and demo.detection.window == "data"
    assert demo.detection.overrides == {"mass_registration_address": {"top_share": 0.0}}
    for profile, seed, illicit, share in ((tiny, 20261026, 2, 1.0), (sample, 20261027, 3, 0.05)):
        assert profile.overlay is not None and profile.overlay.enabled
        assert (profile.overlay.seed, profile.overlay.illicit, profile.overlay.lookalikes) == (
            seed, illicit, illicit
        )  # fmt: skip
        assert profile.overlay.background == {"share": share}
        assert profile.detection is not None and profile.detection.window == "overlay"


def uk_tiny() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((PROFILES_DIR / "uk-tiny.yaml").read_text("utf-8"))
    return data


@pytest.mark.parametrize(
    ("block", "change"),
    [
        ("overlay", {"unknown": 1}),
        ("detection", {"unknown": 1}),
        ("overlay", {"background": {"share": 1.5}}),
        ("overlay", {"background": {"share": -0.1}}),
        ("overlay", {"background": {"loan_share": 2}}),
        ("detection", {"window": "month"}),
    ],
)
def test_a_block_outside_its_rules_fails(block: str, change: dict[str, Any]) -> None:
    data = uk_tiny()
    Profile.model_validate(data)  # as committed
    data[block] |= change
    with pytest.raises(ValidationError):
        Profile.model_validate(data)
