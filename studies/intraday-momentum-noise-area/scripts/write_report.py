"""Produit le rapport depuis les exports exécutés, sans recalcul des signaux/P&L."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import pickle
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from audit_study import indicators,near


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def number(v,digits=2):
    if v is None or (isinstance(v,float) and not math.isfinite(v)):return '—'
    return f'{v:,.{digits}f}'.replace(',',' ').replace('.',',')


def table(headers,rows):
    lines=['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']
    lines+=['| '+' | '.join(map(str,row))+' |' for row in rows]
    return '\n'.join(lines)+'\n'


def identity(r):
    return f'{r.instrument} {"open+1" if r.execution=="next_open" else "close"} {r.leverage_cap:g}x'


def make_manual(out,prepared):
    sample=load(out/'manual_10_inputs.json');texts=[];rows=[];markets={};cash={}
    for symbol in ['SPY','QQQ']:
        with (prepared/f'{symbol}_market.pkl').open('rb') as stream:markets[symbol]=pickle.load(stream)
        cash[symbol]=load(prepared/f'{symbol}_dividends.json')
    # Chronological sample chosen without a profit filter; these ten happen to be LONG.
    # Add explicit SHORT, reversal, half-day and ex-dividend coverage rather than hiding this limit.
    extra=[]
    spytrades=pd.read_csv(out/'SPY/B_next_open_L4_s0.001_principal/trades.csv')
    for label,condition in [
        ('premier SHORT',spytrades.direction=='SHORT'),
        ('retournement',spytrades.exit_reason=='reversal'),
        ('demi-séance',spytrades.exit_time.str[11:16]=='12:59'),
        ('ex-dividende',spytrades.date.isin(cash['SPY'])),
        ('avril 2025',spytrades.date=='2025-04-09')]:
        match=spytrades[condition]
        if match.empty:continue
        t=match.iloc[0];m=markets['SPY'];i=list(m.dates.strftime('%Y-%m-%d')).index(t.date)
        ind=next(x for x in indicators(m,i,cash['SPY']) if x['j']==int(t.entry_decision_index))
        extra.append({**t.to_dict(),**ind,'coverage':label})
    for k,item in enumerate(sample+extra,1):
        s=item['instrument'];m=markets[s];i=list(m.dates.strftime('%Y-%m-%d')).index(item['date'])
        day=indicators(m,i,cash[s]);sign=1 if item['direction']=='LONG' else -1
        sigma=math.fsum(item['past_moves'])/14
        near(sigma,item['sigma'],'manual sigma',1e-12)
        ub=max(item['opening'],item['previous_close_adjusted'])*(1+sigma)
        lb=min(item['opening'],item['previous_close_adjusted'])*(1-sigma)
        near(ub,item['upper'],'manual upper',1e-9);near(lb,item['lower'],'manual lower',1e-9)
        j=item['j'];a=m.arrays
        volume=math.fsum(a['volume'][i,:j+1])
        numerator=math.fsum((a['high'][i,k]+a['low'][i,k]+a['close'][i,k])/3*a['volume'][i,k] for k in range(j+1))
        near(numerator/volume,item['vwap'],'manual VWAP',1e-9)
        q=math.floor(item['equity_at_day_start']*min(4,.02/item['volatility'])/item['opening'])
        assert q==item['quantity']
        assert (item['price']>max(ub,item['vwap'])) if sign==1 else (item['price']<min(lb,item['vwap']))
        entry=item['entry_reference']+sign*.001;exitprice=item['exit_reference']-sign*.001
        fee=2*max(.35,q*.0035);borrow=q*entry*.01/360 if sign<0 else 0
        net=q*sign*(exitprice-entry)-fee-borrow
        near(net,item['net_pnl'],'manual pnl')
        # Expose independent intermediate decisions through the first exit.
        candidates=[x for x in day if x['j']>item['j'] and
                    (x['price']<max(x['upper'],x['vwap']) if sign==1 else x['price']>min(x['lower'],x['vwap']))]
        leave=candidates[0] if candidates else None
        exitclock=f"{(571+leave['j'])//60:02d}:{(571+leave['j'])%60:02d}" if leave else None
        exittext=(f"premier franchissement de sortie à la décision {exitclock} NY : prix {number(leave['price'],6)}, UB {number(leave['upper'],6)}, LB {number(leave['lower'],6)}, VWAP {number(leave['vwap'],6)}"
                  if leave else "aucun franchissement de sortie avant la fin ; liquidation à l'open de la dernière minute")
        texts.append(f"""## {k}. {s} — {item['date']} — {item['direction']} ({item.get('coverage','échantillon chronologique')})

Entrée {item['entry_time']}, sortie {item['exit_time']} ; motif `{item['exit_reason']}`. Les quatorze dates passées et mouvements élémentaires sont conservés dans `manual_10_inputs.json` pour l'échantillon initial.

- Ouverture {number(item['opening'],6)} ; clôture précédente {number(item['previous_close'],6)}, référence ex-dividende {number(item['previous_close_adjusted'],6)}. Moyenne des 14 mouvements = {number(sigma,9)}.
- UB = {number(max(item['opening'],item['previous_close_adjusted']),6)} × (1 + {number(sigma,9)}) = **{number(ub,6)}** ; LB = {number(lb,6)}. VWAP HLC3 scalaire cumulé = **{number(item['vwap'],6)}** ; prix de décision = **{number(item['price'],6)}**. Le double filtre bande/VWAP autorise cette entrée.
- VWAP : somme(HLC3 × volume), jusqu'à la minute terminée seulement, = {number(numerator,3)} ; somme(volume) = {number(volume,0)} ; quotient = **{number(numerator/volume,6)}**.
- Volatilité passée = {number(item['volatility']*100,6)} % ; capital à l'ouverture {number(item['equity_at_day_start'],6)} ; quantité = floor(capital × min(4 ; 0,02/vol) / ouverture) = **{q}**. Même quantité après les autres trades de cette séance.
- Sortie : {exittext}. Prix simulés après friction adverse : entrée **{number(entry,6)}**, sortie **{number(exitprice,6)}**.
- P&L = {q} × {sign} × ({number(exitprice,6)} − {number(entry,6)}) − {number(fee,6)} de commissions − {number(borrow,6)} d'emprunt = **{number(net,6)} USD**. Rapprochement du journal : écart inférieur à 0,000001 USD.
""")
        rows.append(dict(instrument=s,date=item['date'],coverage=item.get('coverage','chronological'),direction=item['direction'],quantity=q,independent_pnl=net,ledger_pnl=item['net_pnl']))
    pd.DataFrame(rows).to_csv(out/'MANUAL_CHECKS.csv',index=False)
    (out/'EXAMEN_MANUEL.md').write_text('# Examen des transactions historiques\n\nDix premières transactions de B, cinq par ETF, puis cas de couverture explicites. Sélection chronologique avant examen des gains ; les dix premières sont toutes LONG. Calculs scalaires indépendants du moteur, examinés pour cohérence des seuils, des horaires, des quantités et du P&L. Aucun prix fictif. Le contrôle exhaustif séparé couvre aussi tous les SHORT et retournements des 32 scénarios principaux.\n\n'+'\n'.join(texts),encoding='utf-8')
    return len(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,default=Path('results/2026-10-19'))
    p.add_argument('--prepared',type=Path,default=Path('data/prepared'));p.add_argument('--workspace',type=Path,required=True)
    args=p.parse_args();out=args.results;workspace=args.workspace
    audit=load(out/'AUDIT_HISTORIQUE.json');assert audit['status']=='passed'
    risk=load(out/'INTRADAY_RISK_AUDIT.json');assert risk['status']=='passed'
    frame=pd.read_csv(out/'comparison_all.csv');r=pd.read_csv(out/'INTRADAY_RISK_AUDIT.csv')
    mainrows=frame[(frame.kind=='principal')&(frame.slippage==.001)]
    b=mainrows[mainrows.period=='B'];bn=b[b.execution=='next_open']
    def summary(row):return load(out/row.instrument/row.label/'summary.json')
    def stattable(part):
        return table(['Compte / exécution / cible','Trades','Net USD','Total %','CAGR %','Sharpe','Sortino','Vol. %','PF','DD minute %'],
                     [[identity(x),x.trades,number(x.net_pnl),number(x.total_return_pct),number(x.cagr_pct),number(x.sharpe),number(x.sortino),number(x.volatility_annual_pct),number(x.profit_factor),number(x.max_drawdown_pct)] for x in part.itertuples()])
    nmanual=make_manual(out,args.prepared)
    # Carry small provenance files into the distributable results, never minute data or keys.
    for name in ['DATA_VALIDATION.json','SPY_quality.csv','QQQ_quality.csv','SPY_dividends.json','QQQ_dividends.json']:
        shutil.copy2(args.prepared/name,out/name)
    source_folder=workspace/'data/noise_area_sources'
    shutil.copy2(source_folder/'DIVIDEND_RECONCILIATION.json',out/'DIVIDEND_RECONCILIATION.json')
    assert any((source_folder/name).exists() for name in ['source_downloads.json','PUBLIC_DOWNLOAD_RECEIPT.json']), 'Missing public-source acquisition receipt.'
    for name in ['source_downloads.json','PUBLIC_DOWNLOAD_RECEIPT.json']:
        if (source_folder/name).exists():shutil.copy2(source_folder/name,out/name)
    fresh=Path('data/prepared_reproduction/DATA_VALIDATION.json');reproduction_verified=False
    if fresh.exists():
        original=load(args.prepared/'DATA_VALIDATION.json');reproduced=load(fresh)
        assert original['prepared_files_sha256']==reproduced['prepared_files_sha256']
        shutil.copy2(fresh,out/'DATA_REPRODUCTION_VALIDATION.json')
        reproduction_verified=True
    notes=dict(unadjusted_gap=dict(affected_rows=4,exported_lookback=99,actual_sigma_lookback=14,
               explanation='99 is the internal feature cache key for the no-dividend diagnostic, not a 99-session lookback. Prices, trades and P&L unaffected.'),
               duration='summary.worst_drawdown_duration_calendar_days is DAILY-CLOSE duration. INTRADAY_RISK_AUDIT reports duration of the actual worst minute drawdown.',
               audit_days='independent_calendar_days counts scenario-day recalculations with overlapping periods, not independent market observations.')
    (out/'OUTPUT_METADATA_NOTES.json').write_text(json.dumps(notes,indent=2),encoding='utf-8')
    sections=['''# Noise Area — backtest et validation au 16 octobre 2026

Étude exécutée le 19 octobre 2026 (heure de New York), terminée le 20 octobre en UTC. Capital initial de **100 000 USD par compte**. Résultats locaux ; aucun ajout à GitHub à ce stade.

## A. Résultat principal et portée

**SPY : catégorie 3 — aucun avantage démontré. QQQ : catégorie 2 — potentiellement intéressante, preuves insuffisantes.** Sur B, QQQ présente une performance positive et un signal statistique au coût bas, avec les mêmes paramètres que SPY. Cela justifie de poursuivre l'observation ; cela ne suffit pas à conclure à un avantage exploitable aujourd'hui. SPY est très sensible aux coûts et ses intervalles incluent largement zéro.

B correspond à la coupure demandée, du **1er mai 2024 au 16 octobre 2026**, soit 618 séances. Convention principale : décision sur minute terminée, exécution au **prochain open**, friction adverse **0,001 USD/action/côté**, commission **0,0035 USD/action/côté, minimum 0,35 USD/ordre**, emprunt SHORT supposé disponible à **1 %/an, minimum un jour/360 par trade**. La friction de référence est un dixième de cent ; les tests à 1–5 cents ci-dessous sont essentiels.
''',stattable(bn),'''
Le buy & hold SPY, dividendes réinvestis, gagne **56,51 %**, Sharpe **1,26** sur les mêmes dates. QQQ buy & hold gagne **69,39 %**, Sharpe **1,12**. Ces passifs sont théoriques, sans frais ni impôt ; leurs drawdowns quotidiens ne doivent pas être assimilés aux drawdowns minute de la stratégie.

La publication initiale n'est pas le 1er mai : le PDF indique une première version au 10 mai 2024 et SSRN une mise en ligne le 14 mai. Le PDF accessible est **révisé au 22 septembre 2025**. Sans copie séparée de mai 2024, B ne constitue pas un hors-échantillon incontestable de la révision consultée. C commence le 15 mai 2024 ; D, le **23 septembre 2025**, est le contrôle après la révision. Cette limite était fixée dans le protocole avant les performances. [Article officiel](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf), [page SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172).

Sur D, QQQ reste bénéficiaire mais ses intervalles de confiance incluent zéro ; SPY perd. Les dix meilleurs jours de B expliquent environ **98–104 % du P&L QQQ**, selon la cible. Ces éléments empêchent la catégorie 1 et une recommandation de passage en réel.

![Capital B, échelle logarithmique](B_OVERVIEW.png)

## B. Reproduction partielle de l'article

L'article annonce environ **1 985 %** au total, **19,6 %/an** et un **Sharpe de 1,33** sur mai 2007–avril 2024. Notre A couvre seulement **26 janvier 2016–30 avril 2024** : les rendements totaux ne sont donc pas directement comparables. La reproduction exacte 2007–2024 n'a pas été réalisée.
''',table(['Mesure / périmètre','Total %','CAGR %','Sharpe'],[['Article annoncé, mai 2007–avril 2024','1 985','19,6','1,33']]+[[f'Notre SPY A, {x.execution}, cible 4x',number(x.total_return_pct),number(x.cagr_pct),number(x.sharpe)] for x in mainrows[(mainrows.period=='A')&(mainrows.instrument=='SPY')&(mainrows.leverage_cap==4)].itertuples()]),stattable(mainrows[mainrows.period=='A']),'''
Les chiffres sont positifs sur A, mais ne prouvent pas la reproduction des chiffres publiés. Les différences de période, source SIP, filtre de séances complètes, coûts fixes avec minimum, dividendes, arrondi inférieur, fenêtres strictement passées et sortie à 15:59 expliquent des écarts possibles. Aucune attribution quantitative de chaque écart au papier n'est revendiquée. Le tutoriel utilise notamment un arrondi et une tranche de volatilité différents de la formule du papier ; nos choix restent ceux du protocole.

Quatre séances de mars 2020 avec 14 minutes absentes ont été exclues : 9, 12, 16 et 18 mars. Ces dates correspondent aux interruptions générales de marché documentées par le NYSE ; ce ne sont pas nécessairement des erreurs du fournisseur. L'exigence d'une grille complète retire donc des journées de crise importantes et affecte aussi le réchauffement ultérieur. C'est une limite matérielle de A, sans incidence sur les 618 séances complètes de B. [NYSE : interruptions de mars 2020](https://www.nyse.com/article/assessing-nyse-model-performance).

## C. B : comparaison des conventions et métriques
''',stattable(b),'''
Le passage du close au prochain open modifie peu ces résultats agrégés, mais le close suppose une exécution au prix qui vient de former le signal. Aucune convention ne démontre un remplissage réel. La sortie de fin de séance est l'open de la dernière minute dans les deux versions, sans prix officiel MOC.
''']
    metrics=[('Trades / séance','trades_per_day'),('% séances avec trade','days_traded_pct'),('Win rate %','win_rate_pct'),
             ('Gain moyen USD','average_gain'),('Perte moyenne USD','average_loss'),('Ratio gain/perte','gain_loss_ratio'),
             ('P&L moyen / nominal entrée bps','mean_trade_bps'),('Série max pertes, trades','longest_loss_streak'),
             ('Bêta quotidien vs SPY TR','beta_vs_SPY'),('Corrélation quotidienne vs SPY TR','correlation_vs_SPY'),
             ('DD max USD','max_drawdown_usd'),('DD max aux clôtures %','max_daily_close_drawdown_pct'),
             ('Pire jour %','worst_day_pct'),('Pire mois %','worst_month_pct'),('Pire année %','worst_year_pct'),
             ('Commissions USD','commission'),('Emprunt USD','borrow_fee')]
    for symbol in ['SPY','QQQ']:
        rows=list(b[b.instrument==symbol].itertuples())
        sections += [f'### Métriques détaillées — {symbol}\n',table(['Mesure']+[identity(x) for x in rows],
                 [[title]+[number(getattr(x,key)) for x in rows] for title,key in metrics]),
                 table(['Compte','Pire jour','Pire mois','Pire année'],[[identity(x),x.worst_day,x.worst_month,x.worst_year] for x in rows])]
    sections+=['''Les moyennes par trade ne sont pas des rendements de compte : les bps divisent le P&L net par le nominal d'entrée. Les années 2024 et 2026 de B sont partielles. Les bêta/corrélations utilisent toutes les séances, y compris celles sans position. Sharpe : rendement quotidien net, taux sans risque nul, annualisation 252 ; Sortino : racine de la moyenne des carrés négatifs sur toutes les séances. CAGR : durée calendaire. Le cash ne rapporte aucun intérêt.

### Coupures de publication : C et D
''',stattable(mainrows[mainrows.period.isin(['C','D'])].assign(instrument=lambda d:d.instrument+' / '+d.period)),
                'C et D sont des comptes réinitialisés à 100 000 USD, réchauffés uniquement avec le passé. Ils recouvrent B et ne sont pas des observations indépendantes.\n']
    dboot=load(out/'POST_REVISION_VALIDATION.json')
    sections += [table(['D, prochain open','IC95 moyenne/jour %','IC95 Sharpe','p aléatoire Sharpe'],
                    [[f"{x['instrument']} {x['leverage_cap']:g}x",' ; '.join(number(v*100,4) for v in x['daily_mean_ci95']),
                      ' ; '.join(number(v,3) for v in x['sharpe_ci95']),number(x['p_random_sharpe_ge_strategy'],4)] for x in dboot if x['execution']=='next_open']),
                 '## D. Risque, levier et coûts\n']
    risks=r[(r.period=='B')&(r.execution=='next_open')]
    sections+=[table(['Compte','DD minute USD','DD minute %','Durée calendaire, jours','Récupéré ?','Levier moyen détenu','Max effectif'],
                    [[identity(x),number(x.max_drawdown_usd),number(x.max_drawdown_pct),number(x.drawdown_pct_duration_calendar_days),
                      'oui' if x.drawdown_pct_recovered else 'non, censuré au 16/10/2026',number(x.effective_leverage_held_minute_mean,3),number(x.effective_leverage_max,3)] for x in risks.itertuples()]),
                 '''La durée ci-dessus concerne **l'épisode du pire drawdown en pourcentage aux marques minute**, du dernier sommet égal au premier retour au sommet, ou jusqu'à la fin s'il reste ouvert. Le maximum USD peut appartenir à un autre épisode. Les durées quotidiennes du `summary.json` sont distinctes et explicitement nommées dans `OUTPUT_METADATA_NOTES.json`. L'audit indépendant livre sommets, creux, récupération et dates des maxima dans [INTRADAY_RISK_AUDIT.csv](INTRADAY_RISK_AUDIT.csv).

Le levier moyen est pondéré par les minutes effectivement détenues ; le maximum inclut les marques de prix et les remplissages. Les cibles 1x/4x sont calculées à l'ouverture et les actions sont figées toute la séance. La cible 1x n'est donc pas une simulation stricte de compte cash : elle atteint environ **1,02x** en B. La cible 4x atteint environ **4,15x**. Les pertes ou mouvements de cours peuvent augmenter l'exposition effective ; aucune liquidation de marge automatique n'est simulée. Les résultats ne constituent pas la performance garantie d'un compte soumis à un plafond dur.

### Friction adverse par action et par côté

Les commissions et l'emprunt restent appliqués en plus de la friction. Chaque cellule résulte d'un rejeu complet avec composition, pas d'une déduction linéaire des coûts.
''']
    costs=frame[(frame.period=='B')&(frame.kind=='principal')&(frame.execution=='next_open')]
    sections+=[table(['Friction USD/côté','SPY 1x net USD','SPY 4x','QQQ 1x','QQQ 4x'],
                    [[number(cost,3)]+[number(costs[(costs.instrument==s)&(costs.leverage_cap==cap)&(costs.slippage==cost)].net_pnl.iloc[0]) for s,cap in [('SPY',1),('SPY',4),('QQQ',1),('QQQ',4)]] for cost in [.001,.01,.02,.03,.05]]),
                 table(['Compte','Friction de point mort USD/action/côté'],[[f"{x['instrument']} {x['leverage_cap']:g}x",number(x['slippage_per_side_usd'],6)] for x in load(out/'COST_BREAKEVEN.json')]),
                 '''Les points morts sont obtenus par bissection avec composition, frais et emprunt inchangés. Ils ne sont ni un coût total par trade ni une promesse d'exécution : spread, impact et difficulté d'emprunt réels peuvent varier, surtout pendant les jours qui portent le résultat. À 1 cent, SPY 1x est déjà légèrement perdant ; SPY 4x passe en perte entre 1 et 2 cents. QQQ demeure bénéficiaire jusqu'à 5 cents dans l'échantillon, mais cela ne garantit pas la persistance de sa moyenne.

Sensibilité de l'emprunt SHORT, prochain open, autres paramètres fixes :
''',table(['Compte','Emprunt annuel','Net USD'],[[identity(x),f'{x.borrow_rate*100:g} %',number(x.net_pnl)] for x in frame[(frame.period=='B')&frame.kind.str.startswith('borrow')].itertuples()]),
                 '''Historique réglementaire : l'ancienne règle PDT exigeait 25 000 USD pour les comptes qualifiés et le 4x dépendait de la marge disponible. Au 19 octobre 2026, FINRA indique une nouvelle norme effective depuis le 4 juin 2026, avec transition des courtiers jusqu'au 20 octobre 2027. Le régime applicable dépend donc du courtier ; le résumé « 25 000 USD obligatoire aujourd'hui dans tous les cas » serait inexact. Cette étude ne vérifie aucun pouvoir d'achat personnel. [FINRA](https://syndication.finra.org/content/understanding-new-intraday-margin-requirements), [Investor.gov](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/margin).

## E. Robustesse, contrôles et concentration

### Incertitude de B

Bootstrap circulaire de **blocs de 5 séances**, **5 000 réplications**, seed **20261019**, mêmes dates rééchantillonnées pour la stratégie et le passif. Les IC sont conditionnels à cet historique et à cette longueur de bloc ; ils ne couvrent pas toute l'incertitude de modèle. Les variantes se recouvrent et aucune correction de multiplicité n'a été appliquée.
''']
    bootrows=[];controlrows=[];toprows=[]
    for row in bn.itertuples():
        s=summary(row);boot=s['bootstrap_block5'];control=s['control_summary']
        bootrows.append([identity(row),' ; '.join(number(x*100,4) for x in boot['daily_mean_ci95']),
                         ' ; '.join(number(x,3) for x in boot['sharpe_ci95']),' ; '.join(number(x,3) for x in boot['sharpe_minus_buyhold_ci95'])])
        controlrows.append([identity(row),number(control['always_long']['total_return_pct']),number(control['always_long']['sharpe']),
                            number(control['p_random_sharpe_ge_strategy'],4),number(control['p_random_final_equity_ge_strategy'],4)])
        toprows.append([identity(row),number(row.top10_days_pnl),number(row.top10_days_share_of_total_pct),number(row.return_without_top10_days_pct)])
    sections += [table(['Compte','IC95 moyenne/jour %','IC95 Sharpe','IC95 ΔSharpe vs ETF passif'],bootrows),
                 '''QQQ au coût de référence a un IC de moyenne et de Sharpe au-dessus de zéro sur B. L'IC de sa différence de Sharpe avec son propre passif inclut zéro : la supériorité ajustée au risque n'est pas établie. SPY n'a pas de moyenne significativement positive. Pour QQQ à 5 cents, les IC incluent zéro ; sur D également. [Tous les IC de coûts B](UNCERTAINTY_B_COSTS.json), [contrôle D](POST_REVISION_VALIDATION.json).

### Comparaison appariée avec SPY passif
''',table(['Compte','IC95 ΔSharpe vs SPY passif'],[[f"{x['instrument']} {x['leverage_cap']:g}x",' ; '.join(number(v,3) for v in x['bootstrap']['sharpe_minus_buyhold_ci95'])] for x in load(out/'B_VS_SPY_PASSIVE.json')['results'] if x['execution']=='next_open']),
                 '''Les différences de Sharpe avec SPY incluent également zéro. Les simulations appariées utilisent exactement les mêmes dates tirées en blocs ; [résultats complets](B_VS_SPY_PASSIVE.json).

### Contrôles de direction

Mêmes intervalles fermés d'entrée/sortie que la stratégie ; **1 000** directions ±1 aléatoires, quantités recalculées sur le capital de chaque chemin, commissions/friction/emprunt appliqués. Le benchmark toujours LONG utilise aussi les sorties de la stratégie. Les horaires et la durée sont déterminés par les signaux originaux : ces contrôles conditionnels ne sont pas une stratégie aléatoire entièrement indépendante ni une preuve causale d'alpha. p empirique unilatérale = (1 + nombre de contrôles au moins aussi bons) / 1 001, sans correction pour essais multiples.
''',table(['Compte','Toujours LONG total %','Sharpe LONG','p aléatoire Sharpe','p aléatoire capital final'],controlrows),
                 '### Concentration des gains\n',table(['Compte','P&L dix meilleurs jours USD','Part du P&L total %','Rendement si dix rendements journaliers retirés %'],toprows),
                 '''Une part supérieure à 100 % signifie que les autres journées ont un P&L en dollars négatif. Le retrait des dix rendements quotidiens est un diagnostic mécanique : il ne rejoue pas une nouvelle taille de position après suppression des journées. Il diffère donc de la contribution en dollars. Cela mesure une concentration, sans affirmer qu'une stratégie de suivi de tendance doit gagner tous les jours.
''']
    for symbol in ['SPY','QQQ']:
        folder=out/symbol/'B_next_open_L4_s0.001_principal'
        daily=pd.read_csv(folder/'daily.csv')
        sections += [f'#### {symbol}, cible 4x : dix meilleurs jours B\n',table(['Date','P&L net USD'],[[x.date,number(x.net_pnl)] for x in daily.nlargest(10,'net_pnl').itertuples()])]
        event=[]
        for period,month in [('A','2020-03'),('B','2025-04')]:
            d=pd.read_csv(out/symbol/f'{period}_next_open_L4_s0.001_principal/daily.csv');part=d[d.date.str.startswith(month)]
            event.append([month,number(part.net_pnl.sum()),number((np.prod(1+part.return_net)-1)*100),int((part.eligibility!='eligible').sum())])
        sections += [table(['Mois de crise','P&L net USD','Rendement %','Séances sans trade pour qualité/réchauffement'],event)]
    sections += ['### Paramètres voisins — aucune sélection du meilleur\n',
                 table(['Compte','Changement isolé','Net USD','Sharpe','DD minute %'],[[identity(x),x.kind,number(x.net_pnl),number(x.sharpe),number(x.max_drawdown_pct)] for x in frame[(frame.period=='B')&frame.kind.str.match('lookback|frequency|stop_')].itertuples()]),
                 '''Les paramètres principaux restent 14/30/stop combiné. Les fenêtres 10/20 ne changent pas les 14 rendements du dimensionnement. Les décisions de 15 ou 60 minutes changent le premier horaire aussi, depuis 09:30. SPY n'est pas stable au changement de fréquence ; QQQ reste positif dans les voisins testés. Ces tableaux ne sont pas une optimisation à exploiter après lecture.

### Walk-forward à paramètres fixes

Trimestres civils, capital autonome de 100 000 USD par bloc, historique passé disponible pour le réchauffement. Premier et dernier trimestres partiels. Les blocs sont descriptifs et recouvrent B ; leur addition ne reconstitue pas le P&L composé de B.
''',table(['ETF','Cible','Bloc','Net USD','Sharpe','Trades'],[[x.instrument,f'{x.leverage_cap:g}x',x.kind,number(x.net_pnl),number(x.sharpe),x.trades] for x in frame[(frame.period=='WF')&(frame.execution=='next_open')].itertuples()]),
                 '### Comportement B — prochain open, cible 4x\n']
    for symbol in ['SPY','QQQ']:
        folder=out/symbol/'B_next_open_L4_s0.001_principal'
        sections += [f'#### {symbol}\n']
        for file,title in [('by_direction.csv','Sens'),('by_entry_clock.csv','Heure d’entrée NY'),('by_volatility_regime.csv','Tercile de volatilité passée'),('by_vix_regime.csv','VIX à l’ouverture'),('by_year.csv','Année')]:
            df=pd.read_csv(folder/file)
            sections += [title+'\n',table(df.columns,[[number(v) if isinstance(v,(float,np.floating)) else v for v in row] for row in df.itertuples(index=False,name=None)])]
        sections += [f'![{symbol} : rendements et distribution](./{symbol}/B_next_open_L4_s0.001_principal/behavior.png)',
                     f'![{symbol} : contrôles de direction](./{symbol}/B_next_open_L4_s0.001_principal/random_controls.png)']
    sections += ['''Les seuils des terciles de volatilité sont estimés sur A seulement puis gelés. Le VIX est l'ouverture quotidienne CBOE, observée avant la première décision, sans clôture du jour utilisée pour classer les trades. Les seuils VIX sont 15 et 25 ; les libellés exacts proviennent des exports. Les résultats en dollars par régime dépendent aussi du capital et du nombre de trades. Les distributions ne prouvent pas une règle conditionnelle profitable. Tous les regroupements existent pour les **32 scénarios principaux** dans leurs sous-dossiers ; les mois sont dans `by_month.csv`.

## F. Méthode, données, code et validation

### Résumé utilisateur vs sources et choix

Voir le [protocole préexécution](../../docs/PROTOCOLE.md) et ses empreintes dans [PRE_EXECUTION_PROTOCOL.json](PRE_EXECUTION_PROTOCOL.json). Le principal changement d'entrée est le filtre bande **et VWAP**, conformément au code des auteurs. La clôture précédente est diminuée du dividende ex-date uniquement pour les références de bandes ; les OHLC minute restent bruts. Les retournements sont immédiats aux décisions, avec fermeture puis ouverture facturées séparément. L'arrondi inférieur et les 14 rendements passés suivent la formule du papier, même lorsque le tutoriel diffère. [Python des auteurs](https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/).

La zone de bruit utilise 14 observations passées à la même minute, jour courant exclu. Les demi-séances contribuent avant 13:00 et ne créent pas de zéros l'après-midi : les 14 observations de l'après-midi peuvent couvrir plus de 14 séances. Volatilité de taille : 14 rendements bruts close-à-close, ddof=1, veille incluse, quinze clôtures consécutives complètes. Une fenêtre manquante laisse le compte plat. Aucun indicateur de signal n'utilise les minutes futures ; VWAP HLC3 limité à la minute terminée.

### Provenance et qualité réelles

**4 258 678 lignes minute Alpaca SIP raw** acquises : SPY 2 166 287, QQQ 2 092 391. Réutilisation vérifiée de 2023–septembre 2026, extension 2016–2022 et fin septembre–16 octobre 2026. Chaque CSV est rapproché ligne à ligne de toutes ses pages JSON originales compressées, avec hashes des deux. Le nombre comprend les heures étendues ; seuls les créneaux réguliers contrôlés servent aux signaux. Aucune bougie minute n'est reconstruite et aucun trou n'est interpolé. [Disponibilité historique SIP](https://docs.alpaca.markets/us/docs/market-data-faq).

Le jeu de données finit le **16 octobre 2026** ; la séance du 19 octobre n'est pas incluse. Le calendrier de contrôle comprend une ligne technique du 31 décembre 2015, provenant de l'UTC initial, sans aucune minute régulière : exclue du backtest. Les premières données régulières sont celles du 4 janvier 2016 ; premier jour éligible le 26 janvier après réchauffement.
''']
    validation=load(out/'DATA_VALIDATION.json')
    sections += [table(['ETF','Séances calendaires contrôlées','Complètes','Exclues dont ligne 2015','Dividendes résolus'],
                    [[x['symbol'],x['calendar_sessions'],x['valid_sessions'],x['excluded_sessions'],x['cash_dividend_count']] for x in validation['profiles']])]
    for symbol in ['SPY','QQQ']:
        q=pd.read_csv(out/f'{symbol}_quality.csv');q=q[q.status=='excluded']
        sections += [f'Séances exclues — {symbol}\n',table(['Date','Minutes absentes','Minutes de décision absentes'],[[x.date,x.missing_minutes,x.missing_decision_minutes] for x in q.itertuples()])]
    sections += ['''L'exclusion complète d'une journée est connue **après** contrôle des données. Même si elle évite des indicateurs artificiels, elle ne simule pas la détection causale d'une panne en cours de journée. Les résultats sont donc conditionnels au filtre de qualité ; ce point affecte surtout A. En B, les 618 séances sont toutes complètes et éligibles.

Dividendes : SPY utilise les 43 distributions officielles SSGA, trois ex-dates étant absentes de la réponse Alpaca. QQQ utilise 44 événements Alpaca uniques ; un doublon identique est retiré. Yahoo confirme les dates SPY et la plupart des événements QQQ, mais manque le 21 septembre 2020 et diffère légèrement sur un montant de 2018. Ces divergences sont conservées dans [DIVIDEND_RECONCILIATION.json](DIVIDEND_RECONCILIATION.json). Disponibilité ex ante des annonces supposée, pas auditée. [SSGA](https://www.ssga.com/us/en/individual/resources/documents/etf-dividend-distributions).

Les benchmarks passifs utilisent les clôtures SIP régulières lorsqu'elles existent, avec clôtures quotidiennes Yahoo de secours lorsque nécessaire et historique des dividendes. Ils ne remplacent jamais des OHLC minute manquants. Rendement total théorique : (clôture + dividende) / clôture précédente − 1. Les dates de secours sont enregistrées dans le manifest. Le VIX provient du [CSV officiel CBOE](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv).

### Exécution et vérifications réalisées
''',f'''- **220 scénarios exécutés** : 80 A/B avec cinq coûts, 16 C/D, 24 paramètres voisins B, huit emprunts B, quatre diagnostics de gap et 88 blocs trimestriels. Aucun réglage retenu en fonction de B.
- **32 tests unitaires** des fonctions critiques passés ; scénarios synthétiques réservés aux tests, jamais utilisés pour les résultats de marché.
- Audit exhaustif de **220 exports**, reconstruction scalaire indépendante de **32 scénarios principaux**, **{audit['halfhour_decisions_checked']:,} décisions** et **{audit['primary_trade_rows_checked']:,} lignes de trades** contrôlées. Les périodes recouvrantes comptent plusieurs fois les mêmes transactions économiques ; ce n'est pas un nombre d'observations indépendantes.
- Risque recalculé séparément sur **{sum(x['marks'] for x in risk['results_by_scenario']):,} marques**, rapprochement du P&L et du drawdown minute. Écart de ledger maximal inférieur à 0,000001 USD.
- **{nmanual} transactions historiques détaillées**, dont les dix premières chronologiques et des cas SHORT/retournement/demi-séance/ex-dividende : [examen des calculs](EXAMEN_MANUEL.md).
- Réexécution complète de la préparation : les six fichiers de données préparées ont des hashes identiques à ceux utilisés pour le backtest. [Reproduction](DATA_REPRODUCTION_VALIDATION.json).
- **73 figures** issues des exports, provenance et hashes conservés ; contrôle visuel des figures de synthèse et d'échantillons détaillés. Les courbes de drawdown dessinées sont quotidiennes, leur pire marque minute est indiquée séparément.
''', '''Les audits partagent les acquisitions brutes contrôlées ; ils ne prouvent pas les remplissages réels. Le diagnostic « gap non ajusté » a un champ `lookback=99` dans quatre lignes d'export : **99 est une clé interne, le calcul utilise bien 14 observations**. Cette annotation est expliquée dans [OUTPUT_METADATA_NOTES.json](OUTPUT_METADATA_NOTES.json) sans réécrire les exports ou les performances figés.

### TradingView, futures et fonctions non validées

Le [Pine v6](../../tradingview/noise_area.pine) a été **réellement compilé et sauvegardé** dans TradingView. Le compte accessible n'a fourni qu'une séance dans le testeur, **zéro trade** : aucune validation annuelle ou concordance de signaux Python/Pine n'est revendiquée. Basic annonce 5 000 bougies, moins que les 5 460 nécessaires à quatorze journées pleines, avant la séance courante. Le minimum de commission et l'emprunt ne sont pas modélisés en Pine ; son slippage entier vaut 1 cent et sa marge peut liquider des positions. [Statut détaillé et preuve](../../tradingview/README.md).

ES/NQ restent hors périmètre, faute de contrats et raccordements vérifiables. Les quotes bid/ask, impact, latence, halts en temps réel, disponibilité et prix d'emprunt à chaque date, marge réelle, intérêts du cash, impôts et changements de régime ne sont pas validés. Les limites d'exposition ne sont pas imposées en cours de position. Les coûts constants sont des hypothèses de simulation, particulièrement optimistes à 0,001 USD.

### Reproduire et inspecter

Les [instructions](../../README.md), dépendances figées, scripts, code et tests sont livrés. Les données minute et les clés restent locales, hors Git. Les journaux `trades.csv`, `daily.csv`, `decisions.csv` et `summary.json` se trouvent dans chaque dossier de scénario. [Comparaison complète : 220 lignes](comparison_all.csv), [audit historique](AUDIT_HISTORIQUE.json), [audit du risque](INTRADAY_RISK_AUDIT.json), [manifest d'exécution](manifest.json), [qualité des acquisitions](DATA_VALIDATION.json).

## G. Réponses aux dix questions et conclusion

1. **Reproduction A : partielle.** Les résultats A sont positifs ; la période 2007–2015 manque et les séances de crise incomplètes sont filtrées. Les chiffres 1 985 % / 19,6 % / 1,33 ne sont pas reproduits à l'identique, sans comparabilité temporelle suffisante pour attribuer un écart à une seule cause.
2. **Rentabilité B :** positive au coût bas pour les quatre comptes. SPY 1x devient perdant à 1 cent et SPY 4x à 2 cents ; QQQ reste positif à 5 cents, avec une preuve statistique moins nette. B inclut quelques jours avant publication et la révision est postérieure : D apporte la réserve déterminante.
3. **Mieux que SPY passif ajusté au risque :** SPY clairement moins bon en valeur centrale ; QQQ a un Sharpe central légèrement supérieur à SPY, sans preuve de supériorité statistique. Les IC appariés contre SPY et contre le passif de chaque ETF incluent zéro.
4. **Direction aléatoire :** QQQ dépasse environ 99 % des contrôles conditionnels au coût de référence B ; SPY ne les bat pas significativement. Sur D, les p de QQQ sont supérieures à 5 %. Multiplicité et conditionnement interdisent une interprétation comme preuve autonome d'alpha.
5. **Levier :** il amplifie les gains, mais aussi le drawdown. QQQ 1x gagne déjà 29,21 % en B ; la cible 4x porte le gain à 59,41 %, DD de 7,02 à 15,46 %. SPY reste faible sans cible élevée. Le levier effectif moyen QQQ 4x n'est qu'environ 2,01x ; aucun simple facteur quatre ne décrit ces résultats composés.
6. **Journées exceptionnelles :** dépendance forte, surtout B. Les dix jours QQQ portent presque tout le P&L et le retrait mécanique laisse moins de 1 % de rendement. Les exclusions de mars 2020 limitent en plus l'analyse de cette crise ; avril 2025 est conservé.
7. **Point mort :** friction par côté approximativement 0,00973/0,01875 USD SPY 1x/4x et 0,14488/0,13052 USD QQQ 1x/4x, frais et emprunt en plus. Il s'agit d'un résultat rétrospectif composé, pas d'un budget de coûts fiable à l'avenir.
8. **QQQ sans réglage :** oui, résultats B plus favorables avec exactement les mêmes paramètres et son propre historique de volatilité. Cela ne transforme pas QQQ en preuve indépendante d'une stratégie découverte sur marchés corrélés.
9. **LONG et SHORT :** contributions nettes positives pour les deux ETF en B, cible 4x, avec équilibre meilleur sur QQQ ; les tableaux par sens donnent les montants exacts. Le rendement de chaque côté reste conditionnel aux mêmes journées et coûts d'emprunt supposés.
10. **Avantage aujourd'hui :** **SPY, catégorie 3** ; **QQQ, catégorie 2**. QQQ mérite un suivi prospectif figé avec données et coûts d'exécution observés, sans changer les paramètres après ce rapport. La concentration, les IC de D, les coûts et les contraintes de marge empêchent de qualifier cette étude de validation solide pour du trading réel.

Les résultats établissent ce que cette simulation a produit jusqu'au 16 octobre 2026. Ils ne justifient pas un passage en réel sur la seule base d'un backtest positif.
''']
    report='\n\n'.join(sections).replace('335,136','335 136').replace('24,352','24 352')
    if not reproduction_verified:
        report=report.replace('- Réexécution complète de la préparation : les six fichiers de données préparées ont des hashes identiques à ceux utilisés pour le backtest. [Reproduction](DATA_REPRODUCTION_VALIDATION.json).',
                              '- Préparation contrôlée par son manifest ; une seconde préparation complète aux hashes identiques n’a pas été vérifiée pour cette exécution.')
    (out/'RAPPORT_FINAL.md').write_text(report,encoding='utf-8')
    receipt=dict(schemaVersion=1,items=[dict(id='noise-area-b',title='Noise Area : validation B sur SPY et QQQ',queries=[dict(id='noise-area-execution',source=dict(label='Backtest Python Noise Area, exécution locale',
                 metricDefinitions=['Rendement net : capital final / 100 000 USD − 1, commissions, friction et emprunt inclus.',
                                    'Sharpe : rendements quotidiens nets, taux sans risque nul, annualisation 252.',
                                    'Drawdown : marques minute et exécutions simulées.'],
                 filters=['2024-05-01 au 2026-10-16','Alpaca SIP raw ; séance régulière NYSE','Prochain open ; cibles 1x/4x ; friction 0,001 USD/action/côté'],
                 caveats=['La période B commence avant la publication initiale et avant la révision de septembre 2025.',
                          'QQQ dépend de quelques jours ; la validation après révision et à coûts plus élevés reste incertaine.',
                          'Les cibles de levier peuvent être dépassées en cours de position ; les appels de marge ne sont pas simulés.'],
                 links=[dict(label='Article des auteurs',url='https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf'),
                        dict(label='Données SIP historiques Alpaca',url='https://docs.alpaca.markets/us/docs/market-data-faq')],
                 executedAt=load(out/'manifest.json')['utc'],
                 evidenceFlow=[dict(kind='calculation',title='Simulation',detail='220 scénarios réellement exécutés sur des acquisitions minute réelles ; paramètres principaux gelés avant le P&L.'),
                               dict(kind='validation',title='Audit',detail='220 exports rapprochés ; 335 136 décisions et 24 352 lignes de trades principaux contrôlées par calcul indépendant.')]),
                 columns=['instrument','cible','rendement_net_pct','sharpe','drawdown_minute_pct'],
                 rows=[dict(instrument=x.instrument,cible=x.leverage_cap,rendement_net_pct=x.total_return_pct,sharpe=x.sharpe,drawdown_minute_pct=x.max_drawdown_pct) for x in bn.itertuples()])])])
    (out/'SOURCES_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    provenance=dict(report_sha256=hashlib.sha256((out/'RAPPORT_FINAL.md').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),manual_checks=nmanual,
                    classification=dict(SPY=3,QQQ=2),data_cutoff='2026-10-16')
    (out/'REPORT_PROVENANCE.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(f'PASS: rapport, {nmanual} calculs historiques et provenance produits depuis les exports audités.')


if __name__=='__main__':main()
