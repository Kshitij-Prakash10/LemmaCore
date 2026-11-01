# Data (owner: Agent B)

`data/raw/` is not committed. `data/processed/` holds small derived files that are committed.

## MetroPT-3 (real data, used as a proxy)

- Source: UCI Machine Learning Repository, dataset id 791, licence CC BY 4.0.
  Download URL used: `https://archive.ics.uci.edu/static/public/791/metropt+3+dataset.zip`
- Downloaded: 2026-11-01 14:26 IST, with curl, during setup. Nothing is fetched at run time.
- Citation: Davari, N., Veloso, B., Ribeiro, R. P., Pereira, P. M., Gama, J. (2021), DSAA 2021, doi 10.1109/DSAA53316.2021.9564181; Veloso et al. (2022), Scientific Data 9:764, doi 10.1038/s41597-022-01877-3.
- What it is: the air production unit (compressor) of a metro train in Porto. **Not an Indian loco.** We use it as a proxy for brake-air behaviour and to show we handle real sensor data.

| File | Size (bytes) | sha256 |
|---|---|---|
| `data/raw/metropt3.zip` | 218,381,995 | `aab991a970e58210de853bb8078ce0e63abb4d9412fdc5c79792dae3d8e1721a` |
| `data/raw/metropt3.csv` (unzipped from `MetroPT3(AirCompressor).csv`) | 218,300,507 | `db30ccb4ea402e3c8bf2c99db06e288d4f2a772f6928f9dbe26a920d69793e24` |
| `data/raw/Data Description_Metro.pdf` | 81,208 | (bundled description) |

### What we verified from the file itself

- 1,516,948 data rows plus a header (`wc -l` gives 1,516,949 lines).
- Columns: unnamed index, `timestamp`, TP2, TP3, H1, DV_pressure, Reservoirs, Oil_temperature, Motor_current, COMP, DV_eletric, Towers, MPG, LPS, Pressure_switch, Oil_level, Caudal_impulses (15 signals).
- First timestamp `2020-02-01 00:00:00`, last `2020-09-01 03:59:50`.
- Rows are 10 s apart, and the unnamed index steps by 10.
- **Disagreement:** the bundled PDF says 15,169,480 points at 1 Hz from February to August 2020. The file we downloaded has one tenth of that, at 10 s spacing, and runs into 1 September. We use the file as it is and treat the sample period as 10 s.

### Failure table

`data/processed/failures.json` transcribes the "Failure Information" table in the bundled PDF: four air-leak events on 2020-04-18, 2020-05-29/30, 2020-06-05 to 06-07 and 2020-07-15. The oddities in that table are noted in the file.
