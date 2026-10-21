# Transactions contrôlées dans les archives originales

Huit dates uniques/instrument : deux plus gros gains et pertes en USD, première ex-date, première demi-séance, première sortie VWAP et dernier trade ; compléter avec premières dates si doublons. Échantillon déterministe, non aléatoire. Prefixes complets jusqu’à la sortie relus dans les pages gzip hachées.

## SPY

| date | direction | quantity | adr20 | vwap_at_signal | entry_reference | exit_reference | exit_reason | net_pnl |
|---|---|---|---|---|---|---|---|---|
| 2016-04-01 | SHORT | 487 | 1.714 | 204.669 | 205.160 | 206.874 | stop_intrabar | -850.399 |
| 2016-04-07 | LONG | 484 | 1.748 | 205.133 | 204.540 | 204.710 | vwap_next_open | 69.212 |
| 2016-06-17 | LONG | 479 | 1.461 | 206.838 | 206.465 | 206.600 | vwap_next_open | 51.684 |
| 2018-04-02 | LONG | 253 | 3.934 | 261.762 | 260.670 | 256.736 | stop_intrabar | -1002.258 |
| 2018-12-07 | LONG | 234 | 4.219 | 269.521 | 268.270 | 264.051 | stop_intrabar | -993.484 |
| 2020-02-28 | LONG | 226 | 4.090 | 289.021 | 286.410 | 289.060 | vwap_next_open | 592.798 |
| 2021-02-26 | LONG | 208 | 4.516 | 381.928 | 378.490 | 381.620 | vwap_next_open | 645.424 |
| 2026-10-05 | SHORT | 117 | 5.371 | 771.087 | 772.680 | 774.480 | eod_open | -216.270 |

2016-04-01 SHORT 487 actions, 2016-04-01 10:30:00-04:00 → 2016-04-01 15:34:00-04:00 (intrabar_minute_unknown) : mouvement -834.474500 − friction 9.740000 − commissions 3.409000 − emprunt 2.775224 = **-850.398724 USD net**. Taille fondée sur close10:29=205.170000, ADR20=1.713500, stop=206.873500.

2016-04-07 LONG 484 actions, 2016-04-07 10:30:00-04:00 → 2016-04-07 13:15:00-04:00 (bar_open) : mouvement 82.280000 − friction 9.680000 − commissions 3.388000 − emprunt 0.000000 = **69.212000 USD net**. Taille fondée sur close10:29=204.540000, ADR20=1.747750, stop=202.792250.

2016-06-17 LONG 479 actions, 2016-06-17 10:30:00-04:00 → 2016-06-17 12:11:00-04:00 (bar_open) : mouvement 64.617100 − friction 9.580000 − commissions 3.353000 − emprunt 0.000000 = **51.684100 USD net**. Taille fondée sur close10:29=206.470000, ADR20=1.461265, stop=205.003735.

2018-04-02 LONG 253 actions, 2018-04-02 10:30:00-04:00 → 2018-04-02 11:41:00-04:00 (intrabar_minute_unknown) : mouvement -995.427235 − friction 5.060000 − commissions 1.771000 − emprunt 0.000000 = **-1002.258235 USD net**. Taille fondée sur close10:29=260.670000, ADR20=3.934495, stop=256.735505.

2018-12-07 LONG 234 actions, 2018-12-07 10:30:00-05:00 → 2018-12-07 14:00:00-05:00 (intrabar_minute_unknown) : mouvement -987.166440 − friction 4.680000 − commissions 1.638000 − emprunt 0.000000 = **-993.484440 USD net**. Taille fondée sur close10:29=268.263300, ADR20=4.218660, stop=264.051340.

2020-02-28 LONG 226 actions, 2020-02-28 10:30:00-05:00 → 2020-02-28 10:53:00-05:00 (bar_open) : mouvement 598.900000 − friction 4.520000 − commissions 1.582000 − emprunt 0.000000 = **592.798000 USD net**. Taille fondée sur close10:29=286.420000, ADR20=4.089915, stop=282.320085.

2021-02-26 LONG 208 actions, 2021-02-26 10:30:00-05:00 → 2021-02-26 10:43:00-05:00 (bar_open) : mouvement 651.040000 − friction 4.160000 − commissions 1.456000 − emprunt 0.000000 = **645.424000 USD net**. Taille fondée sur close10:29=378.530000, ADR20=4.515805, stop=373.974195.

2026-10-05 SHORT 117 actions, 2026-10-05 10:30:00-04:00 → 2026-10-05 15:59:00-04:00 (bar_open) : mouvement -210.600000 − friction 2.340000 − commissions 0.819000 − emprunt 2.511178 = **-216.270178 USD net**. Taille fondée sur close10:29=772.670000, ADR20=5.370695, stop=778.050695.

## QQQ

| date | direction | quantity | adr20 | vwap_at_signal | entry_reference | exit_reference | exit_reason | net_pnl |
|---|---|---|---|---|---|---|---|---|
| 2016-04-01 | SHORT | 889 | 1.124 | 108.815 | 109.190 | 110.314 | stop_intrabar | -1026.104 |
| 2016-04-05 | SHORT | 861 | 1.149 | 109.123 | 109.480 | 109.150 | vwap_next_open | 258.265 |
| 2016-06-17 | LONG | 935 | 0.922 | 107.004 | 106.580 | 106.725 | vwap_next_open | 110.330 |
| 2017-07-03 | LONG | 567 | 1.728 | 137.929 | 137.460 | 136.230 | eod_open | -712.719 |
| 2018-02-05 | SHORT | 568 | 1.678 | 163.967 | 165.515 | 164.290 | vwap_next_open | 677.853 |
| 2018-04-02 | LONG | 306 | 3.135 | 158.405 | 157.360 | 154.225 | stop_intrabar | -967.653 |
| 2021-02-26 | LONG | 163 | 5.461 | 314.395 | 311.080 | 314.600 | vwap_next_open | 569.359 |
| 2026-10-08 | SHORT | 110 | 7.444 | 754.215 | 756.900 | 754.430 | vwap_next_open | 266.417 |

2016-04-01 SHORT 889 actions, 2016-04-01 10:30:00-04:00 → 2016-04-01 15:37:00-04:00 (intrabar_minute_unknown) : mouvement -999.404910 − friction 17.780000 − commissions 6.223000 − emprunt 2.696139 = **-1026.104049 USD net**. Taille fondée sur close10:29=109.190000, ADR20=1.124190, stop=110.314190.

2016-04-05 SHORT 861 actions, 2016-04-05 10:30:00-04:00 → 2016-04-05 10:57:00-04:00 (bar_open) : mouvement 284.130000 − friction 17.220000 − commissions 6.027000 − emprunt 2.618158 = **258.264842 USD net**. Taille fondée sur close10:29=109.485000, ADR20=1.149440, stop=110.629440.

2016-06-17 LONG 935 actions, 2016-06-17 10:30:00-04:00 → 2016-06-17 13:21:00-04:00 (bar_open) : mouvement 135.575000 − friction 18.700000 − commissions 6.545000 − emprunt 0.000000 = **110.330000 USD net**. Taille fondée sur close10:29=106.590000, ADR20=0.921865, stop=105.658135.

2017-07-03 LONG 567 actions, 2017-07-03 10:30:00-04:00 → 2017-07-03 12:59:00-04:00 (bar_open) : mouvement -697.410000 − friction 11.340000 − commissions 3.969000 − emprunt 0.000000 = **-712.719000 USD net**. Taille fondée sur close10:29=137.460000, ADR20=1.728100, stop=135.731900.

2018-02-05 SHORT 568 actions, 2018-02-05 10:30:00-05:00 → 2018-02-05 11:42:00-05:00 (bar_open) : mouvement 695.800000 − friction 11.360000 − commissions 3.976000 − emprunt 2.611301 = **677.852699 USD net**. Taille fondée sur close10:29=165.490000, ADR20=1.678490, stop=167.193490.

2018-04-02 LONG 306 actions, 2018-04-02 10:30:00-04:00 → 2018-04-02 14:02:00-04:00 (intrabar_minute_unknown) : mouvement -959.391090 − friction 6.120000 − commissions 2.142000 − emprunt 0.000000 = **-967.653090 USD net**. Taille fondée sur close10:29=157.360000, ADR20=3.135265, stop=154.224735.

2021-02-26 LONG 163 actions, 2021-02-26 10:30:00-05:00 → 2021-02-26 10:43:00-05:00 (bar_open) : mouvement 573.760000 − friction 3.260000 − commissions 1.141000 − emprunt 0.000000 = **569.359000 USD net**. Taille fondée sur close10:29=311.120000, ADR20=5.460790, stop=305.619210.

2026-10-08 SHORT 110 actions, 2026-10-08 10:30:00-04:00 → 2026-10-08 10:55:00-04:00 (bar_open) : mouvement 271.700000 − friction 2.200000 − commissions 0.770000 − emprunt 2.312719 = **266.417281 USD net**. Taille fondée sur close10:29=756.929600, ADR20=7.444145, stop=764.344145.
