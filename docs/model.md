# Core model notes (Agent A)

Version 0.1. Every parameter is in `config/loco.json` and tagged `assumed` until a mentor confirms it.

## Converter model
- Each unit supplies `unit_kva * power_factor * derate_factor(ambient)` kW. The derate factor falls linearly from 1.0 at the start ambient (40 C) to `factor_at_48c` at 48 C. A faulted-derated unit is multiplied by `unit_derate_fault_factor`. A tripped unit supplies nothing.
- Loads are placed in config order. Home unit of load `i` is `i mod units`. If the home unit is down or full and failover works, the load moves to the healthy unit with the most spare capacity. If it does not fit, the load is dark.
- Faults: `U1_TRIP` and `U2_TRIP` trip a unit and failover works. `STANDBY_STUCK` loses unit 1 and failover does not work. `MCB_TRIP` loses unit 1 and failover does not work (as sheds reported). `UNIT_DERATE` cuts unit 2 capacity. `BLOWER_FAIL` stops the motor blower. `COMPRESSOR_FAIL` stops the brake compressor. `TEMP_SENSOR_STUCK` freezes the observed motor temperature.

## Heat model
`C dT/dt = Q - h (T - T_amb)` with `h = h_on` when the motor blower runs and `h_on * h_off_ratio` when it does not. `Q` is `heat_full * heat_scale` while the train moves, and zero when stopped. Closed form time to the trip limit for constant `Q`: `t = -(C/h) ln((T_lim - T_ss)/(T0 - T_ss))`, `T_ss = T_amb + Q/h`. A test checks it against stepping (1 percent). The loco protection halves `Q` within 10 C of the trip.

## Brake-air model
`dP/dt = fill * compressor_on - leak` (bar per minute), capped at the normal pressure. Limit is `brake_air_min_bar`. The advisor is more cautious: it uses minimum plus the emergency reserve.

## Battery model
State of charge falls only when the control and charger load is dark: `control_a / (capacity_ah * usable_fraction)` per hour.

## Advisor
Tries every subset of loads (2^7 = 128), keeps those the converters can feed exactly, prefers more essential loads, then the most minutes to the first limit, then more load kept. Minutes left are the 5th percentile over 200 draws of the parameters uniformly within their min and max. Decision: continue if the station is within 0.8 of the 5th percentile, stop at the nearest safe place (assumed 3 km) if that is within 0.8, else stop now. A flat motor temperature that the model says should move raises `temp_sensors_disagree`, lowers confidence and uses a pessimistic temperature.

## Known limits (v0.1)
- A derated loco is not slowed: protection halves heat but the speed stays the same.
- There is one thermal node (the motors). The converter temperature is derived.
- `minutes_left_true` in `SimResult` is computed with the model's own closed form at the moment the plan is set.
- The advisor's cautious p5 means it sometimes stops when the baseline would have been fine. The harness will report this as a false-stop count.
- Tuning log (all values stay `assumed`): (1) heat parameters moved from the first guess (h_off_ratio 0.25, heat_full 70) to 0.15 and 90, because with the first guess the loco protection derate always saved the baseline and no case was unsafe. (2) Uncertainty ranges were made roughly symmetric at about plus or minus 25 to 33 percent: leak 0.10 to 0.20 bar/min, h_off_ratio 0.12 to 0.20. The first ranges were lopsided (leak up to 0.30) and made the advisor stop in 34 cases the baseline survived. (3) Default section length is 12 km at 40 km/h (18 minutes), a plausible mainline spacing, up from 9 km.
- The wrong-sensor check fires only when the observed motor temperature is exactly flat for 8 samples while the model says it should be changing by more than 0.05 C/s. It then assumes the temperature is 5 C below the trip. A slope-based check was tried and rejected because it fired by chance when the true trend reversed.

## Harness result (seed 1, 144 cases per policy, advisor given the true fault set)
Baseline unsafe in 44, advisor unsafe in 0, 44 cases saved, 8 stops the baseline did not need (6 are a dead temperature sensor with a heating motor, 2 are a cautious 5th percentile), 0 failed properties. These come from our model with assumed parameters. Regenerate with `make harness`.

## Sensitivity (M3)
`python -m failover.core.sensitivity` (also run by `make harness`) moves each assumed parameter by plus and minus 20 percent, one at a time, and records the minutes to the first limit under the advisor's load plan. In the hard case (hot climb, standby stuck) the most sensitive assumptions are the motor trip temperature (swing 8.4 minutes), the motor heat at full load (5.1) and the motor heat capacity (3.5). For a failed compressor on a cool flat run they are the brake-air minimum (16.0) and the leak rate (8.3). **Ask the mentor for the trip temperature and the brake-air minimum first.** Output: `outputs/sensitivity.json`, committed copy in `demo_outputs/`.
