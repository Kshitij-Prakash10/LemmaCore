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
- Tuning log: heat parameters were retuned from the first guess (h_off_ratio 0.15, heat_full 90 nominal) so that the hot-climb standby-stuck case on a 15 km section makes the baseline hit the motor limit while the advisor stops in time.
