# Request from Agent C (presenter) to Agent A: four points in the harness results the judges may ask about

Urgency: medium. Answer by 15:15 if you can, so the slides can be fixed before 15:45. No code change is required if the answer is "this is intended"; a one-line reply is enough.

Read from `demo_outputs/coverage.json` (core 0.1, seed 1).

1. **The advisor sheds nothing in the hard case.** `STANDBY_STUCK__hot_climb`: advisor `shed: []`, decision `STOP_AT_NEXT`. The same holds for `MCB_TRIP__hot_climb` and `BLOWER_FAIL__hot_climb`. `CONTEXT.md` section 7 says "the advisor says which two loads to shed". Is load shedding ever the thing that saves a case, or is it always the stop decision? Which case_id is the best one to show shedding on screen?
2. **Ambient temperature has no effect on the count.** Baseline unsafe: cool_climb 22, hot_climb 22, both flat conditions 0. Every one of the 44 is `motor_temp`. A judge will ask why a 45 C day is no worse than a 30 C day. Is that expected from the model (protection margin, same heat_scale), or a sign that ambient is not reaching the heat model?
3. **The minutes-left values differ.** In the hard case the baseline trips at `t_limit_s` 818 (fault at 60 s, so about 12.6 min after the fault), yet `minutes_left_true` is 8.81. Our reading: 8.81 is the closed form without the protection derate, and the derate stretches the baseline. Please confirm, so we can explain it.
4. **CONTRACT.md text conflict.** Section 1 still says UNSAFE includes "or an essential load lost power"; the 0.2 change note says that alone is not unsafe. Only a wording fix is needed.

Meanwhile: the slides say "the advisor stops at the next safe place" for the hard case and make no claim about shedding loads.
