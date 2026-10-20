# Exemples reproductibles

Huit dates uniques par instrument : deux gains extrêmes, deux pertes extrêmes, première demi-séance, première ex-date, première ambiguïté si disponible sinon premier SHORT, dernier trade ; compléter avec les premières dates si doublon. Sélection descriptive non aléatoire.



## SPY

| date | direction | quantity | entry_reference | stop_price | target_price | exit_reference | exit_reason | net_pnl |
|---|---|---|---|---|---|---|---|---|
| 2016-01-04 | SHORT | 499 | 200.070 | 200.530 | 195.470 | 200.530 | stop_intrabar | -245.786 |
| 2016-03-18 | SHORT | 494 | 204.110 | 204.260 | 202.610 | 204.260 | stop_intrabar | -90.239 |
| 2016-11-25 | SHORT | 440 | 221.090 | 221.170 | 220.290 | 221.170 | stop_intrabar | -49.782 |
| 2020-02-28 | LONG | 302 | 291.540 | 288.030 | 326.640 | 288.030 | stop_intrabar | -1068.174 |
| 2020-03-17 | SHORT | 386 | 244.775 | 247.450 | 218.029 | 247.450 | stop_intrabar | -1045.442 |
| 2020-03-26 | LONG | 403 | 250.870 | 249.050 | 269.070 | 261.130 | eod_open | 4123.899 |
| 2022-10-13 | LONG | 301 | 349.880 | 348.110 | 367.580 | 366.160 | eod_open | 4892.153 |
| 2026-10-16 | SHORT | 129 | 772.260 | 773.250 | 762.360 | 762.360 | target_intrabar | 1270.850 |

2016-01-04 : 2016-01-04 09:35:00-05:00 → 2016-01-04 15:49:00-05:00, SHORT 499 actions ; mouvement -229.540000 − friction 9.980000 − commissions 3.493000 − emprunt 2.773054 = **-245.786054 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -234.530/733.530 USD.

2016-03-18 : 2016-03-18 09:35:00-04:00 → 2016-03-18 09:36:00-04:00, SHORT 494 actions ; mouvement -74.100000 − friction 9.880000 − commissions 3.458000 − emprunt 2.800706 = **-90.238706 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -79.040/0.000 USD.

2016-11-25 : 2016-11-25 09:35:00-05:00 → 2016-11-25 09:43:00-05:00, SHORT 440 actions ; mouvement -35.200000 − friction 8.800000 − commissions 3.080000 − emprunt 2.702089 = **-49.782089 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -39.600/30.800 USD.

2020-02-28 : 2020-02-28 09:35:00-05:00 → 2020-02-28 09:55:00-05:00, LONG 302 actions ; mouvement -1060.020000 − friction 6.040000 − commissions 2.114000 − emprunt 0.000000 = **-1068.174000 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -1063.040/498.300 USD.

2020-03-17 : 2020-03-17 09:35:00-04:00 → 2020-03-17 11:09:00-04:00, SHORT 386 actions ; mouvement -1032.395600 − friction 7.720000 − commissions 2.702000 − emprunt 2.624429 = **-1045.442029 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -1036.256/2970.424 USD.

2020-03-26 : 2020-03-26 09:35:00-04:00 → 2020-03-26 15:59:00-04:00, LONG 403 actions ; mouvement 4134.780000 − friction 8.060000 − commissions 2.821000 − emprunt 0.000000 = **4123.899000 USD**. Sortie bar_open ; MAE/MFE partiellement observées -442.897/4803.760 USD.

2022-10-13 : 2022-10-13 09:35:00-04:00 → 2022-10-13 15:59:00-04:00, LONG 301 actions ; mouvement 4900.280000 − friction 6.020000 − commissions 2.107000 − emprunt 0.000000 = **4892.153000 USD**. Sortie bar_open ; MAE/MFE partiellement observées -409.360/5303.620 USD.

2026-10-16 : 2026-10-16 09:35:00-04:00 → 2026-10-16 14:04:00-04:00, SHORT 129 actions ; mouvement 1277.100000 − friction 2.580000 − commissions 0.903000 − emprunt 2.767229 = **1270.849771 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -47.730/1275.810 USD.



## QQQ

| date | direction | quantity | entry_reference | stop_price | target_price | exit_reference | exit_reason | net_pnl |
|---|---|---|---|---|---|---|---|---|
| 2016-03-18 | SHORT | 957 | 107.370 | 107.555 | 105.520 | 107.555 | stop_intrabar | -205.738 |
| 2016-11-25 | SHORT | 908 | 118.470 | 118.650 | 116.670 | 118.650 | stop_intrabar | -190.944 |
| 2022-02-24 | LONG | 352 | 321.650 | 318.260 | 355.550 | 340.220 | eod_open | 6527.136 |
| 2022-10-13 | LONG | 539 | 255.590 | 254.260 | 268.890 | 268.890 | target_intrabar | 7154.147 |
| 2022-11-04 | SHORT | 585 | 263.950 | 266.390 | 239.550 | 266.390 | stop_intrabar | -1447.484 |
| 2022-11-15 | LONG | 510 | 292.200 | 292.170 | 292.500 | 292.170 | stop_intrabar | -29.070 |
| 2022-12-28 | LONG | 538 | 264.985 | 262.220 | 292.635 | 262.220 | stop_intrabar | -1502.096 |
| 2026-10-16 | SHORT | 204 | 724.210 | 725.960 | 706.710 | 710.370 | eod_open | 2813.748 |

2016-03-18 : 2016-03-18 09:35:00-04:00 → 2016-03-18 11:09:00-04:00, SHORT 957 actions ; mouvement -177.045000 − friction 19.140000 − commissions 6.699000 − emprunt 2.853987 = **-205.737987 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -186.615/535.920 USD.

2016-11-25 : 2016-11-25 09:35:00-05:00 → 2016-11-25 09:48:00-05:00, SHORT 908 actions ; mouvement -163.440000 − friction 18.160000 − commissions 6.356000 − emprunt 2.987824 = **-190.943824 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -172.520/36.320 USD.

2022-02-24 : 2022-02-24 09:35:00-05:00 → 2022-02-24 15:59:00-05:00, LONG 352 actions ; mouvement 6536.640000 − friction 7.040000 − commissions 2.464000 − emprunt 0.000000 = **6527.136000 USD**. Sortie bar_open ; MAE/MFE partiellement observées -288.640/6821.760 USD.

2022-10-13 : 2022-10-13 09:35:00-04:00 → 2022-10-13 11:40:00-04:00, LONG 539 actions ; mouvement 7168.700000 − friction 10.780000 − commissions 3.773000 − emprunt 0.000000 = **7154.147000 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -625.240/7163.310 USD.

2022-11-04 : 2022-11-04 09:35:00-04:00 → 2022-11-04 10:41:00-04:00, SHORT 585 actions ; mouvement -1427.400000 − friction 11.700000 − commissions 4.095000 − emprunt 4.289025 = **-1447.484025 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -1433.250/1971.450 USD.

2022-11-15 : 2022-11-15 09:35:00-05:00 → 2022-11-15 09:35:00-05:00, LONG 510 actions ; mouvement -15.300000 − friction 10.200000 − commissions 3.570000 − emprunt 0.000000 = **-29.070000 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -20.400/0.000 USD.

2022-12-28 : 2022-12-28 09:35:00-05:00 → 2022-12-28 10:55:00-05:00, LONG 538 actions ; mouvement -1487.570000 − friction 10.760000 − commissions 3.766000 − emprunt 0.000000 = **-1502.096000 USD**. Sortie intrabar_minute_unknown ; MAE/MFE partiellement observées -1492.950/255.550 USD.

2026-10-16 : 2026-10-16 09:35:00-04:00 → 2026-10-16 15:59:00-04:00, SHORT 204 actions ; mouvement 2823.360000 − friction 4.080000 − commissions 1.428000 − emprunt 4.103800 = **2813.748200 USD**. Sortie bar_open ; MAE/MFE partiellement observées -61.200/3461.880 USD.
