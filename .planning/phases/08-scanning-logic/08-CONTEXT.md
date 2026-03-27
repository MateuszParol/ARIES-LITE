# Phase 8: Scanning Logic - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Dwie chirurgiczne poprawki w `src/modes/test_tracker.py`:
1. **SCAN-01**: Sinusoida startuje od aktualnej pozycji pana przy powrocie z TRACKING do SCANNING — bez skoku serwa w pierwszej klatce skanowania.
2. **SCAN-02**: Streak filter resetowany przy wejściu w TARGET_LOST (nie przy wejściu w SCANNING) — twarz w oknie TARGET_LOST wymaga pełnych 3 kolejnych klatek przed przejściem do TRACKING.

Faza NIE zmienia: logiki PID, architektury maszyny stanów, parametrów HAAR, modelu konfiguracji ani żadnego innego zachowania systemu.

</domain>

<decisions>
## Implementation Decisions

### Phase offset — SCAN-01
- Sinusoida kontynuuje od **aktualnej pozycji serwa** przy wejściu do SCANNING: `φ = arcsin(clamp(pan_angle / SCAN_AMPLITUDE, -1.0, 1.0))`
- Phase offset przechowywany jako `_scan_phase_offset: float` w `MaszynaStanow` — obliczany w `_przejdz_do()` przy `nowy_stan == STATE_SCANNING`
- Edge case `|pan_angle| > SCAN_AMPLITUDE`: clamp do ±1.0 przed arcsin — mały skok (max kilka stopni), następnie płynna sinusoida

### Streak reset — SCAN-02
- `resetuj_streak()` wołany **przy wejściu w TARGET_LOST** w `TestTracker.uruchom()` — zmień warunek z `STATE_SCANNING` na `STATE_TARGET_LOST`
- Tylko TARGET_LOST entry — nie dodawać dodatkowego resetu przy SCANNING (byłby redundantny)
- TARGET_LOST widoczny w HUD przez **1 klatkę** — bez zmian (potwierdzone w v1.6)

### Weryfikacja na hardware
- **SCAN-01**: Wizualnie — obserwacja serwa podczas przejścia TRACKING→SCANNING (brak widocznego skoku)
- **SCAN-02**: Wizualnie w HUD — twarz pokazana w oknie TARGET_LOST nie może wywołać TRACKING w mniej niż 3 klatki

### Claude's Discretion
- Dokładna nazwa zmiennej dla phase offset (`_scan_phase_offset` lub inna)
- Czy obliczać offset na początku `_skanuj()` vs w `_przejdz_do()` (preferuj `_przejdz_do()` — jednokrotne obliczenie)
- Sposób aplikacji offsetu w `_skanuj()`: `A * sin(2π * f * t + φ)` lub przez odjęcie czasu

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MaszynaStanow._przejdz_do()` (`test_tracker.py:282`): Miejsce do obliczenia `_scan_phase_offset` — already handles PID reset on SCANNING entry
- `MaszynaStanow._skanuj()` (`test_tracker.py:255`): Metoda do modyfikacji — dodać `+ self._scan_phase_offset` do argumentu sin
- `TestTracker.uruchom()` (`test_tracker.py:334-337`): Miejsce do zmiany warunku streak reset z `STATE_SCANNING` na `STATE_TARGET_LOST`
- `DetekcjaTwarzy.resetuj_streak()` (`test_tracker.py:194`): Gotowa metoda — tylko zmiana miejsca wywołania

### Established Patterns
- `MaszynaStanow` inicjalizuje pola w `__init__` — `_scan_phase_offset = 0.0` pasuje do wzorca
- `_przejdz_do()` obsługuje już side-effects przy zmianie stanu (PID reset) — dodanie phase offset jest spójne
- Stałe modułowe UPPER_SNAKE_CASE: `SCAN_AMPLITUDE`, `SCAN_FREQUENCY` — już dostępne w `_skanuj()`

### Integration Points
- `_skanuj()` wywoływana w każdej klatce podczas SCANNING — modyfikacja musi być tania obliczeniowo (arcsin tylko raz, w `_przejdz_do()`)
- `poprzedni_stan` tracking w `uruchom()` (linia 312) — mechanizm do wykrycia TARGET_LOST entry już istnieje

</code_context>

<specifics>
## Specific Ideas

- Phase offset obliczany w `_przejdz_do()` (jednorazowo przy zmianie stanu), nie w każdej klatce `_skanuj()`
- Formula: `self._scan_phase_offset = math.asin(max(-1.0, min(1.0, self.hardware.pan_angle / SCAN_AMPLITUDE)))`
- Użycie: `pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t + self._scan_phase_offset)`

</specifics>

<deferred>
## Deferred Ideas

Brak — dyskusja pozostała w granicach fazy.

</deferred>

---

*Phase: 08-scanning-logic*
*Context gathered: 2026-03-27*
