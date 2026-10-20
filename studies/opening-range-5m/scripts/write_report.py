"""Rapport des specifications figees, extraits bruts et quatre figures."""
from pathlib import Path
import sys,json,hashlib
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]


def table(df):
    lines=['| '+' | '.join(df.columns)+' |','|'+'|'.join(['---']*len(df.columns))+'|']
    for row in df.itertuples(index=False,name=None):lines.append('| '+' | '.join(f'{x:.3f}' if isinstance(x,(float,np.floating)) else str(x) for x in row)+' |')
    return '\n'.join(lines)


def excerpts(out,selected):
    profile=json.loads((out/'DATA_SOURCE_PROFILE.json').read_text());quotes=[]
    for symbol,t in selected.items():
        requests=[]
        for row in t.itertuples():
            opening=pd.Timestamp(row.entry_time)-pd.Timedelta(minutes=5)
            requests.extend((row.date,'opening_'+str(j),opening+pd.Timedelta(minutes=j)) for j in range(5))
            requests.extend([(row.date,'entry',pd.Timestamp(row.entry_time)),(row.date,'exit',pd.Timestamp(row.exit_time))])
        dates={str(at.date()) for _,_,at in requests};parts=[]
        for a in profile['raw_acquisitions']:
            if not Path(a['path']).name.startswith(symbol+'_'):continue
            path=ROOT.parents[2]/a['path'];digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==a['sha256']
            for chunk in pd.read_csv(path,usecols=['timestamp','open','high','low','close','volume'],float_precision='round_trip',chunksize=200000):
                sub=chunk[chunk.timestamp.str[:10].isin(dates)]
                if len(sub):parts.append(sub)
        raw=pd.concat(parts,ignore_index=True).drop_duplicates();raw['timestamp']=pd.to_datetime(raw.timestamp,utc=True,format='mixed')
        assert not raw.timestamp.duplicated().any();raw=raw.set_index('timestamp')
        prepared=ROOT.parent/'intraday-momentum-noise-area/data/prepared'/f'{symbol}_market.pkl'
        assert hashlib.sha256(prepared.read_bytes()).hexdigest()==profile['prepared_files_sha256'][prepared.name]
        import pickle
        with prepared.open('rb') as stream:m=pickle.load(stream)
        for date,role,at in requests:
            found=raw.loc[at.tz_convert('UTC')];i=int(np.flatnonzero(m.dates==pd.Timestamp(date))[0]);j=int((at-pd.Timestamp(m.quality.iloc[i].session_open)).total_seconds()/60)
            for k in ('open','high','low','close','volume'):assert abs(float(found[k])-float(m.arrays[k][i,j]))<1e-10
            quotes.append(dict(symbol=symbol,trade_date=date,role=role,timestamp_utc=at.tz_convert('UTC').isoformat(),**found.to_dict()))
    pd.DataFrame(quotes).to_csv(out/'raw_ohlcv_excerpts.csv',index=False)
    proof=dict(status='passed',selected_transactions=sum(len(t) for t in selected.values()),raw_bar_references=len(quotes),ohlcv_values_compared=len(quotes)*5,maximum_absolute_error=0,
        scope='Five first bars, entry and exit minute: all OHLCV fields re-read from six hashed raw CSVs and compared to prepared arrays. Repeated minute roles allowed.',
        limitation='Deterministic examples, single provider; not proof of tick ordering, actual fills or absence of provider price errors.')
    (out/'RAW_EXCERPT_AUDIT.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');return proof


def main(out):
    # noise_area.data is needed only for verified historical pickle deserialization.
    sys.path.insert(0,str(ROOT.parent/'intraday-momentum-noise-area'))
    c=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');audit=json.loads((out/'INDEPENDENT_AUDIT.json').read_text());assert audit['status']=='passed'
    primary=c[(c['mode']=='both')&(c.quality=='complete_days')&(c.priority=='stop_first')&(c.slippage==.01)]
    choose=lambda s,p,slip=.01,mode='both':c[(c.symbol==s)&(c.period==p)&(c['mode']==mode)&(c.quality=='complete_days')&(c.priority=='stop_first')&(c.slippage==slip)].iloc[0]
    daily=lambda r:pd.read_csv(out/r.label/'daily.csv');trades=lambda r:pd.read_csv(out/r.label/'trades.csv',float_precision='round_trip')
    figdir=out/'figures';figdir.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    modes=['both','long_only','short_only','inverse'];names=['Signal LONG/SHORT','LONG seul','SHORT seul','Signal inversé, risque recalculé'];colors=['#245a8d','#248452','#b16e11','#8357a0']
    for p in ('ALL','B'):
        fig,axes=plt.subplots(2,1,figsize=(10,7.5),layout='constrained',sharex=True)
        for ax,s in zip(axes,('SPY','QQQ')):
            for mode,name,color in zip(modes,names,colors):
                d=daily(choose(s,p,mode=mode));ax.plot(pd.to_datetime(d.date),d.equity,label=name,color=color,lw=1.2)
            ax.axhline(100000,color='#666666',ls='--',lw=.7);ax.set_ylabel(s+' — capital net USD');ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.suptitle(f'ORB cinq minutes — comptes historiques conditionnels, {p}\nFriction 0,01 USD/action/côté ; sélection de qualité connue après coup')
        fig.savefig(figdir/f'equity_{p}.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');x=np.arange(4)
    for ax,p in zip(axes,('ALL','B')):
        for j,s in enumerate(('SPY','QQQ')):
            bars=ax.bar(x+(j-.5)*.36,[choose(s,p,slip=z).total_return_pct for z in (.01,.02,.03,.05)],width=.36,label=s,color=colors[j]);ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=8)
        ax.axhline(0,color='black',lw=.7);ax.set_xticks(x,['0,01','0,02','0,03','0,05']);ax.set_xlabel('Friction USD/action/côté');ax.set_ylabel('Rendement net conditionnel (%)');ax.set_title(p);ax.grid(axis='y',alpha=.2);ax.margins(y=.18);ax.legend()
    fig.suptitle('Sensibilité aux coûts — commissions et emprunt inclus')
    fig.savefig(figdir/'cost_sensitivity.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    for j,s in enumerate(('SPY','QQQ')):
        annual=pd.read_csv(out/choose(s,'ALL').label/'by_year.csv');ax.bar(np.arange(len(annual))+(j-.5)*.36,annual.return_pct,width=.36,label=s,color=colors[j])
    ax.axhline(0,color='black',lw=.7);ax.set_xticks(np.arange(len(annual)),annual.year.astype(str));ax.set_ylabel('Rendement net conditionnel (%)');ax.legend();ax.grid(axis='y',alpha=.2);ax.set_title('ORB LONG/SHORT — années 2016–2026 (2026 partielle)')
    fig.savefig(figdir/'annual_returns.png',dpi=150);plt.close(fig)
    selected={};manual=['# Exemples reproductibles','Huit dates uniques par instrument : deux gains extrêmes, deux pertes extrêmes, première demi-séance, première ex-date, première ambiguïté si disponible sinon premier SHORT, dernier trade ; compléter avec les premières dates si doublon. Sélection descriptive non aléatoire.']
    prep=ROOT.parent/'intraday-momentum-noise-area/data/prepared'
    exclusions=[]
    for s in ('SPY','QQQ'):
        r=choose(s,'ALL');t=trades(r);divs=json.loads((prep/f'{s}_dividends.json').read_text())
        exdates=set(divs.keys()) if isinstance(divs,dict) else set()
        candidates=pd.concat([t.nlargest(2,'net_pnl'),t.nsmallest(2,'net_pnl'),t[t.half_session].head(1),t[t.date.isin(exdates)].head(1),(t[t.ambiguous_bar] if t.ambiguous_bar.any() else t[t.sign<0]).head(1),t.tail(1),t.head(10)]).drop_duplicates('date').head(8).sort_values('date');selected[s]=candidates
        manual+=['',f'## {s}',table(candidates[['date','direction','quantity','entry_reference','stop_price','target_price','exit_reference','exit_reason','net_pnl']])]
        for row in candidates.itertuples():manual.append(f'{row.date} : {row.entry_time} → {row.exit_time}, {row.direction} {row.quantity} actions ; mouvement {row.price_move_pnl:.6f} − friction {row.friction_cost:.6f} − commissions {row.commission:.6f} − emprunt {row.borrow_fee:.6f} = **{row.net_pnl:.6f} USD**. Sortie {row.exit_resolution} ; MAE/MFE partiellement observées {row.mae_observed_usd:.3f}/{row.mfe_observed_usd:.3f} USD.')
        d=daily(r);e=d[d.conditionally_excluded][['date','eligibility']].copy();e.insert(0,'Instrument',s);exclusions.append(e)
    raw=excerpts(out,selected);(out/'EXAMEN_TRANSACTIONS.md').write_text('\n\n'.join(manual)+'\n',encoding='utf-8')
    excluded=pd.concat(exclusions,ignore_index=True);excluded.to_csv(out/'DATA_EXCLUSIONS.csv',index=False)
    headers={'symbol':'Instrument','period':'Période','trades':'Trades','total_return_pct':'Net %','cagr_pct':'CAGR %','observed_close_drawdown_pct':'DD minute observé %','sharpe':'Sharpe','profit_factor':'Profit factor'}
    sections=['# ORB cinq minutes — rapport final SPY/QQQ',
        '**QQQ mérite une observation prospective supplémentaire ; ces résultats ne suffisent pas à justifier un nouveau bot. SPY ne convainc pas.** QQQ principal gagne 7,759 % en B et 50,933 % sur ALL, à exposition théorique plafonnée à 1x et coûts de base. Mais retirer ses trois meilleurs jours B donne −0,938 %, doubler/tripler la friction fragilise le long historique, et les intervalles descriptifs B couvrent zéro. Aucun paramètre n’est modifié après calcul.',
        '**Portée : comptes historiques conditionnels à la couverture des données.** Le filtre principal exige une séance entièrement observée, information disponible après la clôture : cette sélection ne peut pas être appliquée telle quelle à 09:35. Les journées exclues sont omises du compte, avec `observed_return=NaN` et zéro uniquement comptable dans `return_net`. Aucune performance continue d’un portefeuille réel traversant toutes les journées n’est revendiquée. B n’a pas d’exclusion de données pour ces instruments, mais reste un historique déjà étudié, sans validation aveugle.',
        '## Hypothèse et méthode',
        'Version simplifiée de l’Opening Range Breakout présentée par [Zarattini et Aziz, pp. 4–6](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf). Direction de la bougie 09:30–09:34 ; entrée à l’open 09:35 ; stop au plus bas/haut initial et objectif 10R. L’entrée est immédiate après la plage initiale, sans attendre une cassure ultérieure. Notre capital de 100 000 USD, plafond 1x, coûts, taille causale et sortie à 15:59/12:59 diffèrent du papier ; aucune réplication exacte ni performance publiée attribuée à ce test.',
        'Quantité entière fixée avant entrée : minimum entre capital/close09:34 et 1 % du capital/risque au stop connu, arrondi inférieur. Le gap peut changer le levier effectif et dépasser le budget de risque ; pas de redimensionnement avec un open futur. Objectif calculé sur le risque de référence après fill, pas le prix après friction. Une entrée au-delà du stop reste un aller-retour immédiat coûté. Un objectif SHORT négatif est logiquement inatteignable, sans fill inventé.',
        'Open de chaque minute d’abord : stop dépassé rempli au prix open, objectif dépassé au niveau cible conservateur ; puis high/low, STOP prioritaire si les deux barrières sont touchées. TARGET prioritaire est une sensibilité séparée. La minute de sortie intrabar ne révèle pas la seconde ; son close et ses extrêmes postérieurs possibles sont exclus des marks. MAE/MFE partiellement observées et drawdown aux closes observés ne mesurent pas le risque tick. [Contrat complet](../../PROTOCOL_EXECUTION.md).',
        '## Périodes, sources et frais',
        'ALL : 04/01/2016–16/10/2026 ; A jusqu’au 30/04/2024 ; B du 01/05/2024 au 16/10/2026. Chaque instrument/période recommence à 100 000 USD. A/B/ALL et variantes se recouvrent. Les 54 lignes et leurs trades ne sont pas indépendants. **B réutilisée n’est pas un nouveau hors-échantillon aveugle.**',
        'Alpaca SIP raw local : six CSV et six caches vérifiés par SHA, calendrier XNYS continu, float64, demi-séances/heures vérifiées. Aucune clé dans le dépôt. Les actions sur titres ont été rapprochées dans la validation source ; aucun split n’est retourné par la requête d’origine, sans certification de complétude indépendante du fournisseur. Le signal n’utilise aucune clôture précédente, donc aucun ajustement overnight pour dividende. [Provenance](DATA_SOURCE_PROFILE.json).',
        'Commission par côté max(0,35 USD ; 0,0035×actions), friction adverse 0,01 USD/action/côté, stress 0,02/0,03/0,05 ; SHORT 1 %/360 du notionnel d’entrée après friction, un jour minimum. Cash non rémunéré. Pas de frais réglementaires séparés, disponibilité du prêt, spread observé, latence, rejets ni fills réels. La friction constitue une hypothèse, pas une mesure ni garantie d’exécution. L’open 09:35 peut être inaccessible après publication de close09:34.',
        '## Principaux résultats conditionnels',table(primary[['symbol','period','trades','total_return_pct','cagr_pct','observed_close_drawdown_pct','sharpe','profit_factor']].rename(columns=headers)),
        '![Comptes B](figures/equity_B.png)','![Comptes ALL](figures/equity_ALL.png)',
        '## Sensibilité aux coûts et aux règles',
        table(c[(c['mode']=='both')&(c.quality=='complete_days')&(c.priority=='stop_first')][['symbol','period','slippage','trades','total_return_pct']].rename(columns={**headers,'slippage':'Friction USD/côté'})),
        '![Frais](figures/cost_sensitivity.png)',
        'Toutes les variantes sont publiées dans [comparison_all.csv](comparison_all.csv). LONG seul, SHORT seul et inverse sont des diagnostics prédéfinis. L’inverse possède son propre stop, quantité et heure de sortie ; la comparaison n’isole donc pas le sens à exposition identique et ne démontre pas un alpha face à buy-and-hold.',
        table(c[(c.period=='B')&(c.slippage==.01)][['symbol','mode','quality','priority','trades','total_return_pct']].rename(columns=headers)),
        '## Couverture et exclusions',table(excluded),
        'Des minutes manquent autour de certains arrêts de mars 2020, mais aussi d’autres jours sans suspension établie. La [NYSE décrit les interruptions de mars 2020](https://www.nyse.com/article/assessing-nyse-model-performance) ; cette information ne justifie pas d’interpoler les trous du fournisseur. Une sonde historique SIP en lecture seule sur QQQ du 02/02/2016 n’a récupéré aucune des neuf minutes manquantes. Aucune bougie n’a été fabriquée.',
        table(c[(c['mode']=='both')&(c.priority=='stop_first')&(c.slippage==.01)][['symbol','period','quality','data_excluded_sessions','unresolved_sessions','trades','total_return_pct']].rename(columns=headers)),
        'La sensibilité `resolved_prefix` conserve un trade résolu avant un trou ultérieur. Un trou pendant le maintien ou à l’entrée rend l’exécution indéterminable ; tout le trade est omis du compte conditionnel, y compris frais connus, qui restent décrits dans `unresolved.csv`. Ce compte n’est pas un traitement de production des pannes de données. [Audit des intentions non résolues](INDEPENDENT_UNKNOWN_AUDIT.csv).',
        '## Risque, coût et exposition',table(primary[['symbol','period','price_move_pnl','friction_cost','commission','borrow_fee','regular_time_exposure_upper_pct','max_actual_entry_leverage','max_entry_risk_pct','entry_risk_over_one_pct_count','ambiguous_trades']].rename(columns=headers)),
        'Exposition temps = minutes maintenues / minutes de séances, borne supérieure à une minute près lors d’une sortie intraminute. Risque à l’entrée = distance au stop × quantité / capital avant entrée ; il exclut frais et gaps futurs. Le budget de 1 % ne garantit pas une perte maximale de 1 %. Une seule barre ambiguë sur QQQ ALL/A explique la sensibilité TARGET ; SPY et B n’en ont aucune dans les principaux.',
        '## Années, concentration et incertitude','![Années](figures/annual_returns.png)',
        table(primary[['symbol','period','return_without_top3_days_pct','top3_positive_profit_share_pct','worst_trade_usd','worst_observed_mae_usd','half_session_trades']].rename(columns=headers)),
        'Retirer les trois meilleurs jours positifs met leurs rendements à zéro puis recompose les autres rendements quotidiens conservés. Diagnostic algébrique sans nouvelle simulation ni redimensionnement ; ce n’est pas une trajectoire à quantités fixes et les P&L originaux ne sont pas conservés. Les exports par année/sens/demi-séance/motif de sortie permettent de contrôler la stabilité. 2026 est partielle.']
    intervals=[]
    for s in ('SPY','QQQ'):
        u=json.loads((out/f'{s}_B_uncertainty.json').read_text());lo,hi=u['annual_cluster']['mean_trade_bps_ci95'];sections.append(f'{s} B : IC descriptif 95 % de la moyenne **par transaction** par groupes annuels : [{lo:.3f}, {hi:.3f}] bps du notionnel engagé, seulement trois groupes 2024–2026 partiellement/complètement observés.')
        for block in ('5','20'):
            lo,hi=u['blocks'][block]['conditional_daily_mean_ci95'];intervals.append(dict(Instrument=s,Bloc=int(block),Moyenne_quotidienne_basse_bps=lo*10000,Moyenne_quotidienne_haute_bps=hi*10000))
    sections += [table(pd.DataFrame(intervals)),'Le tableau mesure la moyenne **quotidienne du rendement du capital conditionnel**, unité différente du rendement moyen par trade. Blocs circulaires 5/20 séances, 3 000 répétitions, graine 20261020 ; années sans événement conservées dans le rééchantillonnage annuel. Zéros comptables des exclusions inclus. Intervalles descriptifs sans correction pour essais multiples ; peu de groupes, dépendances et historique réutilisé empêchent une conclusion robuste de rentabilité.',
        '## Validation et reproduction',
        f'Audit indépendant depuis les OHLCV source : **{audit["executions"]} exécutions, {audit["trade_rows"]} lignes recouvrantes, {audit["independent_source_marks"]} marks**. Écart maximal sur champs monétaires par trade {audit["max_currency_trade_field_error_usd"]:.3g} USD ; capital cumulé {audit["max_capital_error_usd"]:.3g} USD ; drawdown monétaire {audit["max_drawdown_usd_error"]:.3g} USD et {audit["max_drawdown_pct_error"]:.3g} point de pourcentage. Tolérance capital/agrégats : 3×10⁻⁶. Signaux, taille Decimal, stops/cibles, ordre des événements, frais, capital, exclusions et DD observé reconstruits sans appeler le moteur. [Preuve et unités détaillées](INDEPENDENT_AUDIT.json), [détail](INDEPENDENT_TRADE_AUDIT.csv).',
        f'42 tests synthétiques ; rapprochements secondaires des 54 exports. {raw["selected_transactions"]} exemples, {raw["raw_bar_references"]} références minute et {raw["ohlcv_values_compared"]} valeurs OHLCV relues dans les CSV hachés, écart nul. [Exemples](EXAMEN_TRANSACTIONS.md), [preuve brute](RAW_EXCERPT_AUDIT.json). Ces contrôles vérifient notre traitement du même fournisseur, pas son exactitude contre une source indépendante ni l’ordre des ticks.',
        'Code et protocole figés avant première boucle financière : [gel](PRE_EXECUTION_PROTOCOL.json), [copie du code](code_snapshot), [manifest initial](MANIFEST.json). Les scripts d’audit/rapport sont écrits après ce gel et tracés dans le manifest de livraison. Une seconde instrumentation d’audit sépare les écarts par unité et mesure le capital cumulé ; sa preuve initiale reste archivée. Les 449 empreintes initiales concordent : aucun correctif numérique du moteur, des statistiques ou des résultats après P&L ni réglage pour retenir une variante. [Guide et tests](../../README.md).',
        '## Décision',
        'Conserver QQQ comme piste exploratoire à tester prospectivement avec données complètes et coûts d’exécution observés ; ne pas remplacer Noise Area ni lancer de nouveau bot avec cet essai seul. Le rendement QQQ de base est positif, mais son CAGR ALL de 3,891 %, le DD observé de 14,229 %, la dépendance aux frais et aux meilleurs jours B et les IC couvrant zéro limitent son intérêt. SPY est trop faible après coûts. Aucun argent réel, ordre paper ou réglage du bot actif n’est produit par cette étude.']
    (out/'RAPPORT_FINAL.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    print('REPORT READY',raw)


if __name__=='__main__':main(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/2026-10-20')
