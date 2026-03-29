"""
SCAN-01 behavioral test: phase offset computation and application.

Verifies that:
1. MaszynaStanow._przejdz_do(STATE_SCANNING) computes _scan_phase_offset
   using math.asin(clamp(pan/SCAN_AMPLITUDE)), clamped to [-1, 1].
2. _skanuj() applies _scan_phase_offset in the sinusoidal formula so the
   first pan value at state-entry time matches the current servo position.

Does NOT require picamera2 — mocks it in sys.modules before import.
Runs in hardware mock mode (no pigpio/gpiozero needed).
"""

import sys
import os
import types
import math
import time

# Ensure project root is on sys.path (tests/ lives one level below root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -----------------------------------------------------------------------
# Stub out picamera2 so test_tracker can be imported on any machine.
# The module-level sys.exit(1) fires only if ImportError is raised, so
# inserting a minimal stub prevents that branch.
# -----------------------------------------------------------------------
_picamera2_stub = types.ModuleType("picamera2")


class _FakePicamera2:
    pass


_picamera2_stub.Picamera2 = _FakePicamera2
sys.modules.setdefault("picamera2", _picamera2_stub)

# Now safe to import
from src.modes.test_tracker import (  # noqa: E402
    MaszynaStanow,
    SCAN_AMPLITUDE,
    SCAN_FREQUENCY,
    STATE_TARGET_LOST,
)
from src import config  # noqa: E402


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------

def _pan_from_offset(offset: float, t: float) -> float:
    """Expected pan formula matching _skanuj() implementation."""
    return SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t + offset)


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

def test_scan_phase_offset_field_exists_on_init():
    """_scan_phase_offset is initialised to 0.0 in __init__ (no AttributeError)."""
    maszyna = MaszynaStanow()
    assert hasattr(maszyna, "_scan_phase_offset"), \
        "MaszynaStanow.__init__ must define _scan_phase_offset"
    assert maszyna._scan_phase_offset == 0.0, \
        f"Initial _scan_phase_offset must be 0.0, got {maszyna._scan_phase_offset}"
    print("PASS test_scan_phase_offset_field_exists_on_init")


def test_phase_offset_computed_correctly_at_scanning_entry_centre():
    """
    When pan_angle == 0.0 (centre), entering SCANNING produces offset == 0.0.
    asin(clamp(0 / 45)) == asin(0) == 0.
    """
    maszyna = MaszynaStanow()
    maszyna.hardware.pan_angle = 0.0
    maszyna.stan = config.STATE_TRACKING  # Come from TRACKING state

    maszyna._przejdz_do(config.STATE_SCANNING)

    expected = math.asin(0.0)  # 0.0
    assert math.isclose(maszyna._scan_phase_offset, expected, abs_tol=1e-9), \
        f"offset at pan=0 must be {expected}, got {maszyna._scan_phase_offset}"
    print(f"PASS test_phase_offset_computed_correctly_at_scanning_entry_centre  (offset={maszyna._scan_phase_offset:.4f})")


def test_phase_offset_computed_correctly_at_scanning_entry_offset_pan():
    """
    When pan_angle == 22.5 (half amplitude), entering SCANNING produces
    offset == asin(0.5) == pi/6 ≈ 0.5236.
    """
    maszyna = MaszynaStanow()
    pan_value = SCAN_AMPLITUDE / 2.0  # 22.5
    maszyna.hardware.pan_angle = pan_value
    maszyna.stan = config.STATE_TRACKING

    maszyna._przejdz_do(config.STATE_SCANNING)

    expected = math.asin(0.5)  # pi/6
    assert math.isclose(maszyna._scan_phase_offset, expected, abs_tol=1e-9), \
        f"offset at pan={pan_value} must be {expected:.6f}, got {maszyna._scan_phase_offset:.6f}"
    print(f"PASS test_phase_offset_computed_correctly_at_scanning_entry_offset_pan  (offset={maszyna._scan_phase_offset:.4f})")


def test_phase_offset_clamp_prevents_value_error_when_pan_exceeds_amplitude():
    """
    When pan_angle == 55.0 > SCAN_AMPLITUDE (45.0), raw ratio > 1.0.
    Without clamp: math.asin(1.22) raises ValueError.
    With clamp:   math.asin(1.0) == pi/2, no exception.
    """
    maszyna = MaszynaStanow()
    maszyna.hardware.pan_angle = 55.0  # Exceeds SCAN_AMPLITUDE
    maszyna.stan = config.STATE_TRACKING

    # Must NOT raise ValueError
    try:
        maszyna._przejdz_do(config.STATE_SCANNING)
    except ValueError as e:
        raise AssertionError(
            f"_przejdz_do raised ValueError when pan={maszyna.hardware.pan_angle} > SCAN_AMPLITUDE={SCAN_AMPLITUDE}: {e}"
        ) from e

    expected = math.asin(1.0)  # pi/2 — clamped
    assert math.isclose(maszyna._scan_phase_offset, expected, abs_tol=1e-9), \
        f"clamped offset must be {expected:.6f}, got {maszyna._scan_phase_offset:.6f}"
    print(f"PASS test_phase_offset_clamp_prevents_value_error_when_pan_exceeds_amplitude  (offset={maszyna._scan_phase_offset:.4f})")


def test_phase_offset_clamp_prevents_value_error_negative_extreme():
    """Negative pan exceeding -SCAN_AMPLITUDE must also be clamped."""
    maszyna = MaszynaStanow()
    maszyna.hardware.pan_angle = -60.0  # Exceeds -SCAN_AMPLITUDE
    maszyna.stan = config.STATE_TRACKING

    try:
        maszyna._przejdz_do(config.STATE_SCANNING)
    except ValueError as e:
        raise AssertionError(
            f"_przejdz_do raised ValueError on negative extreme pan: {e}"
        ) from e

    expected = math.asin(-1.0)  # -pi/2 — clamped
    assert math.isclose(maszyna._scan_phase_offset, expected, abs_tol=1e-9), \
        f"clamped offset must be {expected:.6f}, got {maszyna._scan_phase_offset:.6f}"
    print(f"PASS test_phase_offset_clamp_prevents_value_error_negative_extreme  (offset={maszyna._scan_phase_offset:.4f})")


def test_skanuj_applies_phase_offset_to_sinusoid():
    """
    When _skanuj() is called immediately after _przejdz_do(STATE_SCANNING),
    the hardware pan_angle after the call should match the expected formula:
        pan = SCAN_AMPLITUDE * sin(2pi * f * t + offset)

    We set a known pan position before entry, compute the expected offset,
    then call _skanuj() and verify the resulting pan_angle matches.
    Because time.time() is used internally, we allow a small tolerance
    corresponding to ~1 frame at 30 FPS (33ms).
    """
    maszyna = MaszynaStanow()
    # Set pan to a known mid-amplitude position
    initial_pan = 22.5  # half SCAN_AMPLITUDE
    maszyna.hardware.pan_angle = initial_pan
    maszyna.stan = config.STATE_TRACKING

    maszyna._przejdz_do(config.STATE_SCANNING)
    offset = maszyna._scan_phase_offset

    t_before = time.time()
    maszyna._skanuj()
    t_after = time.time()

    actual_pan = maszyna.hardware.pan_angle

    # Verify actual_pan is consistent with the formula at some t in [t_before, t_after]
    expected_min = min(
        _pan_from_offset(offset, t_before),
        _pan_from_offset(offset, t_after),
    )
    expected_max = max(
        _pan_from_offset(offset, t_before),
        _pan_from_offset(offset, t_after),
    )

    # Add generous tolerance (1 full sinusoid period drift = 10s, so within 33ms window it's tiny)
    tolerance = SCAN_AMPLITUDE * 2.0 * math.pi * SCAN_FREQUENCY * (t_after - t_before) + 0.01

    assert expected_min - tolerance <= actual_pan <= expected_max + tolerance, (
        f"_skanuj() produced pan_angle={actual_pan:.4f} which is outside "
        f"expected range [{expected_min - tolerance:.4f}, {expected_max + tolerance:.4f}] "
        f"for offset={offset:.4f}"
    )
    print(f"PASS test_skanuj_applies_phase_offset_to_sinusoid  (pan={actual_pan:.4f}, offset={offset:.4f})")


# -----------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_scan_phase_offset_field_exists_on_init,
        test_phase_offset_computed_correctly_at_scanning_entry_centre,
        test_phase_offset_computed_correctly_at_scanning_entry_offset_pan,
        test_phase_offset_clamp_prevents_value_error_when_pan_exceeds_amplitude,
        test_phase_offset_clamp_prevents_value_error_negative_extreme,
        test_skanuj_applies_phase_offset_to_sinusoid,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1

    print(f"\n--- SCAN-01: {passed} passed, {failed} failed ---")
    if failed:
        sys.exit(1)
