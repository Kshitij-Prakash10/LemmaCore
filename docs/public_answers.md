# What public sources say about the five mentor questions (14:45, Agent A)

Searched on 1 Nov 2026. Everything below is from public web pages, several of them unofficial copies of Indian Railways handbooks. Nothing here is confirmed by a mentor. Values used in `config/loco.json` stay `assumed` until a human flips them.

## 1. Motor trip temperature and heating with the blower off
- **Found:** the 6FRA 6068 traction motor (WAG-9 and WAP-7) is a forced-air-cooled, 6-pole asynchronous motor. Temperature is read by two resistance elements (PT-100) in a stator tooth. The loco logs "Motor temperature above limit" and "Temperature difference motor bogie > limit". Patents describe how a blower failure or duct breach can push motor temperature past limits, and how controllers detect loss of cooling air by comparing a modelled temperature with one estimated from winding resistance.
- **Not found:** the numeric trip temperature, the insulation class, or the heat-up time with the blower off. An 84 C, 10 s trip in one WAG-9 handbook is for the transformer, not the motor.
- **Status:** `limits.motor_temp_trip_c` (180 C) and the `thermal.motor` values stay assumed. This is the single most sensitive assumption (swing 8.4 minutes in the hard case). Ask the mentor.
- Sources: [6FRA 6068 pamphlet](https://st2.indiarailinfo.com/kjfdsuiemjvcya0/0/3/3/9/1418339/0/pamphleton3phasetractionmotor6fra6068wag9wap717773.pdf), [WAG-9 handbook copy](https://www.scribd.com/document/434794540/1353435608915-g-9-pdf), [US6847187 on loss of cooling air](https://patents.google.com/patent/US6847187).

## 2. Brake-air minimum pressure and leak rate
- **Found:** dispatch test sheets for 3-phase locos from Patiala Locomotive Works give a main reservoir leakage limit of under 1 kg/cm2 in 15 minutes (auto brake in full service), with recorded values of 0.6 and 0.7 kg/cm2 in 15 minutes. That is about 0.067 per minute at the limit and 0.04 to 0.047 per minute as measured. Brake pipe leakage limit: 0.15 kg/cm2 in 5 minutes.
- **Applied:** `air.leak_bar_per_min` is now min 0.04, nominal 0.05, max 0.10 (maximum is our guess for an aged loco). It was 0.10 to 0.20 before, which was about three times the test limit. The harness headline did not change.
- **Not found:** the main reservoir normal pressure, the compressor cut-in and cut-out, and the minimum safe pressure. `limits.brake_air_min_bar` (6.0) and `air.normal_bar` (9.5) stay assumed. The minimum pressure is now the most sensitive assumption in the compressor case. Ask the mentor.
- Sources: [PLW dispatch test sheet example](https://plw.indianrailways.gov.in/uploads/39423.pdf) and the neighbouring sheets in the same folder.

## 3. Which loads run on the auxiliary converter
- **Found (3-phase WAG-9 handbook, unofficial copies):** there are three auxiliary converters, normally loaded equally. If one fails, the others share its load, and the auxiliary supply frequency drops from 50 Hz to about 37 Hz. Loads include oil cooling blowers, traction motor blowers, scavenging blowers, compressors, transformer and converter pumps, and the battery charger. The table that says which load is on which converter, and the kW values, were illegible.
- **Why it matters:** on 3-phase locos a lost converter slows the blowers and compressor (frequency falls) instead of switching loads off. Our model switches loads off (conventional locos with 2 x 130 kVA, the RDSO evidence). Add a frequency-derate mode if the mentor says our model should represent 3-phase locos. Until then say "conventional electric locos" and mention this limit.
- **Status:** load kW values stay assumed. Ask the mentor for a load list with kW.
- Sources: [WAG-9 handbook copy](https://www.scribd.com/document/434794540/1353435608915-g-9-pdf), [WAG-9 book](https://pdfcoffee.com/wag-9-book-english-pdf-free.html).

## 4. How the standby takes over and what the crew does
- **Found:** on 3-phase locos the remaining converters share the load. RDSO's May 2025 minutes record that on conventional locos the load did not shift in some cases (see CONTEXT.md). A 3-phase handbook fragment says "if any thing is abnormal, fail the loco". The traction motor blower speed is controlled by the control electronics from measured temperatures.
- **Not found:** a loco-pilot procedure for an auxiliary converter fault, or any speed restriction. Related Indian fault-code tables exist but we could not read the relevant part.
- **Status:** the crew step stays a question for the mentor.
- Sources: [3-phase loco handbook](https://st2.indiarailinfo.com/kjfdsuiemjvcya0/0/3/4/7/1572347/16526793/3pha10040366.pdf), [RDSO minutes](https://rdso.indianrailways.gov.in/uploads/files/250606A_signed%20merged%20MOM%20on%20SIV.pdf).

## 5. Would a pilot trust a minutes-left number
- **Found:** no study of train drivers and uncertainty displays. Related work: drivers over-trust advisory systems when the interface shows nothing about information quality or system status, and false alerts damaged driver trust in a railway grade-crossing warning pilot. This supports showing a cautious figure with a confidence flag, which we do, and keeping false stops low (we report them).
- **Status:** ask the mentor. Do not claim pilots will trust it.
- Sources: [arXiv 2407.13775](https://arxiv.org/abs/2407.13775v1), [PMC10782180](https://pmc.ncbi.nlm.nih.gov/articles/PMC10782180/).

## Summary
| Question | Answered by public sources? | Config change |
|---|---|---|
| 1 Motor trip temperature and heat-up | No | none |
| 2 Brake-air minimum and leak | Leak yes (test sheets), minimum no | leak range lowered |
| 3 Loads on the converter | Types yes, kW no, plus the 37 Hz behaviour | none |
| 4 Failover and crew action | Partly | none |
| 5 Pilot trust | No direct study | none |
