from app.services.ingest.prepare_dim import _default_unit, _default_policy


def test_default_unit_and_policy_voltage():
    assert _default_unit("voltage_a")[0] == "V"
    vt, vmin, vmax = _default_policy("voltage_b")
    assert vt == "number" and vmin == 0.0 and vmax >= 100.0


def test_default_unit_and_policy_pf():
    assert _default_unit("power_factor")[0] == ""
    vt, vmin, vmax = _default_policy("power_factor")
    assert vt == "number" and vmin == 0.0 and vmax == 1.0
