"""Rapport et figures a partir des exports audites, sans optimisation."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'intraday-momentum-noise-area'))
import argparse,json,hashlib
from decimal import Decimal
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def table(frame):
    columns=list(frame.columns);lines=['| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
    for values in frame.itertuples(index=False,name=None):
        formatted=[f'{v:,.2f}'.replace(',',' ') if isinstance(v,(float,np.floating)) else str(v) for v in values]
        lines.append('| '+' | '.join(formatted)+' |')
    return '\n'.join(lines)


def source_excerpt(out,selected,features):
    profile=json.loads((out/'DATA_SOURCE_PROFILE.json').read_text());quotes=[];max_error=0.
    for symbol,trades in selected.items():
        requests=[];f=features[symbol]
        for row in trades.itertuples():
            at=pd.Timestamp(row.entry_time);until=pd.Timestamp(row.exit_time);idx=int(f.loc[f.date==row.date,'index'].iloc[0]);prev=f.iloc[idx-1]
            points=[('morning',pd.Timestamp(row.date+' 09:59',tz='America/New_York'),'close',row.morning_close),
                ('previous_close',pd.Timestamp(prev.session_close)-pd.Timedelta(minutes=1),'close',row.previous_close),
                ('sizing',at-pd.Timedelta(minutes=1),'close',row.sizing_price),('entry',at,'open',row.entry_reference),('exit',until,'open',row.exit_reference)]
            requests.extend((row.date,role,time.tz_convert('UTC'),field,want) for role,time,field,want in points)
        dates={str(at.date()) for _,_,at,_,_ in requests};parts=[]
        for acquisition in profile['raw_acquisitions']:
            if not Path(acquisition['path']).name.startswith(symbol+'_'):continue
            for chunk in pd.read_csv(ROOT.parents[2]/acquisition['path'],usecols=['timestamp','open','high','low','close','volume'],float_precision='round_trip',chunksize=200000):
                subset=chunk.loc[chunk.timestamp.str[:10].isin(dates)].copy()
                if len(subset):parts.append(subset)
        raw=pd.concat(parts,ignore_index=True);raw['timestamp']=pd.to_datetime(raw.timestamp,utc=True,format='mixed');raw=raw.drop_duplicates()
        assert not raw.timestamp.duplicated().any(),'Conflicting raw excerpt timestamps'
        raw=raw.set_index('timestamp')
        for date,role,at,field,want in requests:
            found=raw.loc[at];error=abs(float(found[field])-float(want));max_error=max(max_error,error);assert error<1e-10,(symbol,date,role,error)
            quotes.append(dict(symbol=symbol,trade_date=date,role=role,timestamp_utc=at.isoformat(),**found.to_dict()))
    pd.DataFrame(quotes).to_csv(out/'raw_ohlcv_excerpts.csv',index=False)
    proof=dict(status='passed',selected_transactions=sum(len(t) for t in selected.values()),raw_bars_compared=len(quotes),maximum_price_error=max_error,
        fields='Morning close, immediate previous-session close, completed sizing-minute close, entry open, exit open, all re-read from hashed raw CSVs.',
        limitation='Selected deterministic examples only; full Decimal audit separately covers every exported trade using prepared arrays.')
    (out/'RAW_EXCERPT_AUDIT.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return proof


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20-v2');args=p.parse_args(argv);out=args.out
    audit=json.loads((out/'AUDIT_INDEPENDANT.json').read_text());assert audit['status']=='passed'
    comparison=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');primary=comparison[(comparison['mode']=='momentum')&(comparison.slippage==.01)].copy()
    features={s:pd.read_csv(out/f'{s}_quality.csv',float_precision='round_trip') for s in ('SPY','QQQ')}
    select=lambda s,p,m='momentum',slip=.01:comparison[(comparison.symbol==s)&(comparison.period==p)&(comparison['mode']==m)&(comparison.slippage==slip)].iloc[0]
    daily=lambda s,p,m='momentum':pd.read_csv(out/f'{s}_{p}_{m}_s0.01/daily.csv',float_precision='round_trip')
    trades=lambda s,p:pd.read_csv(out/f'{s}_{p}_momentum_s0.01/trades.csv',float_precision='round_trip')
    figdir=out/'figures';figdir.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    colors=['#204f8d','#247950','#b36b00','#7c518c'];names=['Momentum LONG/SHORT','Signal LONG seul','LONG systématique (quantités communes)','Signal inversé (quantités communes)']
    for period in ('ALL','B'):
        fig,axes=plt.subplots(2,1,figsize=(10,7.5),layout='constrained',sharex=True,sharey=True)
        for ax,s in zip(axes,('SPY','QQQ')):
            for mode,name,color in zip(('momentum','long_only','always_long','opposite'),names,colors):
                d=daily(s,period,mode);ax.plot(pd.to_datetime(d.date),d.equity,label=name,color=color,lw=1.3)
            ax.axhline(100000,color='#777777',lw=.7,ls='--');ax.set_ylabel(s+' — capital net USD');ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best')
        fig.suptitle(f'Momentum de clôture — {period}, friction 0,01 USD/action/côté\nHistorique exploratoire réutilisé ; témoins à quantités communes')
        fig.savefig(figdir/f'equity_{period}.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained');x=np.arange(4)
    for j,s in enumerate(('SPY','QQQ')):
        values=[select(s,'B',slip=slip).total_return_pct for slip in (.01,.02,.03,.05)]
        bars=ax.bar(x+(j-.5)*.36,values,width=.36,label=s,color=colors[j]);ax.bar_label(bars,fmt='%.2f%%',padding=3,fontsize=9)
    ax.axhline(0,color='black',lw=.7);ax.set_xticks(x,['0,01','0,02','0,03','0,05']);ax.set_xlabel('Friction adverse USD/action/côté, plus commission et emprunt');ax.set_ylabel('Rendement net B (%)');ax.set_title('Sensibilité aux coûts — 01/05/2024–16/10/2026');ax.legend();ax.grid(axis='y',alpha=.2)
    fig.savefig(figdir/'cost_sensitivity_B.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    for j,s in enumerate(('SPY','QQQ')):
        annual=pd.read_csv(out/f'{s}_ALL_momentum_s0.01/by_year.csv');ax.bar(np.arange(len(annual))+(j-.5)*.36,annual.return_pct,width=.36,label=s,color=colors[j])
    ax.axhline(0,color='black',lw=.7);ax.set_xticks(np.arange(len(annual)),annual.year.astype(str));ax.set_ylabel('Rendement annuel net (%)');ax.set_title('Scénarios principaux — années 2016 à 2026 (2026 partielle)');ax.legend();ax.grid(axis='y',alpha=.2)
    fig.savefig(figdir/'annual_returns.png',dpi=150);plt.close(fig)
    selected={};manual=['# Examen reproductible de transactions','Sélection déterministe : deux plus gros gains, deux plus grosses pertes, première ex-date, première demi-séance, premier SHORT et dernière transaction de chaque instrument. Cette sélection illustrée ne constitue pas un échantillon aléatoire. Les cinq prix de référence sont relus dans les CSV bruts hachés ; les calculs complets sont audités séparément.']
    for s in ('SPY','QQQ'):
        t=trades(s,'ALL');sample=pd.concat([t.nlargest(2,'net_pnl'),t.nsmallest(2,'net_pnl'),t[t.dividend>0].head(1),t[t.half_session].head(1),t[t.sign<0].head(1),t.tail(1)]).drop_duplicates('date').sort_values('date');selected[s]=sample
        visible=sample[['date','direction','morning_return','quantity','entry_reference','exit_reference','commission','borrow_fee','net_pnl']].copy()
        visible['morning_return']=visible.morning_return.map(lambda x:f'{x*100:.4f} %')
        manual.extend(['',f'## {s}',table(visible.rename(columns={'morning_return':'Signal incluant overnight'}))])
        for row in sample.itertuples():
            raw=Decimal(str(row.quantity))*Decimal(str(row.sign))*(Decimal(str(row.exit_reference))-Decimal(str(row.entry_reference)))
            net=raw-Decimal(str(row.friction_cost))-Decimal(str(row.commission))-Decimal(str(row.borrow_fee))
            assert abs(net-Decimal(str(row.net_pnl)))<Decimal('.000001')
            manual.append(f'\n{row.date} : signal {row.morning_return*100:.4f} %, {row.direction}, {row.quantity} actions ; mouvement {float(raw):.4f} USD − friction {row.friction_cost:.4f} − commissions {row.commission:.4f} − emprunt {row.borrow_fee:.4f} = **{float(net):.4f} USD net**. Entrée {row.entry_time} ; sortie {row.exit_time}.')
    rawproof=source_excerpt(out,selected,features);(out/'EXAMEN_TRANSACTIONS.md').write_text('\n\n'.join(manual)+'\n',encoding='utf-8')
    sections=['# Momentum de clôture — rapport final, référence v2',
        '**Décision : cette version LONG/SHORT ne justifie pas un nouveau bot.** Les deux scénarios principaux perdent après frais en A et B, et sur ALL. La variante LONG seule de QQQ devient positive en B, mais reste négative sur ALL et ne surpasse pas le témoin LONG sur ce même créneau. Aucun paramètre n’est ajusté après observation. Le bot Noise Area actif est indépendant de cette étude.',
        '## Question, source et exécution',
        'Tester le signe du rendement entre la clôture NYSE précédente corrigée du dividende et la clôture 09:59, puis prendre ce sens à l’open 15:30 et sortir à l’open 15:59. Demi-séances : 12:30–12:59. Maintien réel de **29 minutes**. Quantité entière à cible 1x selon le capital net et la clôture de la minute précédant l’entrée. Le signal inclut l’overnight ; aucun stop ni objectif. [Protocole figé et précisions](../../PROTOCOL_EXECUTION.md).',
        'La littérature motive l’hypothèse de momentum intrajournalier ; notre sortie avant clôture et les ETF ne constituent pas une réplication exacte des enchères ou des futures étudiés. [Source primaire des auteurs](https://academicweb.nd.edu/~zda/intramom.pdf). Le délai de publication de 15:29 peut empêcher d’obtenir exactement l’open 15:30 ; la friction adverse ne prouve pas cette faisabilité.',
        '## Données et qualité',
        'Alpaca SIP raw, acquisitions locales vérifiées : les six empreintes des caches et les six CSV bruts concordent avec DATA_VALIDATION de Noise Area. Calendrier XNYS continu, tableaux float64, heures et demi-séances contrôlées. Les dividendes SPY proviennent de l’émetteur rapproché dans la validation précédente ; QQQ utilise les événements Alpaca dédoublonnés. Le journal d’actions d’origine, interrogé sans filtre de type, ne retourne aucun split ; sa complétude n’a pas été confirmée par un audit indépendant de l’émetteur. [Profil et empreintes](DATA_SOURCE_PROFILE.json).',
        'Les minutes du matin, la clôture précédente immédiate et la minute de taille doivent être valides. Les trous intermédiaires inutiles au signal n’excluent pas le jour. Une sortie requise manquante fait échouer le calcul plutôt que fabriquer du cash. Les trous pendant le maintien sont conservés et limitent le drawdown observé. [Qualité SPY](SPY_quality.csv), [qualité QQQ](QQQ_quality.csv).',
        '## Périodes et coûts',
        'ALL : 04/01/2016–16/10/2026 ; A : jusqu’au 30/04/2024 ; B : 01/05/2024–16/10/2026. Chaque période repart séparément de 100 000 USD. A/B/ALL se recouvrent et ne sont pas des validations indépendantes. B réutilise un historique déjà analysé ; **ce n’est pas un nouvel échantillon aveugle**. Aucun résultat prospectif n’est produit ici.',
        'Commission 0,0035 USD/action/côté, minimum 0,35 USD/ordre ; friction adverse 0,01 USD/action/côté, stress 0,02/0,03/0,05 ; SHORT 1 %/360 sur l’entrée après friction, un jour minimum. Pas d’intérêt sur cash ni tarif réglementaire distinct. Disponibilité du prêt, rejets et fills réels non observés. Ces coûts restent hypothétiques.',
        '## Résultats principaux',
        table(primary[['symbol','period','trades','total_return_pct','cagr_pct','net_pnl','max_daily_close_drawdown_pct','observed_close_drawdown_pct','sharpe','profit_factor']].rename(columns={'symbol':'Instrument','period':'Période','trades':'Trades','total_return_pct':'Net %','cagr_pct':'CAGR %','net_pnl':'Net USD','max_daily_close_drawdown_pct':'DD quotidien %','observed_close_drawdown_pct':'DD minute observé %','sharpe':'Sharpe','profit_factor':'Profit factor'})),
        'Le drawdown minute utilise les clôtures observées pendant la position, la friction d’entrée, la commission puis la sortie nette. Il n’est ni un drawdown tick par tick ni une garantie sur le risque maximal. La MAE par highs/lows est fournie dans les trades ; ces extrema ne constituent pas un chemin de prix ordonné.',
        '![Capital B](figures/equity_B.png)',
        '![Capital ALL](figures/equity_ALL.png)',
        '## Frictions et variantes prédéfinies',
        table(comparison[(comparison.period=='B')&(comparison.role=='strategy')][['symbol','mode','slippage','trades','total_return_pct','net_pnl']].rename(columns={'symbol':'Instrument','mode':'Règle','slippage':'Friction','trades':'Trades','total_return_pct':'Net B %','net_pnl':'Net USD'})),
        '![Coûts B](figures/cost_sensitivity_B.png)',
        '## Témoins à mêmes quantités',
        table(comparison[(comparison.period=='B')&((comparison.role=='reference')|((comparison['mode']=='momentum')&(comparison.slippage==.01)))][['symbol','mode','trades','total_return_pct','net_pnl']].rename(columns={'symbol':'Instrument','mode':'Règle','trades':'Trades','total_return_pct':'Net B %','net_pnl':'Net USD'})),
        'Les quantités cibles du principal sont héritées par LONG systématique et signal inversé à friction 0,01. Leur capital propre ne redimensionne pas leurs entrées ; ces témoins isolent le sens, et ne sont pas des stratégies investissables maintenues chacune à 1x. Le LONG prend les séances à signal nul, l’inversé reste plat. Aucun chemin n’est insolvable dans l’audit. Aucune combinaison n’est optimisée.',
        '## Coûts, sens et exposition',
        table(primary.assign(max_actual_entry_leverage=primary.max_actual_entry_leverage.map(lambda x:f'{x:.6f}'))[['symbol','period','price_move_pnl','friction_cost','commission','borrow_fee','days_with_position_pct','regular_time_exposure_pct','max_actual_entry_leverage']].rename(columns={'symbol':'Instrument','period':'Période','price_move_pnl':'Mouvement USD','friction_cost':'Friction USD','commission':'Commission USD','borrow_fee':'Emprunt USD','days_with_position_pct':'Séances exposées %','regular_time_exposure_pct':'Temps RTH exposé %','max_actual_entry_leverage':'Levier effectif max'})),
        'La cible 1x calculée avant entrée peut être légèrement dépassée après un changement de prix. Chaque dossier de scénario publie les ventilations par sens, année et demi-séance. Les coûts dégradent les résultats ; leur décomposition comptable ne démontre pas la cause économique d’une absence de prévisibilité.',
        '## Régimes annuels et concentration',
        '![Rendements annuels](figures/annual_returns.png)',
        table(primary[['symbol','period','return_without_top3_days_pct','top3_positive_profit_share_pct','worst_trade_usd','half_session_trades','trades_with_missing_holding_minutes']].rename(columns={'symbol':'Instrument','period':'Période','return_without_top3_days_pct':'Sans 3 meilleurs jours %','top3_positive_profit_share_pct':'3 meilleurs / profits positifs %','worst_trade_usd':'Pire trade USD','half_session_trades':'Trades demi-séance','trades_with_missing_holding_minutes':'Trades maintien incomplet'})),
        'L’ablation met à zéro les rendements des trois meilleurs jours positifs, en conservant tous les autres rendements et tailles historiques ; elle ne simule pas un nouveau portefeuille redimensionné. Les 2026 annuelles sont partielles.',
        '## Incertitude']
    intervals=[]
    for s in ('SPY','QQQ'):
        u=json.loads((out/f'{s}_B_uncertainty.json').read_text());annual=u['annual_cluster']['mean_trade_bps_ci95']
        for block in ('5','20'):
            b=u['paired_blocks'][block];low,high=b['daily_mean_ci95'];dl,dh=b['mean_minus_long_ci95']
            intervals.append(dict(Instrument=s,Bloc=int(block),Moyenne_bps_basse=low*10000,Moyenne_bps_haute=high*10000,Ecart_LONG_bps_bas=dl*10000,Ecart_LONG_bps_haut=dh*10000))
        sections.append(f'{s} B : intervalle 95 % par années entières sur la moyenne nette par transaction **[{annual[0]:.3f}, {annual[1]:.3f}] bps**, avec seulement trois années partiellement ou totalement observées.')
    sections.extend(['Le tableau suivant mesure la moyenne du **rendement quotidien du capital**, en points de base, et son écart quotidien au témoin LONG. Les intervalles annuels ci-dessus mesurent la moyenne **par transaction**, rapportée au notionnel engagé.',table(pd.DataFrame(intervals).rename(columns={'Moyenne_bps_basse':'Moyenne quotidienne basse (bps)','Moyenne_bps_haute':'Moyenne quotidienne haute (bps)','Ecart_LONG_bps_bas':'Écart quotidien LONG bas (bps)','Ecart_LONG_bps_haut':'Écart quotidien LONG haut (bps)'})),
        '3 000 réplications, graine 20261020 ; blocs circulaires de 5/20 séances alignées et années entières. Les intervalles sont descriptifs, supposent des dépendances compatibles avec ces rééchantillonnages, sans correction pour les variantes examinées. B réutilisée, trois groupes annuels et changements de régime empêchent d’en tirer une garantie de rentabilité. Les chiffres négatifs ne sont pas transformés en preuve universelle contre le mécanisme publié.',
        '## Audit et reproductibilité',
        f'Audit indépendant Decimal : **{audit["executions"]} exécutions, {audit["trade_rows"]:,} lignes de transactions et {audit["minute_marks"]:,} points de capital contrôlés**, erreur monétaire maximale {audit["max_currency_error_usd"]:.3g} USD. Le nombre de lignes se recouvre entre A/B/ALL et variantes ; il ne mesure pas des événements indépendants. [Preuve](AUDIT_INDEPENDANT.json).',
        f'Les exemples détaillés contrôlent {rawproof["selected_transactions"]} transactions et {rawproof["raw_bars_compared"]} références relues dans les CSV bruts, écart maximal {rawproof["maximum_price_error"]:.3g}. [Examen explicite](EXAMEN_TRANSACTIONS.md), [extraits bruts limités](raw_ohlcv_excerpts.csv), [preuve](RAW_EXCERPT_AUDIT.json).',
        'Les tests synthétiques ne sont pas des données de performance. Le moteur et l’audit n’envoient aucun ordre et ne modifient pas le bot. La première exécution reste conservée ; v2 corrige localement la durée du drawdown quand plusieurs pics sont identiques ou la période est plate. Les règles, transactions et P&L sont inchangés entre versions. Les résultats historiques Noise Area/FVG restent intacts.',
        'Les 42 scénarios passent aussi les rapprochements secondaires des coûts totaux, ratios, exposition, ablation, CAGR, Sharpe, rendements/comptes annuels, sens, demi-séances et durée corrigée du drawdown. [Rapprochements](AGGREGATE_VALIDATION.json). Ces contrôles utilisent les exports déjà audités ; les intervalles Monte-Carlo disposent de tests contrôlés et de limites explicites, sans certification statistique indépendante. [42 comparaisons](comparison_all.csv), [gel avant exécution](PRE_EXECUTION_PROTOCOL.json), [manifest initial](MANIFEST.json).',
        '## Conclusion pratique',
        'Archiver cette version comme piste négative après coûts. Ne pas créer un bot de trading sur la base de ces résultats et ne pas retenir QQQ LONG seul uniquement parce que B est positive. Le protocole jusqu’à 15:29 décrit en extension reste une hypothèse distincte à geler avant son propre test ; il ne corrige pas rétroactivement cet essai. Le suivi prospectif Noise Area QQQ continue avec ses propres preuves.'])
    exceptions=[];coverage=[]
    for symbol,f in features.items():
        f=f[f.date>='2016-01-04'];e=f[f.eligibility!='eligible'][['date','eligibility']].copy();e.insert(0,'Instrument',symbol);exceptions.append(e)
        coverage.append(dict(Instrument=symbol,Seances=len(f),Admissibles=int(f.eligibility.eq('eligible').sum()),Exclues=len(e),Signaux_nuls_admissibles=int(((f.eligibility=='eligible')&(f.signal_sign==0)).sum())))
    excluded=pd.concat(exceptions,ignore_index=True);excluded.to_csv(out/'EXCLUSIONS.csv',index=False)
    at=sections.index('## Périodes et coûts');sections[at:at]=[table(pd.DataFrame(coverage)),table(excluded.rename(columns={'date':'Date','eligibility':'Motif causal'})),
        'La première séance 2016 est exclue faute de clôture précédente exploitable. Les journées avec interruption du matin restent exclues sans minute interpolée. Les signaux strictement nuls sont des jours admissibles mais plats pour le principal ; ils expliquent l’écart de comptage avec le témoin LONG. [Exclusions exportées](EXCLUSIONS.csv).']
    (out/'RAPPORT_FINAL.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    previous=ROOT/'results/2026-10-20/comparison_all.csv'
    if previous.exists():
        old=pd.read_csv(previous,float_precision='round_trip').set_index('label');new=comparison.set_index('label');diff={}
        for column in new.columns:
            if column=='worst_drawdown_duration_calendar_days':continue
            assert old[column].equals(new[column]),('unexpected version change',column)
        for row in comparison.itertuples():
            for name in ('trades.csv','daily.csv'):
                assert (ROOT/'results/2026-10-20'/row.label/name).read_bytes()==(out/row.label/name).read_bytes(),('version trade path change',row.label,name)
        (out/'VERSION_COMPARISON.json').write_text(json.dumps(dict(status='passed',previous='2026-10-20',reference=out.name,identical_fields_except=['worst_drawdown_duration_calendar_days'],all_trade_and_daily_files_identical=True,reason='Local drawdown duration correction only'),indent=2)+'\n',encoding='utf-8')
    files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='DELIVERY_MANIFEST.json'}
    (out/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),files=files),indent=2)+'\n',encoding='utf-8')
    print('REPORT COMPLETE',out,flush=True)


if __name__=='__main__':main()
