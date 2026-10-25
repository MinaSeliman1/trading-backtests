"""Build the French research report exclusively from completed exported results."""
import argparse
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAIRS = ['GBPUSD', 'USDJPY', 'AUDUSD']


def number(value, places=2):
    if value is None or pd.isna(value):
        return 'n.d.'
    return f'{value:,.{places}f}'.replace(',', ' ').replace('.', ',')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='2026-10-24-python-v1')
    args = parser.parse_args()
    run = ROOT / 'results' / args.run_id
    manifest = json.loads((run / 'RUN_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['complete'], 'Financial runs must be complete'
    df = pd.read_csv(run / 'comparison_all.csv')
    assert len(df) == 126
    quality = json.loads((run / 'data_quality.json').read_text(encoding='utf-8'))
    source = json.loads((ROOT / 'results/2026-10-24-python/source_manifest.json').read_text(encoding='utf-8'))
    minimum = json.loads((run / 'MINIMUM_100.json').read_text(encoding='utf-8'))
    base = df[(df.variant == 'reference') & (df.period == 'ALL')].set_index('pair')
    negative = all(base.loc[p, 'net_pnl'] < 0 for p in PAIRS)
    decision = ('La référence perd de l’argent après frais sur les trois paires. Cette version ne justifie pas de créer un bot de trading.'
                if negative else 'Les résultats restent exploratoires : les contrôles de stabilité, les coûts et la couverture doivent être lus ensemble avant toute décision de bot.')
    parts = [f'''# Nowick / Compensation Play — backtest Python

Exécution `{args.run_id}`, achevée le {manifest['finished_utc']}. Formalisation fournie par Mina, pas une certification d’une autre version de la méthode Bard FX.

**{decision}** Les résultats ci-dessous sont ceux du moteur Python sur archives FXCM, pas des résultats TradingView. Les sorties sur trou sont pénalisées selon une convention explicite ; elles ne sont pas des fills observés.

## Périmètre et seuil demandé

Entrées nominales du 1er janvier 2015 au 31 décembre 2024, même période pour les trois paires. La source s’interrompt notamment du 13 décembre 2024 au 12 janvier 2025 : il n’existe donc pas de couverture continue jusqu’au 31 décembre. Amorçage fin 2014, historique de sortie jusqu’au 24 janvier 2025 ; aucune clôture forcée pour atteindre le nombre de trades.

Le seuil de 100 est vérifié **par paire, sur la référence ALL**, sans additionner les variantes ni les moitiés recouvrantes. « Résolu » exclut toute position traversant une minute absente et toute pénalité de couverture. Objectif atteint sur les trois paires : **{'oui' if minimum['all_three_pass'] else 'non'}**.
''']
    parts.append(table(['Paire', 'Fermés ALL', 'Résolus sans trou', 'Pénalités de couverture', 'Position finale ouverte'],
                       [[p, int(base.loc[p, 'closed_trades']), int(base.loc[p, 'resolved_closed_trades']), int(base.loc[p, 'coverage_penalty_trades']), 'oui' if base.loc[p, 'open_position_end'] else 'non'] for p in PAIRS]))
    parts.append('''
## Règles et coûts conservés

Bougies Bid 15 min constituées de 15 minutes valides ; nouvelles entrées 02:00 incluse–08:00 exclue, America/New_York, heure d’été incluse. Structure de pivots 5/5 confirmés seulement, Nowick sans mèche côté ouverture et tolérance zéro, direction de la tendance. Limite à l’ouverture de la Nowick, valable neuf bougies après sa clôture ; front-run activé. SL au dernier pivot opposé confirmé plus 3 pips, distance 5–30 pips, TP 1R. Une position ou un ordre en attente, risque de prix 1 % du solde au signal, unités entières et plafond de marge 100x. Aucune gestion ultérieure, aucun break-even.

1 pip = 0,0001 sur GBPUSD/AUDUSD et 0,01 sur USDJPY. Le franchissement de limite exige 1 pip, puis le fill reste au prix prévu. Le TP limite exige également cette pénétration, conformément à l’hypothèse globale de limite de la version Pine. Le coût **total synthétique est 1 pip aller-retour**, moitié à l’entrée et moitié à la sortie ; les spreads Ask-Bid archivés ne sont pas ajoutés à nouveau. Les gaps de stop peuvent encore aggraver la perte. Swaps/financement non inclus. Il s’agit d’un modèle de graphique Bid à coûts fixes, pas d’une reconstitution des achats à l’Ask et ventes au Bid d’un courtier réel.

Chaque simulation commence avec 100 000 dans la devise de cotation : **USD** pour GBPUSD/AUDUSD et **JPY** pour USDJPY. Les montants ne constituent pas trois comptes en USD et ne s’additionnent pas comme un portefeuille. Les frais font dépasser 1 % de perte nette même sur un stop ordinaire.

La [spécification figée avant performances](../../PYTHON_PROTOCOL.md) précise les égalités de pivots, les heures complètes de l’EMA, la fraîcheur des signaux, les annulations et la priorité des événements. Aucun paramètre n’a été retenu après observation de sa rentabilité.

## Résultats principaux après frais
''')
    parts.append(table(['Paire', 'Résultat net %', 'PF monétaire', 'Win rate', 'Wilson 95 %', 'Espérance nette R', 'DD marques %', 'DD fermé R', 'Série pertes'],
                       [[p, number(base.loc[p, 'return_pct']), number(base.loc[p, 'profit_factor']), number(base.loc[p, 'win_rate_pct'])+' %', number(base.loc[p, 'wilson_low_pct'])+'–'+number(base.loc[p, 'wilson_high_pct'])+' %', number(base.loc[p, 'expectancy_r'], 3), number(base.loc[p, 'max_marked_dd_pct']), number(base.loc[p, 'max_closed_dd_r']), int(base.loc[p, 'longest_loss_streak'])] for p in PAIRS]))
    parts.append('\nPF = somme des gains nets / somme absolue des pertes nettes. R = risque de prix figé à l’entrée, avant frais. Le drawdown en R porte sur les trades fermés ; le drawdown en % utilise les clôtures minute observées et les événements de fill, pas chaque tick. Wilson suppose des observations binomiales indépendantes : l’intervalle ne corrige pas l’autocorrélation ni les changements de régime.\n')
    parts.append(table(['Paire / devise', 'PnL brut', 'Frais', 'PnL net', 'Solde final', 'CAGR nominal %'],
                       [[p+(' / JPY' if p=='USDJPY' else ' / USD'), *[number(base.loc[p, k]) for k in ['gross_pnl', 'commission', 'net_pnl', 'ending_balance', 'cagr_pct']]] for p in PAIRS]))
    parts.append('\nLe CAGR emploie la durée calendaire nominale de dix ans et le résultat du modèle ; les interruptions de données l’empêchent de représenter dix années d’exécution certifiée. Les comptes et les listes de transactions se trouvent dans les sous-dossiers `PAIRE/ALL/reference/`.\n\n## Deux moitiés chronologiques séparées\n\nA = 2015–2019, B = 2020–2024. Chaque moitié repart de 100 000 avec les mêmes règles et l’historique antérieur pour les indicateurs. Les tailles composées expliquent pourquoi leurs montants ne s’additionnent pas à ALL. B est une validation chronologique des règles fixées ; elle n’est pas présentée comme une nouvelle expérience prospective aveugle.\n')
    rows=[]
    for p in PAIRS:
        for period in ['A','B']:
            r=df[(df.pair==p)&(df.period==period)&(df.variant=='reference')].iloc[0]
            rows.append([p,period,int(r.closed_trades),int(r.resolved_closed_trades),number(r.return_pct),number(r.profit_factor),number(r.expectancy_r,3),number(r.max_marked_dd_pct)])
    parts.append(table(['Paire','Moitié','Fermés','Résolus','Net %','PF','R / trade','DD %'],rows))
    parts.append('\nL’exigence de 100 porte sur chaque paire complète. Les moitiés ou filtres ayant moins de 100 trades restent affichés avec leur taille ; aucun échantillon n’a été gonflé en additionnant des scénarios.\n\n## Coûts et taux de réussite minimal\n')
    parts.append(table(['Paire','1 pip : net %','2 pips : net %','3 pips : net %'],
                       [[p]+[number(df[(df.pair==p)&(df.period=='ALL')&(df.variant==v)].iloc[0].return_pct) for v in ['reference','cost_2pips','cost_3pips']] for p in PAIRS]))
    parts.append('''
Les portefeuilles sont recalculés à chaque coût, y compris la composition des tailles. Sans gap, pour un TP/SL 1:1 et une distance de stop fixe de S pips, avec c pips aller-retour : `E[R] = 2p − 1 − c/S`. Seuil de rentabilité : **p > (1 + c/S)/2**. À 1 pip de frais : 60 % pour un stop de 5 pips, 55 % à 10 pips, 51,67 % à 30 pips. Avec des stops variables, il faut tenir compte du coût relatif moyen et de la dépendance entre taille du stop et résultat ; « plus de 50 % » ne suffit pas. Les pénalités/gaps augmentent encore l’exigence.

## Filtres et sensibilités fixés à l’avance

Référence : filtres Swing, S/R et Double OFF. Chaque filtre est activé séparément, puis les trois ensemble. Le filtre S/R recherche les pivots opposés confirmés dans les 100 dernières bougies. Le Double compare les signaux acceptés de même sens espacés de 2 à 4 bougies. Un filtre peut modifier les positions disponibles et donc augmenter le nombre ultérieur de trades ; les portefeuilles sont simulés à nouveau.
''')
    labels={'reference':'Référence','swing_on':'Swing ON','sr_on':'S/R ON','double_on':'Double ON','filters_all':'Trois filtres ON','ema_1h':'EMA 50/200 1h','mid_body':'Milieu du corps','rr_1_5':'TP 1,5R','rr_2':'TP 2R','front_run_off':'Front-run OFF'}
    rows=[]
    for name,label in labels.items():
        row=[label]
        for p in PAIRS:
            r=df[(df.pair==p)&(df.period=='ALL')&(df.variant==name)].iloc[0]
            row.append(f'{int(r.closed_trades)} / {number(r.return_pct)} % / {number(r.expectancy_r,3)} R')
        rows.append(row)
    parts.append(table(['Variante : n / net % / R moyen']+PAIRS,rows))
    parts.append('\nToutes les variantes et les moitiés figurent dans [comparison_all.csv](comparison_all.csv), soit 126 exécutions recouvrantes. Ce ne sont pas 126 preuves indépendantes. Les variantes à petit n ne permettent pas de sélectionner un gagnant fiable. **News : non évalué**, faute de calendrier daté fourni et archivé ; aucune liste de nouvelles n’a été inventée, filtre OFF dans toutes les exécutions.\n\n## Incertitude d’exécution et trous\n\nL’open de chaque minute est connu avant ses extrêmes. Si le front-run et le retest sont dans une même minute sans ordre temporel certain, la référence annule et `fill_first` remplit d’abord. L’annulation n’est pas une borne garantie du PnL. Quand SL et TP sont tous deux possibles sur une minute de position ouverte, le stop prime. Après un fill intraminute, une seule mèche favorable ne prouve pas un TP postérieur au fill.\n')
    rows=[]
    for p in PAIRS:
        r=base.loc[p]
        f=df[(df.pair==p)&(df.period=='ALL')&(df.variant=='fill_first')].iloc[0]
        o=df[(df.pair==p)&(df.period=='ALL')&(df.variant=='observed_gap')].iloc[0]
        rows.append([p,int(r.front_run_ambiguous_setups),number(r.return_pct),number(f.return_pct),number(o.return_pct),int(r.coverage_penalty_trades),number(r.coverage_penalty_net_pnl),number(r.resolved_only_net_pnl_diagnostic)])
    parts.append(table(['Paire','Front-run ambigus','Annuler %','Fill d’abord %','Gaps observés %','Pénalités n','PnL pénalités','PnL résolus seul*'],rows))
    parts.append('''
Au premier open valide suivant une minute absente, la référence ferme une position au pire du stop ou de cet open, avec frais complets, sous l’étiquette `COVERAGE_GAP_STOP`. Cette **pénalité de couverture** est une hypothèse, pas un ordre exécuté ni une borne universelle sur des prix inconnus. Une limite en attente est annulée sur trou. La sensibilité `observed_gap` conserve les positions sur les quotes disponibles et les signale : elle ne résout pas ce qui s’est passé dans le trou.

*Le PnL des seuls trades résolus est un diagnostic en devise de cotation des tailles originales, pas un portefeuille recréé en supprimant les autres trades. Les pénalités ne sont donc pas cachées en excluant les pertes. Les valeurs des autres variantes sont également soumises à leur propre nombre de trous, disponible dans leurs summaries.

## Qualité et provenance des données

[FXCM MarketData officiel](https://github.com/fxcm/MarketData) et [exemple officiel de lecture des candles](https://github.com/fxcm/MarketData/blob/master/CandleData/CandleData%28pandas%29.py). Archives `https://candledata.fxcorporate.com/m1/{PAIR}/{YEAR}/{WEEK}.csv.gz`, timestamps UTC. 1 620 archives demandées : 1 579 reçues et 41 réponses 404, sans erreur de téléchargement restante. Empreintes par archive dans le [manifest d’acquisition](../2026-10-24-python/source_manifest.json).

FXCM décrit ces quotes comme indicatives ; elles ne garantissent pas un prix accessible chez le courtier de l’utilisateur. Les historiques intégraux restent locaux et ignorés par Git ; le dépôt contient les résultats dérivés et leurs preuves. Aucun abonnement ni clé API n’est utilisé.
''')
    rows=[]
    for p in PAIRS:
        q=quality[p]
        # Acquisition schema is stable but retain only information proven by that manifest.
        rows.append([p,number(q['weekday_window_coverage_pct']),int(q['complete_360minute_days']),int(q['weekday_days']),int(q['zero_quote_weekdays']),int(q['missing_weekday_window_minutes'])])
    parts.append(table(['Paire','Minutes présentes %','Jours complets 360 min','Jours ouvrés nominaux','Jours sans quote','Minutes absentes'],rows))
    parts.append('''
L’enveloppe de couverture compte chaque lundi–vendredi 02:00–08:00 New York, y compris jours fériés : elle mesure des observations, pas un calendrier certifié de marché négociable. Aucune minute n’est forward-fill. Les trous empêchent les signaux incomplets ; une fenêtre de pivot doit comporter 11 bougies complètes et consécutives. Les égalités de pivots utilisent une convention explicite non certifiée par un compilateur Pine.

Les trois flux présentent notamment les interruptions communes suivantes : 30 juin–9 juillet 2023, 23 août–1er septembre 2024, 13 décembre 2024–12 janvier 2025. Les dates et vingt plus grands écarts par paire sont dans [data_quality.json](data_quality.json). Les fichiers de couverture journalière rendent les autres absences visibles. Ces trous peuvent aussi supprimer des opportunités qui auraient eu lieu ; une pénalité sur les positions connues ne les reconstitue pas.

Les OHLC non finis, non positifs ou incohérents sont refusés comme barres valides ; les doublons conflictuels provoquent un arrêt. L’acquisition obtenue ne comporte aucun OHLC Bid/Ask invalide ni doublon. Des quotes de clôture Ask inférieures au Bid existent : GBPUSD 25 742, USDJPY 31 193, AUDUSD 25 074. Ce défaut interdit de traiter le spread archivé comme une preuve de fill réel ; le modèle principal utilise la seule série Bid et son coût synthétique explicite.

## Répartition et concentration
''')
    years=[]; directions=[]
    for p in PAIRS:
        t=pd.read_csv(run/p/'ALL/reference/trades.csv')
        t['entry_year']=pd.to_datetime(t.entry_time_utc,utc=True).dt.year
        for year,g in t.groupby('entry_year'):
            years.append({'pair':p,'entry_year':int(year),'closed_trades':len(g),'wins':int((g.net_pnl>0).sum()),'net_pnl':float(g.net_pnl.sum()),'sum_r':float(g.net_r.sum())})
        for direction,g in t.groupby('d'):
            directions.append({'pair':p,'direction':'LONG' if direction==1 else 'SHORT','closed_trades':len(g),'net_pnl':float(g.net_pnl.sum()),'mean_r':float(g.net_r.mean())})
    pd.DataFrame(years).to_csv(run/'reference_by_entry_year.csv',index=False)
    pd.DataFrame(directions).to_csv(run/'reference_by_direction.csv',index=False)
    parts.append(table(['Paire','LONG n / PnL','SHORT n / PnL','Trois meilleurs gains','Net moins ces gains*','Durée ≥24 h'],
                       [[p]+[f"{int(next(x for x in directions if x['pair']==p and x['direction']==d)['closed_trades'])} / {number(next(x for x in directions if x['pair']==p and x['direction']==d)['net_pnl'])}" for d in ['LONG','SHORT']]+[number(base.loc[p,'top3_positive_pnl']),number(base.loc[p,'net_less_top3_cash_diagnostic']),int(base.loc[p,'overnight_24h_trades'])] for p in PAIRS]))
    parts.append('''
*Soustraction comptable, pas une nouvelle simulation de capital. Les répartitions par année d’entrée et direction sont exportées à côté du rapport. « Durée ≥24 h » n’est pas synonyme de passage à la date New York suivante ; une sortie avant 24 h peut néanmoins être overnight. Le modèle n’ajoute aucun swap.

## Figures

![Capital net](figures/equity_reference.png)

![Stabilité chronologique](figures/chronological_expectancy.png)

![Coûts](figures/cost_sensitivity.png)

![Couverture](figures/coverage_monthly.png)

![Filtres](figures/filter_comparison.png)

## Validation, reproduction et portée

70 tests contrôlés couvrent décodage des archives, unités et timestamps, confirmations de pivots, EMA 1h, sessions/DST, validité des limites, front-run, priorités stop/TP, frais, risques et trous. Ils comprennent les 27 tests de référence précédents et deux régressions de préservation des données lors d’une reproduction refusée ; ils ne compilent pas le Pine. Le drawdown a été corrigé avant toute exécution de marché pour intégrer les frais dès l’entrée ; une régression reproduit le défaut puis vérifie le correctif.

La revue indépendante et les calculs Decimal/math sont conservés dans [audit](../../audit/). Le script d’audit n’importe pas les helpers de calcul du moteur pour vérifier les comptes. Voir [VALIDATION_PYTHON.md](../../VALIDATION_PYTHON.md) pour le périmètre exact, les compteurs et les limites ; un audit d’échantillons ne devient pas une relecture manuelle de toutes les minutes.

[RUN_MANIFEST.json](RUN_MANIFEST.json) conserve paramètres et empreintes figés avant les performances ; [DEPENDENCY_PROVENANCE.json](DEPENDENCY_PROVENANCE.json) complète l’empreinte du helper `reference.py`, inchangé par rapport au commit antérieur. Les snapshots de code rendent cette version reproductible. Le [guide de l’étude](../../README.md) donne les commandes. L’intégrité de publication est inventoriée dans `FILE_MANIFEST.json` ; les exécutions historiques précédentes ne sont pas remplacées.

Les biais restants sont l’historique incomplet et indicatif, la résolution minute qui ne donne pas l’ordre des ticks, l’absence de swaps, un coût fixe qui ne varie pas lors des annonces et les files d’attente/latences de limites non simulées. Les paires partagent des risques USD et ne sont pas des réplications indépendantes. La compilation Pine et la parité TradingView restent non vérifiées.

## Décision
''')
    parts.append(decision+' Aucun passage automatique en réel. Une autre formalisation ou une nouvelle source devrait faire l’objet d’un nouveau protocole et d’une nouvelle exécution, sans effacer cette version ni sélectionner ici un filtre après coup.\n')
    (run/'RAPPORT_FINAL.md').write_text('\n\n'.join(parts),encoding='utf-8',newline='\n')
    print('French report and entry-year/direction tables generated from 126 executed exports.')


if __name__=='__main__':
    main()
