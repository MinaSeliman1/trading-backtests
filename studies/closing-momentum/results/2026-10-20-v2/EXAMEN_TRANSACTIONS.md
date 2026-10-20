# Examen reproductible de transactions

Sélection déterministe : deux plus gros gains, deux plus grosses pertes, première ex-date, première demi-séance, premier SHORT et dernière transaction de chaque instrument. Cette sélection illustrée ne constitue pas un échantillon aléatoire. Les cinq prix de référence sont relus dans les CSV bruts hachés ; les calculs complets sont audités séparément.



## SPY

| date | direction | Signal incluant overnight | quantity | entry_reference | exit_reference | commission | borrow_fee | net_pnl |
|---|---|---|---|---|---|---|---|---|
| 2016-01-05 | SHORT | -0.0348 % | 496 | 201.24 | 201.31 | 3.47 | 2.77 | -50.88 |
| 2016-03-18 | LONG | 0.3731 % | 489 | 204.58 | 204.41 | 3.42 | 0.00 | -96.33 |
| 2016-11-25 | LONG | 0.2469 % | 435 | 221.33 | 221.47 | 3.04 | 0.00 | 47.85 |
| 2020-03-06 | SHORT | -3.0088 % | 293 | 292.18 | 297.93 | 2.05 | 2.38 | -1 695.04 |
| 2020-03-13 | LONG | 3.4099 % | 325 | 258.97 | 268.80 | 2.27 | 0.00 | 3 185.98 |
| 2020-03-18 | SHORT | -4.5674 % | 372 | 231.83 | 238.08 | 2.60 | 2.40 | -2 337.44 |
| 2020-03-25 | SHORT | -0.4393 % | 338 | 253.54 | 246.22 | 2.37 | 2.38 | 2 460.93 |
| 2026-10-16 | SHORT | -0.0428 % | 85 | 763.20 | 763.54 | 0.70 | 1.80 | -33.10 |


2016-01-05 : signal -0.0348 %, SHORT, 496 actions ; mouvement -34.7200 USD − friction 9.9200 − commissions 3.4720 − emprunt 2.7724 = **-50.8844 USD net**. Entrée 2016-01-05 15:30:00-05:00 ; sortie 2016-01-05 15:59:00-05:00.


2016-03-18 : signal 0.3731 %, LONG, 489 actions ; mouvement -83.1300 USD − friction 9.7800 − commissions 3.4230 − emprunt 0.0000 = **-96.3330 USD net**. Entrée 2016-03-18 15:30:00-04:00 ; sortie 2016-03-18 15:59:00-04:00.


2016-11-25 : signal 0.2469 %, LONG, 435 actions ; mouvement 59.5950 USD − friction 8.7000 − commissions 3.0450 − emprunt 0.0000 = **47.8500 USD net**. Entrée 2016-11-25 12:30:00-05:00 ; sortie 2016-11-25 12:59:00-05:00.


2020-03-06 : signal -3.0088 %, SHORT, 293 actions ; mouvement -1684.7500 USD − friction 5.8600 − commissions 2.0510 − emprunt 2.3779 = **-1695.0389 USD net**. Entrée 2020-03-06 15:30:00-05:00 ; sortie 2020-03-06 15:59:00-05:00.


2020-03-13 : signal 3.4099 %, LONG, 325 actions ; mouvement 3194.7500 USD − friction 6.5000 − commissions 2.2750 − emprunt 0.0000 = **3185.9750 USD net**. Entrée 2020-03-13 15:30:00-04:00 ; sortie 2020-03-13 15:59:00-04:00.


2020-03-18 : signal -4.5674 %, SHORT, 372 actions ; mouvement -2325.0000 USD − friction 7.4400 − commissions 2.6040 − emprunt 2.3955 = **-2337.4395 USD net**. Entrée 2020-03-18 15:30:00-04:00 ; sortie 2020-03-18 15:59:00-04:00.


2020-03-25 : signal -0.4393 %, SHORT, 338 actions ; mouvement 2472.4362 USD − friction 6.7600 − commissions 2.3660 − emprunt 2.3804 = **2460.9298 USD net**. Entrée 2020-03-25 15:30:00-04:00 ; sortie 2020-03-25 15:59:00-04:00.


2026-10-16 : signal -0.0428 %, SHORT, 85 actions ; mouvement -28.9000 USD − friction 1.7000 − commissions 0.7000 − emprunt 1.8020 = **-33.1020 USD net**. Entrée 2026-10-16 15:30:00-04:00 ; sortie 2026-10-16 15:59:00-04:00.



## QQQ

| date | direction | Signal incluant overnight | quantity | entry_reference | exit_reference | commission | borrow_fee | net_pnl |
|---|---|---|---|---|---|---|---|---|
| 2016-01-05 | SHORT | -0.0548 % | 914 | 109.36 | 109.23 | 6.40 | 2.78 | 91.37 |
| 2016-03-18 | SHORT | -0.2167 % | 918 | 107.43 | 107.37 | 6.43 | 2.74 | 27.55 |
| 2016-11-25 | LONG | 0.2153 % | 816 | 118.72 | 118.78 | 5.71 | 0.00 | 26.93 |
| 2020-03-13 | LONG | 3.5092 % | 481 | 184.53 | 192.48 | 3.37 | 0.00 | 3 810.96 |
| 2020-03-18 | SHORT | -2.9504 % | 553 | 169.09 | 173.49 | 3.87 | 2.60 | -2 450.73 |
| 2020-03-20 | LONG | 1.1702 % | 510 | 174.54 | 170.77 | 3.57 | 0.00 | -1 936.47 |
| 2020-03-25 | SHORT | -0.7182 % | 479 | 187.07 | 181.81 | 3.35 | 2.49 | 2 501.72 |
| 2026-10-16 | SHORT | -0.9779 % | 91 | 710.74 | 710.37 | 0.70 | 1.80 | 29.35 |


2016-01-05 : signal -0.0548 %, SHORT, 914 actions ; mouvement 118.8200 USD − friction 18.2800 − commissions 6.3980 − emprunt 2.7763 = **91.3657 USD net**. Entrée 2016-01-05 15:30:00-05:00 ; sortie 2016-01-05 15:59:00-05:00.


2016-03-18 : signal -0.2167 %, SHORT, 918 actions ; mouvement 55.0800 USD − friction 18.3600 − commissions 6.4260 − emprunt 2.7392 = **27.5548 USD net**. Entrée 2016-03-18 15:30:00-04:00 ; sortie 2016-03-18 15:59:00-04:00.


2016-11-25 : signal 0.2153 %, LONG, 816 actions ; mouvement 48.9600 USD − friction 16.3200 − commissions 5.7120 − emprunt 0.0000 = **26.9280 USD net**. Entrée 2016-11-25 12:30:00-05:00 ; sortie 2016-11-25 12:59:00-05:00.


2020-03-13 : signal 3.5092 %, LONG, 481 actions ; mouvement 3823.9500 USD − friction 9.6200 − commissions 3.3670 − emprunt 0.0000 = **3810.9630 USD net**. Entrée 2020-03-13 15:30:00-04:00 ; sortie 2020-03-13 15:59:00-04:00.


2020-03-18 : signal -2.9504 %, SHORT, 553 actions ; mouvement -2433.2000 USD − friction 11.0600 − commissions 3.8710 − emprunt 2.5973 = **-2450.7283 USD net**. Entrée 2020-03-18 15:30:00-04:00 ; sortie 2020-03-18 15:59:00-04:00.


2020-03-20 : signal 1.1702 %, LONG, 510 actions ; mouvement -1922.7000 USD − friction 10.2000 − commissions 3.5700 − emprunt 0.0000 = **-1936.4700 USD net**. Entrée 2020-03-20 15:30:00-04:00 ; sortie 2020-03-20 15:59:00-04:00.


2020-03-25 : signal -0.7182 %, SHORT, 479 actions ; mouvement 2517.1450 USD − friction 9.5800 − commissions 3.3530 − emprunt 2.4889 = **2501.7231 USD net**. Entrée 2020-03-25 15:30:00-04:00 ; sortie 2020-03-25 15:59:00-04:00.


2026-10-16 : signal -0.9779 %, SHORT, 91 actions ; mouvement 33.6700 USD − friction 1.8200 − commissions 0.7000 − emprunt 1.7966 = **29.3534 USD net**. Entrée 2026-10-16 15:30:00-04:00 ; sortie 2026-10-16 15:59:00-04:00.
