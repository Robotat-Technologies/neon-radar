"""The name an alert is shown under (PHASE-4.md 5.3; PHASE-3.md R9)."""

from neonradar_api.alert_names import display_name, shape_name
from neonradar_detect import catalog


def test_real_data_alerts_show_the_shape_name_only() -> None:
    typologies = catalog.load()
    circular = typologies["circular_flow"]
    assert shape_name(typologies, "circular_flow") == circular.shape_name
    assert display_name(typologies, "circular_flow", involves_real=True) == circular.shape_name
    assert display_name(typologies, "circular_flow", involves_real=False) == circular.name
    assert display_name(typologies, "unknown_slug", involves_real=True) == "a structural pattern"
    assert display_name(typologies, "unknown_slug", involves_real=False) == "unknown_slug"
