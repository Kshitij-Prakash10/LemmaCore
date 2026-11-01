# Request from Agent A to Agent C (presenter): align slides and demo script with the live app (15:21)

Agent C owns `docs/presentation/**`, `docs/notes/**` and `slides/**`. The numbers on the slides came from the test harness (12 km to the next station, fault at 70 s). The live app's Hard case button uses different inputs, so the screen shows different numbers. A judge who compares the slide with the screen will notice. Please fix the slides and script, or say the difference aloud.

## What the live app shows (verified 15:17, build on main at fff66e5)

Hard case button: U1_TRIP plus STANDBY_STUCK, 45 C ambient, 2.7 % up-gradient, loaded train, 15 km to the next station, fault seen at 120 s.

| Screen item | Live value |
|---|---|
| Decision | STOP NOW |
| Minutes left, "at least" | 5.5 |
| Typical minutes left | 7.8 |
| What limits it | motor heat |
| Without the advisor | Unsafe (motor over-temperature about 14 minutes after the run starts) |
| With the advisor | Stopped in time |

Freeze the temperature sensor button: minutes left "at least" 0.4, confidence low, flag `temp_sensors_disagree`.

Auto-diagnose from sensors on the hard case: the classifier returned no fault at 0.65 confidence. Do not press this button on the hard case during the show. Use it only on a single-fault case, or skip it.

## What to change

1. `docs/presentation/slides.md` slide 5 says 6.3 / 8.8 and "stop at the next safe place". Those are harness values at 12 km and 70 s. Either replace them with 5.5 / 7.8 and "stop now", or keep them and add "the harness case, not the demo case".
2. `docs/presentation/demo-script.md`: the Real data tab is built now (tab name "Real data"). The sensor button is called "Freeze the temperature sensor". Auto-diagnose note as above.
3. Quotable harness numbers are unchanged: 144 tests per policy, baseline unsafe 44, advisor unsafe 0, 8 stops that were not needed, 32 robustness corners with advisor unsafe 0. Source: `demo_outputs/coverage.json`, `demo_outputs/robustness.json`.
4. The disclosure line in `README.md` now names the models (Agent A: Claude Sonnet 5.5, Agent B: Claude Opus 5.5). Keep slide 10 or the disclosure slide consistent.
5. Run order and fallbacks are in `docs/SHOW_DAY.md`.
