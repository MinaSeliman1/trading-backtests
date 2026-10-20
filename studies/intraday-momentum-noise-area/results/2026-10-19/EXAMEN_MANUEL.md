# Examen des transactions historiques

Dix premières transactions de B, cinq par ETF, puis cas de couverture explicites. Sélection chronologique avant examen des gains ; les dix premières sont toutes LONG. Calculs scalaires indépendants du moteur, examinés pour cohérence des seuils, des horaires, des quantités et du P&L. Aucun prix fictif. Le contrôle exhaustif séparé couvre aussi tous les SHORT et retournements des 32 scénarios principaux.

## 1. SPY — 2024-05-01 — LONG (échantillon chronologique)

Entrée 2024-05-01 15:00:00-04:00, sortie 2024-05-01 15:59:00-04:00 ; motif `session_end`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 501,380000 ; clôture précédente 502,040000, référence ex-dividende 502,040000. Moyenne des 14 mouvements = 0,007156882.
- UB = 502,040000 × (1 + 0,007156882) = **505,633041** ; LB = 497,791683. VWAP HLC3 scalaire cumulé = **502,169578** ; prix de décision = **507,340000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 21 554 777 950,931 ; somme(volume) = 42 923 305 ; quotient = **502,169578**.
- Volatilité passée = 0,912109 % ; capital à l'ouverture 100 000,000000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **437**. Même quantité après les autres trades de cette séance.
- Sortie : aucun franchissement de sortie avant la fin ; liquidation à l'open de la dernière minute. Prix simulés après friction adverse : entrée **507,351000**, sortie **500,529000**.
- P&L = 437 × 1 × (500,529000 − 507,351000) − 3,059000 de commissions − 0,000000 d'emprunt = **-2 984,273000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 2. SPY — 2024-05-09 — LONG (échantillon chronologique)

Entrée 2024-05-09 11:00:00-04:00, sortie 2024-05-09 12:00:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 517,380000 ; clôture précédente 517,190000, référence ex-dividende 517,190000. Moyenne des 14 mouvements = 0,002504208.
- UB = 517,380000 × (1 + 0,002504208) = **518,675627** ; LB = 515,894849. VWAP HLC3 scalaire cumulé = **518,009878** ; prix de décision = **519,165000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 5 706 532 530,809 ; somme(volume) = 11 016 262 ; quotient = **518,009878**.
- Volatilité passée = 0,854594 % ; capital à l'ouverture 97 015,727000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **438**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 12:00 NY : prix 518,500000, UB 518,818870, LB 515,751658, VWAP 518,345124. Prix simulés après friction adverse : entrée **519,161000**, sortie **518,489000**.
- P&L = 438 × 1 × (518,489000 − 519,161000) − 3,066000 de commissions − 0,000000 d'emprunt = **-297,402000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 3. SPY — 2024-05-09 — LONG (échantillon chronologique)

Entrée 2024-05-09 13:00:00-04:00, sortie 2024-05-09 14:30:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 517,380000 ; clôture précédente 517,190000, référence ex-dividende 517,190000. Moyenne des 14 mouvements = 0,003345045.
- UB = 517,380000 × (1 + 0,003345045) = **519,110659** ; LB = 515,459976. VWAP HLC3 scalaire cumulé = **518,425710** ; prix de décision = **519,219900**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 9 801 183 835,143 ; somme(volume) = 18 905 667 ; quotient = **518,425710**.
- Volatilité passée = 0,854594 % ; capital à l'ouverture 97 015,727000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **438**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 14:30 NY : prix 519,480000, UB 519,591123, LB 514,979689, VWAP 518,608508. Prix simulés après friction adverse : entrée **519,211000**, sortie **519,489000**.
- P&L = 438 × 1 × (519,489000 − 519,211000) − 3,066000 de commissions − 0,000000 d'emprunt = **118,698000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 4. SPY — 2024-05-14 — LONG (échantillon chronologique)

Entrée 2024-05-14 10:30:00-04:00, sortie 2024-05-14 11:00:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 521,100000 ; clôture précédente 520,910000, référence ex-dividende 520,910000. Moyenne des 14 mouvements = 0,001690801.
- UB = 521,100000 × (1 + 0,001690801) = **521,981076** ; LB = 520,029245. VWAP HLC3 scalaire cumulé = **521,519389** ; prix de décision = **522,230000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 5 071 534 594,087 ; somme(volume) = 9 724 537 ; quotient = **521,519389**.
- Volatilité passée = 0,735247 % ; capital à l'ouverture 96 837,023000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **505**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 11:00 NY : prix 521,765000, UB 522,277863, LB 519,732566, VWAP 521,463661. Prix simulés après friction adverse : entrée **522,231000**, sortie **521,769000**.
- P&L = 505 × 1 × (521,769000 − 522,231000) − 3,535000 de commissions − 0,000000 d'emprunt = **-236,845000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 5. SPY — 2024-05-14 — LONG (échantillon chronologique)

Entrée 2024-05-14 15:00:00-04:00, sortie 2024-05-14 15:59:00-04:00 ; motif `session_end`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 521,100000 ; clôture précédente 520,910000, référence ex-dividende 520,910000. Moyenne des 14 mouvements = 0,004130075.
- UB = 521,100000 × (1 + 0,004130075) = **523,252182** ; LB = 518,758603. VWAP HLC3 scalaire cumulé = **521,617324** ; prix de décision = **523,268700**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 16 058 528 675,223 ; somme(volume) = 30 786 034 ; quotient = **521,617324**.
- Volatilité passée = 0,735247 % ; capital à l'ouverture 96 837,023000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **505**. Même quantité après les autres trades de cette séance.
- Sortie : aucun franchissement de sortie avant la fin ; liquidation à l'open de la dernière minute. Prix simulés après friction adverse : entrée **523,256000**, sortie **523,689000**.
- P&L = 505 × 1 × (523,689000 − 523,256000) − 3,535000 de commissions − 0,000000 d'emprunt = **215,130000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 6. QQQ — 2024-05-01 — LONG (échantillon chronologique)

Entrée 2024-05-01 15:00:00-04:00, sortie 2024-05-01 15:30:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 423,150000 ; clôture précédente 424,530000, référence ex-dividende 424,530000. Moyenne des 14 mouvements = 0,010495125.
- UB = 424,530000 × (1 + 0,010495125) = **428,985496** ; LB = 418,708988. VWAP HLC3 scalaire cumulé = **423,331248** ; prix de décision = **429,150000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 13 409 136 239,970 ; somme(volume) = 31 675 281 ; quotient = **423,331248**.
- Volatilité passée = 1,338464 % ; capital à l'ouverture 100 000,000000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **353**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 15:30 NY : prix 428,358100, UB 429,090527, LB 418,604297, VWAP 424,214633. Prix simulés après friction adverse : entrée **429,161000**, sortie **428,349000**.
- P&L = 353 × 1 × (428,349000 − 429,161000) − 2,471000 de commissions − 0,000000 d'emprunt = **-289,107000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 7. QQQ — 2024-05-10 — LONG (échantillon chronologique)

Entrée 2024-05-10 10:00:00-04:00, sortie 2024-05-10 10:30:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 442,540000 ; clôture précédente 441,030000, référence ex-dividende 441,030000. Moyenne des 14 mouvements = 0,002329199.
- UB = 442,540000 × (1 + 0,002329199) = **443,570764** ; LB = 440,002753. VWAP HLC3 scalaire cumulé = **443,384798** ; prix de décision = **443,800000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 1 644 649 446,645 ; somme(volume) = 3 709 305 ; quotient = **443,384798**.
- Volatilité passée = 1,057979 % ; capital à l'ouverture 99 710,893000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **425**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 10:30 NY : prix 441,515000, UB 443,944004, LB 439,630786, VWAP 442,994621. Prix simulés après friction adverse : entrée **443,801000**, sortie **441,549000**.
- P&L = 425 × 1 × (441,549000 − 443,801000) − 2,975000 de commissions − 0,000000 d'emprunt = **-960,075000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 8. QQQ — 2024-05-14 — LONG (échantillon chronologique)

Entrée 2024-05-14 10:30:00-04:00, sortie 2024-05-14 11:00:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 442,650000 ; clôture précédente 443,100000, référence ex-dividende 443,100000. Moyenne des 14 mouvements = 0,002480226.
- UB = 443,100000 × (1 + 0,002480226) = **444,198988** ; LB = 441,552128. VWAP HLC3 scalaire cumulé = **443,381064** ; prix de décision = **444,815000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 3 702 592 799,742 ; somme(volume) = 8 350 814 ; quotient = **443,381064**.
- Volatilité passée = 0,996377 % ; capital à l'ouverture 98 750,818000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **447**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 11:00 NY : prix 444,219700, UB 444,245934, LB 441,505230, VWAP 443,463659. Prix simulés après friction adverse : entrée **444,821000**, sortie **444,209000**.
- P&L = 447 × 1 × (444,209000 − 444,821000) − 3,129000 de commissions − 0,000000 d'emprunt = **-276,693000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 9. QQQ — 2024-05-14 — LONG (échantillon chronologique)

Entrée 2024-05-14 11:30:00-04:00, sortie 2024-05-14 12:00:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 442,650000 ; clôture précédente 443,100000, référence ex-dividende 443,100000. Moyenne des 14 mouvements = 0,003164333.
- UB = 443,100000 × (1 + 0,003164333) = **444,502116** ; LB = 441,249308. VWAP HLC3 scalaire cumulé = **443,603589** ; prix de décision = **444,690000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 5 667 306 010,208 ; somme(volume) = 12 775 609 ; quotient = **443,603589**.
- Volatilité passée = 0,996377 % ; capital à l'ouverture 98 750,818000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **447**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 12:00 NY : prix 443,770000, UB 444,562449, LB 441,189036, VWAP 443,630719. Prix simulés après friction adverse : entrée **444,696000**, sortie **443,764000**.
- P&L = 447 × 1 × (443,764000 − 444,696000) − 3,129000 de commissions − 0,000000 d'emprunt = **-419,733000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 10. QQQ — 2024-05-14 — LONG (échantillon chronologique)

Entrée 2024-05-14 14:30:00-04:00, sortie 2024-05-14 15:59:00-04:00 ; motif `session_end`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 442,650000 ; clôture précédente 443,100000, référence ex-dividende 443,100000. Moyenne des 14 mouvements = 0,004225215.
- UB = 443,100000 × (1 + 0,004225215) = **444,972193** ; LB = 440,779709. VWAP HLC3 scalaire cumulé = **443,779444** ; prix de décision = **445,139900**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 9 224 511 799,227 ; somme(volume) = 20 786 253 ; quotient = **443,779444**.
- Volatilité passée = 0,996377 % ; capital à l'ouverture 98 750,818000 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **447**. Même quantité après les autres trades de cette séance.
- Sortie : aucun franchissement de sortie avant la fin ; liquidation à l'open de la dernière minute. Prix simulés après friction adverse : entrée **445,141000**, sortie **446,289000**.
- P&L = 447 × 1 × (446,289000 − 445,141000) − 3,129000 de commissions − 0,000000 d'emprunt = **510,027000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 11. SPY — 2024-05-22 — SHORT (premier SHORT)

Entrée 2024-05-22 14:30:00-04:00, sortie 2024-05-22 15:59:00-04:00 ; motif `session_end`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 530,660000 ; clôture précédente 531,320000, référence ex-dividende 531,320000. Moyenne des 14 mouvements = 0,002452297.
- UB = 531,320000 × (1 + 0,002452297) = **532,622954** ; LB = 529,358664. VWAP HLC3 scalaire cumulé = **530,321525** ; prix de décision = **527,810000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 10 139 344 514,311 ; somme(volume) = 19 119 240 ; quotient = **530,321525**.
- Volatilité passée = 0,491535 % ; capital à l'ouverture 97 400,915200 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **734**. Même quantité après les autres trades de cette séance.
- Sortie : aucun franchissement de sortie avant la fin ; liquidation à l'open de la dernière minute. Prix simulés après friction adverse : entrée **527,819000**, sortie **529,236000**.
- P&L = 734 × -1 × (529,236000 − 527,819000) − 5,138000 de commissions − 10,761643 d'emprunt = **-1 055,977643 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 12. SPY — 2024-12-18 — LONG (retournement)

Entrée 2024-12-18 14:00:00-05:00, sortie 2024-12-18 14:30:00-05:00 ; motif `reversal`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 603,980000 ; clôture précédente 604,240000, référence ex-dividende 604,240000. Moyenne des 14 mouvements = 0,001754818.
- UB = 604,240000 × (1 + 0,001754818) = **605,300332** ; LB = 602,920125. VWAP HLC3 scalaire cumulé = **605,318634** ; prix de décision = **605,470000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 13 045 572 353,702 ; somme(volume) = 21 551 579 ; quotient = **605,318634**.
- Volatilité passée = 0,440987 % ; capital à l'ouverture 109 320,732673 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **724**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 14:30 NY : prix 600,080000, UB 605,431033, LB 602,789479, VWAP 604,216948. Prix simulés après friction adverse : entrée **605,541000**, sortie **600,099000**.
- P&L = 724 × 1 × (600,099000 − 605,541000) − 5,068000 de commissions − 0,000000 d'emprunt = **-3 945,076000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 13. SPY — 2024-07-03 — LONG (demi-séance)

Entrée 2024-07-03 11:30:00-04:00, sortie 2024-07-03 12:59:00-04:00 ; motif `session_end`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 548,680000 ; clôture précédente 548,970000, référence ex-dividende 548,970000. Moyenne des 14 mouvements = 0,001725381.
- UB = 548,970000 × (1 + 0,001725381) = **549,917182** ; LB = 547,733318. VWAP HLC3 scalaire cumulé = **549,576367** ; prix de décision = **550,030000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 6 022 974 481,367 ; somme(volume) = 10 959 304 ; quotient = **549,576367**.
- Volatilité passée = 0,424758 % ; capital à l'ouverture 99 095,277743 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **722**. Même quantité après les autres trades de cette séance.
- Sortie : aucun franchissement de sortie avant la fin ; liquidation à l'open de la dernière minute. Prix simulés après friction adverse : entrée **550,031000**, sortie **551,329000**.
- P&L = 722 × 1 × (551,329000 − 550,031000) − 5,054000 de commissions − 0,000000 d'emprunt = **932,102000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 14. SPY — 2024-06-21 — SHORT (ex-dividende)

Entrée 2024-06-21 10:00:00-04:00, sortie 2024-06-21 10:30:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 544,470000 ; clôture précédente 546,950000, référence ex-dividende 545,190976. Moyenne des 14 mouvements = 0,001078748.
- UB = 545,190976 × (1 + 0,001078748) = **545,779100** ; LB = 543,882654. VWAP HLC3 scalaire cumulé = **544,011944** ; prix de décision = **543,850000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 2 819 184 682,333 ; somme(volume) = 5 182 211 ; quotient = **544,011944**.
- Volatilité passée = 0,433340 % ; capital à l'ouverture 97 284,689328 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **714**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 10:30 NY : prix 544,320000, UB 546,022817, LB 543,639259, VWAP 544,091851. Prix simulés après friction adverse : entrée **543,849000**, sortie **544,311000**.
- P&L = 714 × -1 × (544,311000 − 543,849000) − 4,998000 de commissions − 10,786339 d'emprunt = **-345,652338 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.

## 15. SPY — 2025-04-09 — LONG (avril 2025)

Entrée 2025-04-09 10:00:00-04:00, sortie 2025-04-09 10:30:00-04:00 ; motif `trailing_exit`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture 493,440000 ; clôture précédente 496,740000, référence ex-dividende 496,740000. Moyenne des 14 mouvements = 0,003005422.
- UB = 496,740000 × (1 + 0,003005422) = **498,232913** ; LB = 491,957004. VWAP HLC3 scalaire cumulé = **497,872449** ; prix de décision = **499,850000**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = 7 479 029 470,910 ; somme(volume) = 15 021 979 ; quotient = **497,872449**.
- Volatilité passée = 2,123537 % ; capital à l'ouverture 125 178,282562 ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **238**. Même quantité après les autres trades de cette séance.
- Sortie : premier franchissement de sortie à la décision 10:30 NY : prix 498,970000, UB 499,900887, LB 490,300111, VWAP 498,435201. Prix simulés après friction adverse : entrée **499,861000**, sortie **499,069000**.
- P&L = 238 × 1 × (499,069000 − 499,861000) − 1,666000 de commissions − 0,000000 d'emprunt = **-190,162000 USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.
