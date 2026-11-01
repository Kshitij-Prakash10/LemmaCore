# Context: the competition, the problem and what we are building

This file is shared by both agents. Humans edit it. Agents read it and do not change it.

## 1. The competition

**Node Quest 2026.** Organised by the IEEE Industrial Electronics Society (IES) student branch at IIT (BHU), Varanasi, on 1 November 2026, in the Department of Electrical Engineering. Judges are a joint panel of IIT (BHU) faculty and an IEEE IES industrial panel.

**The challenge, verbatim:** "Identify one real problem in Indian Railways that matters to someone (an engineer, a driver, a maintenance worker, a station manager or a passenger) and build a working software solution for it."

**The prompt from the industry session by Banaras Locomotive Works (BLW):** "If this component fails during a journey, what should the system do next?" The BLW talk covered the electric loco power path (25 kV overhead supply, pantograph and vacuum circuit breaker, main transformer, converter or inverter, traction motors, wheels), plus control and monitoring, auxiliary supply (cooling, compressors, lighting, control loads) and protection. It named two design challenges: heat and cooling ("What happens if a fan fails?") and reliability and protection in vibration, dust, temperature swings and long duty cycles.

### Format

- **Phase 1, idea making (before lunch):** teams of 3 to 4 choose one real railway problem, define what goes wrong, who faces it and why it matters, plan the solution and the hard case it will handle. Mentors visit tables. The phase ends with a one or two sentence problem and solution shared with a mentor.
- **Phase 2, build (after lunch):** build a working software prototype. Simulated or made-up data is fine. No hardware is needed. A progress review checks that the solution runs and handles the hard case. The top 8 teams are selected to present.
- The event page also lists a schedule of problem reveal at 12:15 IST, build 13:30 to 15:30 and presentations 16:00 to 17:00. Plan for roughly 100 to 120 minutes of build, and confirm the real window with a volunteer.
- **Final round:** the top 8 teams present for 5 minutes, followed by 3 minutes of questions from the judges.

### What the team must show

1. **The problem:** what goes wrong, who faces it, why it matters (2 or 3 sentences).
2. **Working software:** a prototype that runs during the demo.
3. **The hard case:** one difficult or unusual situation the solution handles (a failure, wrong data, an emergency, many users at once).
4. **Next steps:** how it could be used in real railways.

### Rules

- Teams of 3 to 4 members. Any programming language or tool.
- Open-source code and AI assistants are allowed, **but we must disclose what we used.**
- **The software must run on our own laptop. It must not depend on the internet.**
- Simulated or made-up data is fine. No hardware is needed.

### Judging rubric (100 points)

| Criterion | Weight | What the judges look for |
|---|---|---|
| Problem selection | 20% | A real, specific railway problem for a named user. Not vague, not a copy of an existing app. |
| Idea and innovation | 20% | A clever, original approach and a thoughtful choice of what to build and what to leave out. |
| Understanding of the problem | 15% | Root cause, who is affected, how often, what it costs, what exists today and why it is not enough. |
| Solution design and the hard case | 15% | A clear plan and at least one difficult situation handled sensibly. |
| Working prototype | 10% | Something runs and shows the core idea. A working core beats a polished mock-up. |
| Ownership and reasoning (Q&A) | 10% | Every member can explain the idea, the logic and their own code or design choices, and answers "why" without reading from a screen. |
| Future scope and impact | 10% | A realistic path to real use: who adopts it, what it needs (data, hardware, approvals), how it scales. |

The judges say: "A sharp, real problem and a smart solution beat a big app that solves nothing specific."

Prizes are non-cash engineering gadgets (first, second and third) plus IEEE IES certificates. Every team that completes the challenge gets a certificate of participation.

## 2. The problem we chose (locked)

**Named users:** the loco pilot and assistant, who must decide within minutes, and the loco shed electricians and RDSO engineers, who test and diagnose converters.

**Problem in simple words.** A loco's auxiliary converter (static inverter, SIV) powers the cooling blowers, oil pumps, the brake-air compressor, the battery charger and the lights. It fails often. Many locos have two converters so one can cover the other, but sheds report that the cover does not always happen. The loco pilot is then in the middle of a section with no clear instruction on what to switch off or how long they can keep running before something overheats or the brake air drops.

## 3. Our solution (locked)

**Failover Guardian** has two parts:

1. **The advisor.** One screen for the loco pilot. It reads the fault and the conditions, then says what to switch off, what to keep on, how many minutes are left ("at least N minutes", a 5th percentile), the limiting factor (heat, brake air, battery or power), and whether to continue to the next station, stop at the next safe place, or stop now.
2. **The proof.** A fault-injection harness that tries every single and double converter fault, in four conditions, with and without the advisor, and records the outcome. It is the test that proves the advisor. It is not a second product.

**ML component (added by the team).** The advisor is physics-first. Machine learning supports it in three places:

- **Fault diagnosis:** a model that infers which faults are present from sensor windows, so the pilot does not need to know which unit failed. Trained on simulated scenarios with domain randomization.
- **Real-data calibration and anomaly detection:** the public MetroPT-3 dataset (real compressor sensor data from a metro train, maintenance-confirmed air-leak failures) is used to estimate brake-air leak behaviour and to demo an early-warning detector. It is a proxy from a metro train in Porto, not an Indian loco, and we say so.
- **Minutes-left surrogate (stretch):** a fast model with prediction intervals. It may never be more optimistic than the physics: the advisor uses the more cautious of the two.

## 4. Evidence we can quote (with trust level)

| Fact | Source | Trust |
|---|---|---|
| RDSO "expressed serious concern about high rate of failures" of 180 kVA SIVs on conventional electric locos (meeting 29 May 2025). | RDSO minutes (rdso.indianrailways.gov.in, file 250606A signed merged MOM on SIV) | High, primary |
| FY 2024-25 failures: AAL 243 of 607 units, ABB 32 of 67, Medha 84 of 413, Hind 93 of 219, Siemens 130 of 810. Sum 582 of 2,116, about 27 per 100 units a year. | Annexure-I of the same minutes | High for the table. Totals and column meaning are our reading. |
| Sheds reported load not shifting from SIV1 to SIV2 after a fault (Siemens 2x130 kVA) and not shifting when the front-panel MCB trips (Medha 2x130 kVA). Also frequent overvoltage trips, capacitor overheating from a loose terminal, a cracked blower fan base plate (ABB). | Same minutes | High, primary |
| Fault log holds 20 days while scheduled loco visits are 60 days apart. Makers did not share root-cause analyses. | Same minutes | High, primary |
| Older rule: in a block section try to resume traction within 20 minutes, else inform control. Do not switch off HQOP/HOBA before trying motor isolation. | Traction service document for older loco classes, found by search | Medium-low |
| An auxiliary converter fault left three coaches of a Vande Bharat without AC, lights and fans for about an hour (Oct 2019). | Scroll | Medium, news |
| Remote monitoring (REMMLOT) reports loco health. CLW specified an analytics system for 3-phase locos (April 2024). Deployment status unknown. Neither is a crew advisor, as far as we found. | IRIMEE slides, CLW documents | Medium |
| Locomotive controllers already estimate motor temperature from a thermal model and can derate or trip. Parallel auxiliary converters exist on EMUs. | US patents, an EMU paper | Medium |

**Scope warning.** The 2025 RDSO table is for conventional electric locos, not for the 3-phase locos BLW builds. 3-phase locos use IGBT auxiliary converters (a vendor lists 3 x 130 kVA), so the converter count must be a setting. Say "conventional electric locos" whenever the 27 per 100 figure is quoted.

## 5. Scope

- **Must have:** config, converter state machine, heat model, brake-air model, advisor with load search, fault harness with coverage map data, one-screen app, report tab.
- **Should have:** fault diagnosis classifier, MetroPT-3 calibration, what-if sliders, exportable test report.
- **Stretch:** battery model, 5th percentile Monte Carlo (build early if cheap), minutes-left surrogate, sensitivity view, Hindi and English labels, smart log retention.
- **Cut order:** log retention, Hindi labels, sensitivity view, surrogate, then the report. Never cut the advisor, the fault harness or the map.
- **Out of scope:** failure prediction, passenger features, cloud services, other railway problems, any claim of safety certification.

## 6. Assumptions policy

Nothing about the loco has been confirmed by a mentor yet. Every parameter in `config/loco.json` carries a `status` of `assumed` or `confirmed` and a `source`. The app must show these badges. A mentor will be asked: which loads run on the converter, how long the loco can run if the blowers stop and at what temperature protection trips, what the crew does today, how the standby takes over and when it fails to, and whether a pilot would trust a minutes-left figure. When answers arrive, a human edits `config/loco.json` (owner: Agent A) and flips the status.

## 7. The demo (what the judges will see)

1. Open the coverage map: 36 fault combinations by 4 conditions, coloured safe, controlled stop or unsafe, for the baseline and for the advisor.
2. Click a red baseline cell: hot day, climbing, unit 1 trips and the standby does not take over. The baseline passes a limit. The advisor says which two loads to shed, "at least N minutes", and whether to continue or stop. The chart stays under the limit.
3. Use "Auto-diagnose": feed a noisy sensor window and watch the classifier name the faults.
4. Stick the temperature sensor. The advisor flags the disagreement and shortens its estimate (the wrong-data hard case).
5. Show the real-data slide: the air model calibrated on MetroPT-3 and the anomaly detector's result.
6. Show the assumptions screen with every value tagged assumed or confirmed.

## 8. Definition of success

A stranger can run one command, see the coverage map and the advisor on a laptop with Wi-Fi off, and every number on screen can be traced to a config value, a test or an evaluation file. Each of the four team members can explain the idea and their own part.
