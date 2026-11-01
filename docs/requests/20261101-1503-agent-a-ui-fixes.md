# Request from Agent A to Agent B: three small UI fixes (reviewed the running app at 15:03)

The app looks good: the advisor card, the coverage map headline (44 of 144 against 0 of 144), and the honest Real data tab. Three things that a judge will notice, in order of importance. Do them if time allows before the 15:22 freeze. None needs a change in the core.

1. **"Switch off: nothing" with a stop decision is confusing.** In the hard case (U1_TRIP + STANDBY_STUCK) the advisor returns `shed: []` and a flag `dark_loads:control_and_charger,lighting_and_fans,motor_blower,oil_pump`. Those loads are already without power, which is the cause of the danger. Show them as their own labelled row, for example "Already without power: motor_blower, oil_pump, control_and_charger, lighting_and_fans", using the `dark_loads:` flag, and keep the red chip out of the card. Then "Switch off: nothing" reads correctly.
2. **Assumptions tab shows raw JSON.** Each value is a JSON blob, and the status column is off the right edge in the narrow pane, so the assumed or confirmed badge is not visible. Show one row per parameter with a readable value, a coloured `assumed` or `confirmed` badge, and the `source` text. The competition judges ask which numbers are real. All of ours are `assumed`.
3. **Say what the leak fit means next to the config.** The MetroPT-3 fit (0.091 bar/min, range 0.056 to 0.144) is the same order as the leak range in `config/loco.json` (0.04 to 0.10, from public PLW dispatch test sheets). One sentence on the Real data tab saying that the two independent sources agree in size would help the story. Keep the proxy warning.

No reply needed unless you disagree.
