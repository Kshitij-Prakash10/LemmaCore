# Agent A brief: core (plant models, advisor, fault harness)

You own `failover/core/**`, `config/**`, `CONTRACT.md`, `tests/core/**`, `demo_outputs/**`, `docs/model.md` and `docs/STATUS_A.md`. Read `CONTEXT.md`, `OWNERSHIP.md` and `CONTRACT.md` first. Your branch is `agent-a/core`.

Your job in one line: make the physics and the decision logic correct, fast and testable, and produce the proof (the fault-injection coverage map). Agent B builds the ML and the app on top of your contract, so land the types and a thin working `simulate`/`advise` early.

## What you build

### The converter model (`converter.py`)
- `units` converters (2 or 3), each with capacity `unit_kva * power_factor` in kW, reduced when `UNIT_DERATE` is active or when ambient passes `derate.start_ambient_c` (a simple linear curve from the config).
- Normal state: loads are shared across healthy units.
- `U1_TRIP` or `U2_TRIP`: that unit goes to state 2. Its loads move to the remaining healthy units up to their capacity.
- `STANDBY_STUCK`: the failover does not happen. The loads of the tripped unit stay unpowered.
- `MCB_TRIP`: the unit is cut off and the load does not shift (as sheds reported).
- Output at each step: which loads are powered, `power_demand_kw`, `power_available_kw`, each unit's state and load.

### The heat model (`heat.py`)
For each cooling group, `C * dT/dt = Q - h * (T - T_amb)`, with `h = h_on * cooling_fraction` where the cooling fraction is the blower speed fraction, floored at `h_off_ratio` when the blower group is unpowered. `Q` depends on the gradient and train load. Provide both a closed-form time to limit (constant `Q`) and a stepping simulation, and test that they agree. When halving `dt_s` the time to limit must change by less than 1 percent.

### The brake-air model (`air.py`)
`dP/dt = fill_rate * compressor_on - leak_rate`. The time to the brake-air minimum is the second number the advisor needs. `air_params_fit.json` from Agent B, when present, gives a fitted leak range. Use it only if `config.air.use_fitted` is true, and record that in `assumptions_used`.

### The battery model (`battery.py`, should have)
Usable charge divided by control current. It is rarely the limiting factor, but keep it so the three limits are shown.

### The advisor (`advisor.py`)
1. Get the fault set: from `fault_hypothesis` if given, else infer it from `observed` with simple rules (a unit load dropped to zero, a blower speed zero, and so on).
2. Compute the power available.
3. Search every subset of loads (at most about 1,024): skip a subset if its demand exceeds the available power, or if an essential load (brake compressor, control and charger) is off. For each subset compute the minutes to the heat limit, the brake-air limit and the battery limit. Keep the subset with the most minutes, preferring to keep more loads on ties.
4. Minutes left are `min(t_heat, t_air, t_battery)`. Run `mc_runs` (default 200) Monte Carlo draws, sampling parameters uniformly inside their `min` and `max` in the config, and report the 5th percentile as `minutes_left_p5`.
5. Decision: `CONTINUE` if the time to the next station is at most `safety_factor` (0.8) times `minutes_left_p5`; `STOP_AT_NEXT` if a safe place is reachable within the minutes left but the station is not; otherwise `STOP_NOW`.
6. **Wrong data:** if two temperature readings disagree by more than a threshold, or one is flat while the other changes, add the flag `temp_sensors_disagree`, set `confidence` to `low`, and use the more pessimistic reading.
7. The reason string is one plain sentence a pilot can read in two seconds.

### The harness (`harness.py`)
- Enumerate the 8 single faults and the 28 pairs (36 combinations), times the 4 conditions, for both policies. Seeded. Parallelise with `concurrent.futures` if useful.
- Check four properties on every run: brake air stays above its minimum while moving under the advisor; control power is never lost under the advisor; the advisor never recommends more load than there is power for; the minutes-left value is never more optimistic than the simulated time to limit.
- Write `outputs/coverage.json` (schema in `CONTRACT.md`), `outputs/runs.csv`, and `outputs/report.html` (static, no external assets, includes the assumptions table and the headline numbers). Copy `coverage.json` to `demo_outputs/` at each milestone.
- Headline numbers come from the real run. Never hard-code them.

### Tuning the config
The starting values in `config/loco.json` are guesses. Tune them within plausible ranges so that the hard case (`hot_climb`, `STANDBY_STUCK`) gives roughly 10 to 20 minutes, and so that the baseline hits a limit before the next station in at least some cases and not in all of them. Keep them all marked `assumed`. Record every tuning in `docs/model.md`.

## Milestones (from the start of the build)

| By | Deliver | Done when |
|---|---|---|
| **M0, 10 min** | `types.py`, `CORE_VERSION`, `config.py`, a thin `simulate()` and `advise()` that return shape-correct results from the contract, `tests/core/test_contract.py`. Merge to `main`. | Agent B can import them and run one scenario. |
| **M1, 35 min** | Real converter state machine, heat model with closed-form check, air model, advisor with subset search. `python -m failover.core.cli demo` prints the advice for the hard case. | One end-to-end hard case works. This is the progress-review slice. |
| **M2, 70 min** | Harness, properties, `coverage.json`, `runs.csv`, `report.html`. Monte Carlo p5. Sensor-disagreement logic. Numerical convergence test. | `make harness` produces 144 cases per policy and no property fails, or the failures are explained. |
| **M3, 95 min** | Battery model, `sensitivity.json` (change each parameter by 20 percent, record minutes-left change), notes in `docs/model.md`. | Agent B can show the sensitivity view. |
| **Freeze, last 15 min** | Tests green, `docs/model.md` explains every equation and assumption, `docs/STATUS_A.md` lists AI and open-source use. | |

## Tests you write
Contract shape; determinism (same seed, same result); closed form against stepping; time-step halving; each fault changes the signals it should; the four harness properties; the advisor never exceeds power; the advisor is never more optimistic than the simulation; `advise()` under 50 ms.

## Do not
- Edit `failover/ml`, `failover/app`, `failover/stubs`, `data`, `models` or any human-owned file.
- Add predictive maintenance, passenger features or cloud calls.
- Change a signal name or a type without a contract change and a `CORE_VERSION` bump.
- Claim a number is confirmed. Only a human flips a `status` to `confirmed`.

## First 10 minutes
1. `git pull`, create `agent-a/core`, read the four documents.
2. Create a virtual environment and install: `pip install -r requirements-core.txt`. The laptop has Python 3.14, so check that numpy and scipy install. If they do not, tell the human at once and write the request.
3. Write `types.py` and the thin functions. Run the contract test. Merge to `main`. Update `docs/STATUS_A.md`.
