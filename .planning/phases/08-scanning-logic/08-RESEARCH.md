# Phase 8: Scanning Logic - Research

**Researched:** 2026-03-27
**Domain:** Python state machine / sinusoidal servo control / streak filter reset
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **SCAN-01 formula:** `φ = arcsin(clamp(pan_angle / SCAN_AMPLITUDE, -1.0, 1.0))` — computed once in `_przejdz_do()` when `nowy_stan == STATE_SCANNING`
- **SCAN-01 storage:** `_scan_phase_offset: float` field on `MaszynaStanow`, initialised to `0.0` in `__init__`
- **SCAN-01 edge case:** `|pan_angle| > SCAN_AMPLITUDE` — clamp before arcsin; accepts max few-degree discontinuity, then smooth sine
- **SCAN-02 trigger point:** `resetuj_streak()` called on TARGET_LOST *entry* — change condition in `TestTracker.uruchom()` from `STATE_SCANNING` to `STATE_TARGET_LOST`
- **SCAN-02 no extra reset:** Do NOT add a second reset on SCANNING entry (would be redundant)
- **Scope boundary:** Changes confined to `src/modes/test_tracker.py` only — no PID logic, no state-machine architecture, no HAAR params, no config model

### Claude's Discretion

- Exact variable name for phase offset (`_scan_phase_offset` or other — prefer `_scan_phase_offset`)
- Whether to compute offset at top of `_skanuj()` vs inside `_przejdz_do()` (prefer `_przejdz_do()` — single computation)
- How to apply offset in `_skanuj()`: `A * sin(2π * f * t + φ)` or by subtracting time

### Deferred Ideas (OUT OF SCOPE)

Brak — dyskusja pozostała w granicach fazy.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCAN-01 | Powrót z TRACKING do SCANNING nie powoduje skoku serwa — sinusoida startuje od aktualnej pozycji (phase offset) | Formula verified against existing `_skanuj()` implementation; `math.asin` already imported via `math` module; `hardware.pan_angle` is readable at state-transition time |
| SCAN-02 | Streak filter resetowany przy wejściu w TARGET_LOST (nie czeka do SCANNING) | `DetekcjaTwarzy.resetuj_streak()` exists at line 194; call site in `uruchom()` lines 334-337; `STATE_TARGET_LOST` constant already defined at module level |
</phase_requirements>

---

## Summary

Phase 8 is two independent surgical fixes inside `src/modes/test_tracker.py`. No new dependencies, no architectural changes. Both fixes are fully reversible and self-contained.

**SCAN-01** solves servo jerk on TRACKING→SCANNING transition. Currently `_skanuj()` (line 258) computes `pan = SCAN_AMPLITUDE * math.sin(2π * f * t)` using raw wall-clock time `t`. When the system re-enters SCANNING after tracking, `t` is at an arbitrary phase of the sinusoid, so the commanded pan position may differ from where the servo physically sits — causing a step change. The fix adds a phase offset φ computed from the actual servo position at the moment of state transition, so the first scan frame commands the same angle the servo is already at.

**SCAN-02** solves premature TRACKING re-entry during the TARGET_LOST window. Currently the streak is reset when `stan == STATE_SCANNING and previous != STATE_SCANNING` (lines 334-337). Because TARGET_LOST is a single-frame pass-through state (it immediately calls `_przejdz_do(STATE_SCANNING)` in the same tick), the streak reset happens one frame *after* the detection that triggered the TRACKING-bound transition can already be counted. Moving the reset to TARGET_LOST *entry* ensures no accumulated streak credit survives the grace window.

**Primary recommendation:** Make both changes in a single commit — they are independent but small enough that a single diff is cleaner.

---

## Standard Stack

No new libraries required. All used modules are already present:

| Module | Already imported? | Usage |
|--------|------------------|-------|
| `math` | Yes (line 8) | `math.asin`, `math.pi`, `math.sin` |
| `time` | Yes (line 10) | `time.time()` in `_skanuj()` |
| `src.config` | Yes (line 19) | `STATE_SCANNING` |
| `STATE_TARGET_LOST` | Yes (line 38, module-level constant) | Condition check in `uruchom()` |

**Installation:** none required.

---

## Architecture Patterns

### Existing Pattern: State-entry side effects in `_przejdz_do()`

`_przejdz_do()` (lines 282-289) is the single choke-point for all state transitions. It already performs a PID reset on SCANNING entry. Adding phase-offset computation here is consistent with the established pattern — all state-entry side effects live in one place.

```python
# Current _przejdz_do() (lines 282-289)
def _przejdz_do(self, nowy_stan: str) -> None:
    logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
```

SCAN-01 addition — append inside the `if nowy_stan == config.STATE_SCANNING` block:

```python
        raw = self.hardware.pan_angle / SCAN_AMPLITUDE
        self._scan_phase_offset = math.asin(max(-1.0, min(1.0, raw)))
```

### Existing Pattern: Module-level constants UPPER_SNAKE_CASE

`SCAN_AMPLITUDE` and `SCAN_FREQUENCY` follow this convention (lines 30-31). The new instance field `_scan_phase_offset` follows the class-field naming already used (`_streak`, `_czas_ostatniego_celu`).

### Existing Pattern: `__init__` initialises all instance fields

`MaszynaStanow.__init__` (lines 202-216) initialises every field used by the class. Adding `self._scan_phase_offset = 0.0` there is mandatory for correctness — the first SCANNING session (before any TRACKING→SCANNING transition) must use offset 0 (start of sinusoid from 0°, which is where `smooth_move_to(0,0)` leaves the servo at `inicjalizuj()` time).

### Existing Pattern: Streak reset via `resetuj_streak()`

`DetekcjaTwarzy.resetuj_streak()` is already a dedicated method (line 194). The only change needed is the *call site* condition.

```python
# Current call site (lines 334-337 in uruchom())
if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING:
    self.detekcja.resetuj_streak()
poprzedni_stan = stan
```

SCAN-02 replacement condition:

```python
if stan == STATE_TARGET_LOST and poprzedni_stan != STATE_TARGET_LOST:
    self.detekcja.resetuj_streak()
```

### Anti-Patterns to Avoid

- **Computing phase offset in `_skanuj()` every frame:** `math.asin` is cheap but the offset only needs computing once per state transition. Pointless per-frame overhead.
- **Adding offset to tilt:** The sinusoidal scan is pan-only. `_skanuj()` hard-codes `tilt=0.0`. No offset needed for tilt.
- **Using `AwbEnable: False`** (out of scope, but worth noting): established project decision from Phase 6 — do NOT add.
- **Resetting streak on SCANNING entry in addition to TARGET_LOST:** Would be redundant. CONTEXT.md explicitly forbids the double reset.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inverse-sine for phase continuity | Custom iterative approximation | `math.asin` | Already in stdlib, handles ±1 boundary |
| Clamp to valid arcsin domain | Custom range-check function | `max(-1.0, min(1.0, x))` inline | One-liner, no helper needed |

---

## Common Pitfalls

### Pitfall 1: Phase offset initialisation missing from `__init__`

**What goes wrong:** `AttributeError: 'MaszynaStanow' object has no attribute '_scan_phase_offset'` on first SCANNING frame (before any state transition has computed it).
**Why it happens:** `_przejdz_do()` computes the offset but `_skanuj()` references it on every frame. If `inicjalizuj()` calls `_skanuj()` before any transition has fired, the attribute does not exist.
**How to avoid:** Add `self._scan_phase_offset = 0.0` to `MaszynaStanow.__init__` (after `self._czas_ostatniego_celu`).
**Warning signs:** Traceback on startup before any face is detected.

### Pitfall 2: arcsin domain error when pan is outside ±SCAN_AMPLITUDE

**What goes wrong:** `ValueError: math domain error` from `math.asin(x)` when `|x| > 1.0`.
**Why it happens:** `hardware.pan_angle` can be up to ±60° (soft limit) but `SCAN_AMPLITUDE = 45.0°`. At a tracking position of e.g. 55°, `55/45 ≈ 1.22` — outside arcsin domain.
**How to avoid:** Clamp before the call: `max(-1.0, min(1.0, pan_angle / SCAN_AMPLITUDE))`.
**Warning signs:** Exception logged at state transition, servo stops responding.

### Pitfall 3: Streak reset condition matches wrong transition

**What goes wrong (current code):** The existing condition `stan == STATE_SCANNING and previous != STATE_SCANNING` triggers on the frame *after* TARGET_LOST. Because TARGET_LOST is a single-tick pass-through (tick N: TARGET_LOST, tick N+1: SCANNING), the streak resets one frame later than needed. If a face was visible in tick N and the streak was already at 2, re-entering SCANNING with streak=2 means only 1 more consecutive detection is needed — violating the "full 3 frames" requirement.
**How to avoid:** Reset on `stan == STATE_TARGET_LOST and previous != STATE_TARGET_LOST`.
**Warning signs:** TRACKING re-entered in fewer than 3 frames after a TARGET_LOST transition.

### Pitfall 4: Wrong sign convention for phase offset application

**What goes wrong:** Servo snaps to the opposite side of its current position on scan resumption.
**Why it happens:** `sin(φ) = pan/A` means φ could be in either the first or second quadrant for a given sin value. `math.asin` returns the principal value in `[-π/2, +π/2]`. For the continuous sinusoidal motion, this is correct — the servo will approach from the nearest matching phase rather than the opposite one.
**How to avoid:** Use `math.asin` directly (principal value). Do not use `math.atan2` here — the goal is to find the phase of the sine wave, not a full-circle angle.

---

## Code Examples

### SCAN-01: Full diff target

```python
# Source: analysis of test_tracker.py lines 202-216, 255-259, 282-290

# In MaszynaStanow.__init__ — add after line 215:
self._scan_phase_offset: float = 0.0

# In MaszynaStanow._skanuj() — replace line 258:
# BEFORE:
pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t)
# AFTER:
pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t + self._scan_phase_offset)

# In MaszynaStanow._przejdz_do() — append inside `if nowy_stan == config.STATE_SCANNING` block:
raw = self.hardware.pan_angle / SCAN_AMPLITUDE
self._scan_phase_offset = math.asin(max(-1.0, min(1.0, raw)))
```

### SCAN-02: Full diff target

```python
# Source: analysis of test_tracker.py lines 334-337

# BEFORE:
if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING:
    self.detekcja.resetuj_streak()

# AFTER:
if stan == STATE_TARGET_LOST and poprzedni_stan != STATE_TARGET_LOST:
    self.detekcja.resetuj_streak()
```

---

## Validation Architecture

`workflow.nyquist_validation` is not present in `.planning/config.json` — treated as enabled. However, `test_framework` is explicitly `"none"` in `.planning/config.json` and CLAUDE.md confirms "There are no unit tests or linting tools configured. Verification is empirical (HTTP responses, visual confirmation, command output)."

### Test Framework

| Property | Value |
|----------|-------|
| Framework | none — empirical hardware verification only |
| Config file | none |
| Quick run command | `python3 run_test_tracker.py` (on RPi4) |
| Full suite command | `python3 run_test_tracker.py` (on RPi4, visual observation) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| SCAN-01 | No visible servo snap/step on TRACKING→SCANNING transition | manual visual | `python3 run_test_tracker.py` | Observe pan servo during face-cover event; must sweep smoothly without snap |
| SCAN-02 | Face shown during TARGET_LOST window requires 3 consecutive frames before TRACKING | manual visual | `python3 run_test_tracker.py` | Rapidly show/hide face near TARGET_LOST boundary; HUD must not enter TRACKING in < 3 frames |

### Sampling Rate

- **Per task commit:** `python3 run_test_tracker.py` (smoke — does it start without AttributeError or ValueError)
- **Per wave merge:** Full visual verification on RPi4
- **Phase gate:** Both SCAN-01 and SCAN-02 confirmed visually before `/gsd:verify-work`

### Wave 0 Gaps

None — no test files needed. Verification is empirical by project convention.

---

## Sources

### Primary (HIGH confidence)

- `src/modes/test_tracker.py` — direct code inspection; all line references exact
- `src/config.py` — state constants, PID gains, servo limits
- `.planning/phases/08-scanning-logic/08-CONTEXT.md` — locked implementation decisions
- `.planning/REQUIREMENTS.md` — SCAN-01, SCAN-02 requirement text
- `.planning/config.json` — `test_framework: none`, `nyquist_validation` absent

### Secondary (MEDIUM confidence)

- Python stdlib `math` module documentation — `math.asin` principal value `[-π/2, π/2]`, domain `[-1.0, 1.0]` (well-known, no external lookup needed)

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, all modules already imported
- Architecture: HIGH — two-line change each, existing patterns fully understood
- Pitfalls: HIGH — domain error and initialisation pitfalls are deterministic and verified from code

**Research date:** 2026-03-27
**Valid until:** Indefinite — code is stable, no moving dependencies
