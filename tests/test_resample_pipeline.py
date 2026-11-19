import pytest
from audio import resample_pipeline as mod

CASES = [
    ("step", 'm.step_ratio(48000, 44100) == approx(0.91875)'),
    ("cutoff", 'm.anti_alias_cutoff(44100, 0.9) == approx(39690.0)'),
    ("phase", 'm.phase_drift(0.1, 0.3) == approx(0.2)'),
    ("overlap", 'm.block_overlap(1024, 256) == 768'),
    ("latency", 'm.latency_comp(480, 2) == 240'),
    ("peak", 'm.peak_limit(2.0, 1.0) == approx(1.0)'),
    ("dither", 'm.dither_amplitude(8) == approx(1.0 / 256.0)'),
    ("reset", 'm.reset_state(True, 5) is None'),
    ("reset_keep", 'm.reset_state(False, 5) == 5'),
    ("multi", 'm.multitrack_ratio(2, 0.5) == [0.5, 0.5]'),
    ("dedupe", 'm.software_hardware_dedupe(True, True) is False'),
    ("cache", 'm.cache_key("a", 44100) == "a:44100"'),
    ("thread", 'm.thread_sync(1, 2) is True'),
    ("timebase", 'm.timebase_ratio(30, 60) == approx(0.5)'),
    ("sample", 'm.sample_at(10, 2) == 20')
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx})
