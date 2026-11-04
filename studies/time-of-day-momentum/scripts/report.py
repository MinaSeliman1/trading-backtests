"""Post-export presentation only: tables and standalone matplotlib figures."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from seasonal.data import source


def number(v,d=2):
    if v is None or pd.isna(v):return 'n/a'
    return f'{float(v):.{d}f}'


def table(df,columns):
    lines=['| '+' | '.join(label for key,label in columns)+' |','|'+'---|'*len(columns)]
    for row in df.to_dict('records'):
        lines.append('| '+' | '.join(str(row[key]) if isinstance(row[key],str) else number(row[key],0 if key in ('trades','data_excluded_sessions','unresolved_sessions') else 4 if key in ('max_modeled_fill_leverage','max_entry_risk_pct','max_modeled_stop_net_risk_pct') else 2) for key,label in columns)+' |')
    return lines


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);out=p.parse_args().out.resolve();df=pd.read_csv(out/'comparison_all.csv');screen=json.loads((out/'SCREENING.json').read_text());audit=json.loads((out/'INDEPENDENT_AUDIT.json').read_text());extra=json.loads((out/'ADDITIONAL_CHECKS.json').read_text());frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text());profile=json.loads((out/'DATA_SOURCE_PROFILE.json').read_text());figs=out/'figures';figs.mkdir(exist_ok=True)
    assert len(df)==96 and audit['accounts']==96 and audit['all_matched'] and extra['passed']
    df['max_modeled_fill_leverage']=np.nan
    for ix,row in df.loc[(df.variant=='reference')&(df.period=='ALL')].iterrows():
        df.loc[ix,'max_modeled_fill_leverage']=pd.read_csv(out/f"{row['symbol']}_ALL_reference/trades.csv").entry_fill_leverage.max()
    plt.rcParams.update({'figure.dpi':150,'axes.grid':True,'grid.alpha':.2,'font.size':9})
    symbols=('SPY','QQQ');colors=['#1266A4','#D9822B','#6B6B6B','#8A6FB0'];controls=('reference','control_same_clock_long','control_fixed_clock','control_random_clock')
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for ax,symbol in zip(axes,symbols):
        for name,color in zip(controls,colors):
            d=pd.read_csv(out/f'{symbol}_ALL_{name}/daily.csv');ax.plot(pd.to_datetime(d.date),d.equity/1000,label={'reference':'Référence','control_same_clock_long':'Achat au même créneau','control_fixed_clock':'Même sens à 10:00','control_random_clock':'Même sens, horaire aléatoire'}[name],color=color,linewidth=1)
        ax.set_title(symbol+' — comptes historiques conditionnels, pas portefeuille observé continu');ax.set_ylabel('Capital, milliers USD');ax.legend(fontsize=7,ncol=2)
    fig.tight_layout();fig.savefig(figs/'equity_and_controls.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,symbol in zip(axes,symbols):
        d=pd.read_csv(out/f'{symbol}_ALL_reference/by_year.csv');x=np.arange(len(d));ax.bar(x,d.return_pct,color=np.where(d.return_pct>=0,'#1266A4','#B64C45'));ax.axhline(0,color='black',linewidth=.6);ax.set_xticks(x,d.year.astype(str),rotation=45);ax.set_title(symbol+' — référence par année');ax.set_ylabel('Rendement net (%)')
    fig.tight_layout();fig.savefig(figs/'yearly_returns.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,symbol in zip(axes,symbols):
        for period,color in zip(('A','B','ALL'),colors):
            subset=df.loc[(df.symbol==symbol)&(df.period==period)&df.variant.isin(['reference','cost_0.02','cost_0.03','cost_0.05'])].sort_values('slippage');ax.plot(subset.slippage,subset.total_return_pct,marker='o',label=period,color=color)
        ax.axhline(0,color='black',linewidth=.6);ax.set_title(symbol);ax.set_xlabel('Friction par action et par côté (USD)');ax.set_ylabel('Rendement net (%)');ax.legend()
    fig.tight_layout();fig.savefig(figs/'cost_sensitivity.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,symbol in zip(axes,symbols):
        d=pd.read_csv(out/f'{symbol}_random_clock_draws.csv');summary=json.loads((out/f'{symbol}_random_clock_panel.json').read_text());ax.hist(d.normalized_net_usd/1000,bins=35,color='#8BAAC1');ax.axvline(summary['normalized_reference_total_usd']/1000,color='#B64C45',label='Référence');ax.set_title(symbol+' — 1 000 horaires aléatoires');ax.set_xlabel('Somme P&L normalisé, milliers USD');ax.set_ylabel('Tirages');ax.legend()
    fig.suptitle('Capital constant 100 000 USD chaque jour, pas 1 000 comptes composés',fontsize=10);fig.tight_layout();fig.savefig(figs/'random_clock_controls.png');plt.close(fig)
    tests=ET.parse(ROOT/'runtime/preflight-tests.xml').getroot();suites=list(tests.iter('testsuite'));testresult=dict(tests=sum(int(s.get('tests',0)) for s in suites),failures=sum(int(s.get('failures',0)) for s in suites),errors=sum(int(s.get('errors',0)) for s in suites),scope='Synthetic causal, execution, statistics, delivery and full96-account runner tests before market PnL')
    assert testresult['tests']>=47 and testresult['failures']==0 and testresult['errors']==0;source.write_json(out/'TESTS.json',testresult)
    refs=df.loc[df.variant=='reference'].copy();refs['period']=pd.Categorical(refs.period,['A','B','ALL']);refs=refs.sort_values(['symbol','period'])
    lines=['# Rapport final — saisonnalité au même créneau : QQQ et SPY','',
      '**Conclusion : la référence ne justifie aucun nouveau bot dans cette formalisation.** Les décisions restent celles du protocole figé avant le premier calcul de marché ; aucun réglage gagnant n’a été substitué après lecture des résultats.','',
      'Cette étude cherche une persistance du rendement à la même heure sur 40 séances passées. Source primaire : [Heston/Korajczyk/Sadka](https://arxiv.org/abs/1005.3535). Leur résultat porte sur des classements transversaux d’actions ; notre règle par ETF, son seuil statistique et ses stops sont une adaptation, pas une réplication. [Recherche élargie et alternatives](../../RESEARCH.md).','',
      'Données SIP 1 minute, séances du 4 janvier 2016 au 16 octobre 2026. A se termine le 30 avril 2024 ; B commence le 1er mai 2024. A et B ont déjà été réutilisées par de nombreuses études du dépôt : **B n’est pas une nouvelle validation aveugle**. Comptes indépendants de 100 000 USD, taille décidée avant fill, plafond cible 1x / risque 1 %. Prix bruts, pas de nuit ni intérêt de cash.','',
      '## Résultats de référence après les mêmes frais','']
    lines+=table(refs,[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net cumulé %'),('cagr_pct','CAGR %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD observé %'),('win_rate_pct','Win rate %')])
    lines+=['','Ces rendements sont **conditionnels aux données résolues**. Les dates inconnues ne sont pas des journées cash observées. Le drawdown est celui des marques/closes tenus et de la sortie simulée, pas du pire tick.','', '## Règles et coûts','',
      'À chaque séance, choisir le premier créneau 10:00–15:00 dont le rendement des 40 séances précédentes donne |moyenne/erreur-type|>=1,5. Le sens et le créneau historiques sont connus avant l’ouverture. À la décision, stop à 2 sigma estimés à l’avance, prix de taille dernier close connu ; entrée une minute plus tard, puis stop ou sortie à l’open 30 minutes après l’entrée. Un trade/jour, aucune réentrée, aucun objectif optimisé. Les créneaux tardifs sont retirés quand le calendrier annonce une demi-séance.','',
      'Commission max(0,35 USD, 0,0035 USD/action) **par côté**, friction adverse 0,01 USD/action/côté, emprunt SHORT 1 %/360 avec minimum un jour. Stress 0,02/0,03/0,05. Le prix d’ouverture futur ne redimensionne pas l’ordre ; gaps, entrée déjà au-delà du stop et deux côtés de coûts sont conservés. [Protocole exact](../../PROTOCOL_EXECUTION.md).','', '## Attribution du résultat ALL','']
    lines+=table(df.loc[(df.variant=='reference')&(df.period=='ALL')],[('symbol','ETF'),('price_move_pnl','Mouvements prix USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('borrow_fee','Emprunt USD'),('net_pnl','Net USD')])
    lines+=['','Cette attribution conserve les quantités du trajet après frais. Elle ne constitue pas un nouveau compte sans frais recalculé. Les coûts ne sont soustraits qu’une fois.','', '## Témoins et incertitude','',
      'Trois témoins causaux conservent la candidature historique : achat systématique au même créneau, même sens à 10:00, même sens à une heure SHA-seedée avant la séance. Quantités, stops, durée et coûts suivent les mêmes règles. Comparaisons appariées sur couverture commune ; bootstrap circulaire 3 000 tirages avec blocs 5/20 sur le calendrier en gardant les dates inconnues masquées. Les anciennes CI de zéros comptables restent descriptives ; le critère économique utilise seulement les observations connues avec pondération de leur nombre dans chaque bloc.','']
    for symbol in symbols:
        u=json.loads((out/f'{symbol}_ALL_uncertainty.json').read_text());ci=u['observed_calendar_blocks']['blocks']['20']['mean_ci95'];lines+=['### '+symbol,'',f"Moyenne quotidienne nette observée, IC95 blocs 20 : [{ci[0]*10000:.4f}, {ci[1]*10000:.4f}] points de base ; {u['observed_calendar_blocks']['observed_sessions']} séances connues sur {u['observed_calendar_blocks']['calendar_sessions']} calendaires.",'','| Témoin | Jours appariés | Jours où les deux tradent | Écart moyen net, pb/jour | IC95 blocs 20, pb/jour | p unilatéral |','|---|---:|---:|---:|---|---:|']
        pairs=json.loads((out/f'{symbol}_ALL_controls.json').read_text())
        for name,v in pairs.items():
            ci=v['uncertainty']['blocks']['20']['mean_ci95'];lines.append(f"| {name} | {v['paired_sessions']} | {v['paired_signal_dates']} | {number(v['mean_difference_bps'],4)} | [{ci[0]*10000:.4f}, {ci[1]*10000:.4f}] | {number(v['p_one_sided'],4)} |")
        s=screen['results'][symbol];lines+=['',f"p d’intersection (maximum des 3 comparaisons)={s['intersection_raw_p']:.6f}, p Holm parmi les 2 ETF={s['holm_p']:.6f}. Critères satisfaits : {sum(s['criteria'].values())}/{len(s['criteria'])}. Statut de référence : {'candidat historique seulement' if s['passes_all'] else 'critères non satisfaits'}.",'']
    lines+=['La correction Holm concerne cette étude seulement. Elle ne corrige pas le choix de cette hypothèse ni toutes les recherches antérieures. Les CI restent conditionnelles à la couverture et aux très nombreuses décisions de recherche déjà prises.','', '## Panneau de 1 000 horaires aléatoires','',
      'Diagnostic à **capital constant 100 000 USD chaque jour**, référence normalisée de la même manière. Ce ne sont pas 1 000 comptes composés. Sous-ensemble conditionnel où toutes les heures compatibles avec le calendrier ont un historique et une trajectoire résolus ; dates exclues publiées. Aucun choix du meilleur seed.','']
    for symbol in symbols:
        x=json.loads((out/f'{symbol}_random_clock_panel.json').read_text());lines.append(f"- {symbol} : {x['paired_signal_dates']} dates appariées, {x['excluded_signal_dates']} candidates retirées ; référence normalisée {x['normalized_reference_total_usd']:.2f} USD, médiane hasard {x['random_total_usd_median']:.2f} USD, rang {x['reference_percentile_rank_pct']:.2f} %, fraction supérieure {x['random_upper_tail_probability']:.4f}.")
    lines+=['','## Couverture, risque et concentration','']
    lines+=table(df.loc[(df.variant=='reference')&(df.period=='ALL')],[('symbol','ETF'),('data_excluded_sessions','Séances exclues'),('unresolved_sessions','Trajets non résolus'),('return_without_top3_days_pct','Net sans top3 %'),('max_modeled_fill_leverage','Levier max au fill modélisé'),('max_entry_risk_pct','Risque prix max %'),('max_modeled_stop_net_risk_pct','Risque stop+coûts max %')])
    for symbol in symbols:
        d=pd.read_csv(out/f'{symbol}_ALL_reference/daily.csv');counts=d.eligibility.value_counts().to_dict();lines+=['',symbol+' — statuts des séances : '+', '.join(f'{k}={v}' for k,v in counts.items())+'.']
    lines+=['','complete_days utilise la complétude de la journée actuelle, information disponible après coup : le signal causal est choisi avant ce filtre et ne bouge pas. resolved_prefix retire ce filtre mais conserve les informations requises avant entrée et pendant la position. En cas de trajet inconnu, le trade entier est omis du résultat résolu et ses coûts d’entrée connus sont conservés dans unresolved.csv. La mémoire de 40 séances propage aussi les lacunes historiques ; ces exclusions ne représentent pas une disponibilité continue.','',
       'Les erreurs de prix, corrections ultérieures, spreads variables, faible liquidité, prêt de titres, rejets/partiels et absence de carnet ne sont pas reproduits par ces barres. Le plafond 1x et le risque 1 % sont des cibles au prix connu avant fill, pas des garanties après gap.','', '## Toutes les variantes ALL','']
    pivot=df.loc[df.period=='ALL'].pivot(index='variant',columns='symbol',values='total_return_pct').reset_index();lines+=table(pivot,[('variant','Variante'),('SPY','SPY net %'),('QQQ','QQQ net %')]);lines+=['','Une variante ou un témoin positif isolé reste un diagnostic exploratoire. Aucun nouveau modèle n’est choisi ni installé après ces résultats. Les références A/B/ALL, tous les stress et tous les témoins restent disponibles dans comparison_all.csv.','', '## Figures','',
       '![Comptes et témoins](figures/equity_and_controls.png)','', '![Années](figures/yearly_returns.png)','', '![Frais](figures/cost_sensitivity.png)','', '![Horaires aléatoires](figures/random_clock_controls.png)','', '## Validation et reproduction','',
       f"{testresult['tests']} tests synthétiques passés avant le premier P&L de marché. Oracle séparé : {audit['accounts']} comptes, {audit['features_checked']} lignes de features, {audit['daily_rows_checked']} journées et {audit['trades_checked']} trades comparés, avec quantité, sens, prix, stops, coûts, emprunt, capital composé et drawdown. Les sources de l’oracle sont distinctes du moteur financier mais utilisent les mêmes caches vérifiés : ce n’est pas un deuxième fournisseur.", '',
       f"Préenregistrement publié avant calcul : commit `{frozen['git_commit']}`, reçu daté {frozen['utc']}. Archives, caches, code, dépendances et protocoles hachés ; vérification des sources courantes ET des snapshots avant audit et livraison. Les scripts supplémentaires de présentation/contrôle d’exports sont ajoutés après calcul et distingués du gel financier ; le manifest final les inclut.", '',
       f"Contrôle statistique supplémentaire : {extra['bootstrap_comparisons']} reconstructions indépendantes de bootstrap, appariements/Holm et deux panneaux de 1 000 tirages reconstruits. Les données brutes restent locales et sous licence ; le dépôt publie les exports dérivés, pas les clés ou les fichiers OHLC complets.", '',
       '```powershell','python -m pytest studies/time-of-day-momentum/tests -q --junitxml=studies/time-of-day-momentum/runtime/preflight-tests.xml','python studies/time-of-day-momentum/scripts/run_study.py --out studies/time-of-day-momentum/results/nouvelle_execution','python studies/time-of-day-momentum/audit/independent.py --out studies/time-of-day-momentum/results/nouvelle_execution','python studies/time-of-day-momentum/scripts/additional_checks.py --out studies/time-of-day-momentum/results/nouvelle_execution','python studies/time-of-day-momentum/scripts/report.py --out studies/time-of-day-momentum/results/nouvelle_execution','python studies/time-of-day-momentum/scripts/verify_delivery.py --out studies/time-of-day-momentum/results/nouvelle_execution --seal','```','',
       'Configurer PYTHONPATH vers les dépendances locales ou installer les versions de requirements-lock.txt dans un environnement séparé. Le loader s’appuie sur les caches vérifiés existants ; le runner refuse d’écraser une exécution. TESTS.json de la livraison est extrait du JUnit préexécution ; pour reproduire le rapport avec cette commande, enregistrer préalablement le JUnit à runtime/preflight-tests.xml comme indiqué dans le README.','',
       '[96 comparaisons](comparison_all.csv) · [Critères](SCREENING.json) · [Gel](PRE_EXECUTION_PROTOCOL.json) · [Sources](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](INDEPENDENT_AUDIT.json) · [Contrôles supplémentaires](ADDITIONAL_CHECKS.json). Aucun résultat TradingView, fill broker, nouveau bot ou avantage prospectif n’est revendiqué.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print('Report and four figures generated.')
if __name__=='__main__':main()
