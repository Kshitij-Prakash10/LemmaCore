# Contract: interfaces between Agent A (core) and Agent B (ML and app)

Owner: Agent A. Agent B reads it and codes against it. Changes go through `docs/requests/`. Current version: `CONTRACT_VERSION = "0.2"`.

**Changes in 0.2 (Agent A, 14:33):** (1) `UNSAFE` means a limit was hit while the train was still moving. Loss of an essential load is not unsafe by itself, because its consequence (brake air falling, battery draining) shows up as a limit. (2) `STANDBY_STUCK` alone implies unit 1 is lost with no takeover, so it has an effect as a single fault. (3) `advise()` also returns flags such as `dark_loads:<names>` and `faults_inferred_from_signals`. (4) `Scenario` has defaults for every field except `id`. (5) The harness advisor policy passes the true fault set as `fault_hypothesis` (an oracle). The app should pass the classifier output instead. The core exposes `failover.core.CORE_VERSION`. Every generated dataset and output file records the core version that produced it.

Units: seconds, degrees Celsius, bar, kW, kVA, volts, percent. Time series are sampled every `dt_s` (default 1.0) for `horizon_s` (default 1800).

## 1. Names that both agents use

```python
FAULT_IDS = [
    "U1_TRIP",            # converter unit 1 trips off
    "U2_TRIP",            # converter unit 2 trips off
    "STANDBY_STUCK",      # the standby unit does not take over the orphaned loads
    "MCB_TRIP",           # front-panel MCB trips: unit cut off, load does not shift
    "UNIT_DERATE",        # a unit's capacity falls (heat), here to 50 percent
    "BLOWER_FAIL",        # a cooling blower group stops (cooling falls to its off value)
    "COMPRESSOR_FAIL",    # the brake-air compressor stops, so air pressure decays
    "TEMP_SENSOR_STUCK",  # the observed motor temperature freezes at its last good value
]

CONDITION_IDS = ["cool_flat", "hot_flat", "cool_climb", "hot_climb"]
# cool = 30 C ambient, hot = 45 C ambient, flat = 0 percent gradient, climb = 2.7 percent (1 in 37)
# train_load is "loaded" for all four conditions unless a scenario says otherwise

POLICIES = ["baseline", "advisor"]
# baseline = no load shedding. The crew keeps running toward the next station. Loco protection derates
#            at (limit - 10 C) and trips at the limit. This is a stated modelling assumption.
# advisor  = the load shedding and the continue or stop decision from advise()

OUTCOMES = ["SAFE", "CONTROLLED_STOP", "UNSAFE"]
# SAFE             essential loads stayed on and the train reached the next station without hitting a limit
# CONTROLLED_STOP  the train was stopped (by policy) before any limit was hit
# UNSAFE           a limit (motor temperature, brake air minimum, battery empty) was hit while moving,
#                  or an essential load lost power
```

Single faults: 8. Pairs: C(8,2) = 28. Combinations: 36. Conditions: 4. Cases per policy: 144. Runs for both policies: 288.

## 2. Types (defined in `failover/core/types.py`, owned by Agent A)

```python
@dataclass(frozen=True)
class Scenario:
    id: str
    faults: tuple[str, ...]           # subset of FAULT_IDS, length 0 to 2 in the harness
    ambient_c: float                  # 20 to 48
    gradient_pct: float               # 0.0 to 3.0
    train_load: str                   # "empty" | "loaded"
    units: int                        # converter count, 2 or 3
    dist_next_station_km: float       # 1 to 30
    speed_kmph: float                 # 20 to 100
    noise: float                      # sensor noise level, 0.0 to 0.1 (fraction of range)
    seed: int
    params: dict                      # optional overrides for domain randomization, keys as in config

@dataclass
class SimResult:
    scenario_id: str
    policy: str                       # "baseline" | "advisor"
    core_version: str
    t_s: list[float]
    true: dict[str, list[float]]      # true signals, names in section 3
    observed: dict[str, list[float]]  # what sensors report: noise added, stuck sensors frozen
    events: list[dict]                # {"t_s": 12.0, "type": "fault_injected", "fault": "U1_TRIP"} etc.
    outcome: str                      # one of OUTCOMES
    limit_hit: str | None             # "motor_temp" | "brake_air" | "battery" | "power" | None
    t_limit_s: float | None
    reached_station: bool
    minutes_left_true: float | None   # time from fault until the first limit, with the chosen load plan

@dataclass
class Advice:
    shed: list[str]                   # load names to switch off
    keep: list[str]                   # load names to keep on
    minutes_left_p5: float            # 5th percentile of minutes until the first limit
    minutes_left_nominal: float
    limiting_factor: str              # "heat" | "air" | "battery" | "power"
    decision: str                     # "CONTINUE" | "STOP_AT_NEXT" | "STOP_NOW"
    reason: str                       # one plain sentence for the pilot
    confidence: str                   # "high" | "low"
    flags: list[str]                  # e.g. "temp_sensors_disagree", "diagnosis_low_confidence"
    assumptions_used: list[str]       # config keys whose status is "assumed"
```

## 3. Signal names

All series are lists of floats, same length as `t_s`.

| Name | Unit | Meaning |
|---|---|---|
| `unit1_state`, `unit2_state`, `unit3_state` | 0, 1, 2 | 0 healthy, 1 derated, 2 tripped (unit3 only when `units` is 3) |
| `unit1_load_kva`, `unit2_load_kva`, `unit3_load_kva` | kVA | load carried by each unit |
| `power_demand_kw`, `power_available_kw` | kW | demand of loads switched on, and what the healthy units can supply |
| `dc_link_v` | V | converter DC link voltage |
| `blower_motor_pct`, `blower_oil_pct` | % | speed of the two cooling groups (0 when unpowered) |
| `motor_temp_c`, `converter_temp_c` | C | traction motor and converter temperatures |
| `air_pressure_bar` | bar | main reservoir pressure |
| `battery_v`, `battery_soc_pct` | V, % | control battery |
| `loads_on` | count | number of loads switched on |

`true` has all of them. `observed` has the same names, with noise added, and with `motor_temp_c` frozen when `TEMP_SENSOR_STUCK` is active. The classifier must use `observed` only.

## 4. Functions

```python
# failover/core/simulate.py
def simulate(scenario: Scenario, policy: str, config: dict | None = None,
             horizon_s: int = 1800, dt_s: float = 1.0) -> SimResult: ...

# failover/core/advisor.py
def advise(observation: dict, config: dict | None = None,
           fault_hypothesis: list[str] | None = None) -> Advice: ...
# observation keys: "observed" (dict of short windows, last 60 s), "context" (ambient_c, gradient_pct,
# train_load, units, dist_next_station_km, speed_kmph). If fault_hypothesis is None the advisor infers the
# state from observed signals with simple rules. If given, it trusts it unless it flags a conflict.

# failover/core/harness.py
def run_harness(config: dict | None = None, out_dir: str = "outputs",
                n_mc: int = 200) -> dict: ...
# CLI: python -m failover.core.harness --out outputs

# failover/core/config.py
def load_config(path: str = "config/loco.json") -> dict: ...
```

Rules for the core: pure functions of their inputs, no global state, deterministic given the seed, `advise()` under 50 ms, `simulate()` for 1800 s under 0.5 s.

### ML interface (Agent B, `failover/ml/infer.py`)

```python
def diagnose(observed_window: dict[str, list[float]]) -> dict:
    # {"faults": {fault_id: probability}, "predicted": [fault_id, ...], "confidence": float}

def compressor_anomaly(window: dict[str, list[float]]) -> float:
    # anomaly score for the MetroPT-3 demo, higher is more abnormal

def minutes_left_p5(features: dict) -> float | None:
    # surrogate, stretch. Return None if the model file is missing.
```

Safety rule: the surrogate may lower the advisor's minutes-left but never raise it. The advisor takes the minimum of the physics value and the surrogate value.

## 5. Files that cross the boundary

| File | Written by | Read by | Content |
|---|---|---|---|
| `config/loco.json` | A (human edits via A) | everyone | parameters with `status` and `source` |
| `outputs/coverage.json` | A harness (generated, not committed) | B app | see below |
| `demo_outputs/coverage.json` | A (committed copy) | B app, when `outputs/` is absent | same schema |
| `outputs/runs.csv` | A harness | B report | one row per run |
| `outputs/sensitivity.json` (copy in `demo_outputs/`) | A harness (`make harness` writes it) | B app | for 3 cases, how minutes-left changes when each assumed parameter moves 20 percent, sorted by swing. Keys: `cases[].case`, `nominal_minutes`, `limiting_factor`, `parameters[].parameter`, `config_path`, `status`, `minutes_at_minus_20pct`, `minutes_at_plus_20pct`, `swing_minutes` |
| `outputs/report.html` | A harness | humans | static test report, no external assets |
| `data/processed/air_params_fit.json` | B | A (optional) | fitted brake-air leak range from MetroPT-3, see AGENT_B.md |
| `data/processed/scenarios.parquet` or `.csv` | B | B | training data generated by the core |
| `models/*.joblib`, `models/metrics.json` | B | B app | trained models and held-out metrics |

### `coverage.json` schema

```json
{
  "core_version": "0.1",
  "generated_utc": "2026-11-01T14:00:00Z",
  "seed": 1,
  "conditions": [
    {"id": "hot_climb", "ambient_c": 45, "gradient_pct": 2.7, "train_load": "loaded"}
  ],
  "faults": ["U1_TRIP", "U2_TRIP", "STANDBY_STUCK", "MCB_TRIP", "UNIT_DERATE", "BLOWER_FAIL", "COMPRESSOR_FAIL", "TEMP_SENSOR_STUCK"],
  "cases": [
    {
      "case_id": "STANDBY_STUCK__hot_climb",
      "faults": ["STANDBY_STUCK"],
      "condition": "hot_climb",
      "baseline": {"outcome": "UNSAFE", "limit_hit": "motor_temp", "t_limit_s": 420.0, "reached_station": false},
      "advisor": {"outcome": "CONTROLLED_STOP", "minutes_left_p5": 14.2, "decision": "STOP_AT_NEXT",
                  "shed": ["cab_ac"], "limiting_factor": "heat", "reached_station": true},
      "properties_ok": true
    }
  ],
  "summary": {"runs_per_policy": 144, "baseline_unsafe": 0, "advisor_unsafe": 0, "properties_failed": 0}
}
```

`baseline_unsafe` and `advisor_unsafe` hold the real counts. The numbers above are an example of the shape only. No agent may hard-code results.

## 6. Versioning

When the core changes the meaning of a signal or the physics enough to change data, A bumps `CORE_VERSION` and logs the change in `docs/model.md`. B regenerates the training data and records the version in `models/metrics.json`. A test in `tests/ml` fails if the model's recorded core version differs from the current one.
