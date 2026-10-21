"""Rapport, figures et extraits des pages gzip originales, sans optimisation."""
from pathlib import Path
import sys,json,gzip,hashlib,re
from decimal import Decimal
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from vwap_reversion.data import load_sources
D=lambda x:Decimal(str(x))


def table(df):
    lines=['| '+' | '.join(df.columns)+' |','|'+'|'.join(['---']*len(df.columns))+'|']
    for row in df.itertuples(index=False,name=None):lines.append('| '+' | '.join(f'{x:.3f}' if isinstance(x,(float,np.floating)) else str(x) for x in row)+' |')
    return '\n'.join(lines)


def excerpts(out,selected,markets,profile):
    requests={};date_sets={};found={};quotes=[];max_error=0.
    for symbol,t in selected.items():
        requests[symbol]={};date_sets[symbol]=set(t.date)
        for r in t.itertuples():
            start=pd.Timestamp(r.entry_time)-pd.Timedelta(minutes=60)
            for j in range(r.exit_slot+1):requests[symbol][(start+pd.Timedelta(minutes=j)).value]=(r.date,j)
    for p in profile['vwap_source']['basis']['pages']:
        symbol=p['symbol'];path=ROOT.parents[2]/p['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']
        with gzip.open(path,'rt',encoding='utf-8') as stream:body=json.load(stream)
        bars=body['bars'];bars=bars[symbol] if isinstance(bars,dict) else bars
        for b in bars:
            if b['t'][:10] not in date_sets[symbol]:continue
            at=pd.Timestamp(b['t']).value;key=(symbol,at)
            if at not in requests[symbol]:continue
            if key in found:assert found[key]==b
            found[key]=b
    for symbol,t in selected.items():
        m=markets[symbol];indices={str(x.date()):i for i,x in enumerate(m.dates)}
        for at,(date,j) in requests[symbol].items():
            b=found[(symbol,at)];i=indices[date]
            for key,raw in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v'),('vwap','vw')]:
                error=abs(float(b[raw])-float(m.arrays[key][i,j]));max_error=max(max_error,error);assert error<1e-10
            quotes.append(dict(symbol=symbol,trade_date=date,slot=j,timestamp_utc=pd.Timestamp(at,tz='UTC').isoformat(),**{k:b[v] for k,v in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v'),('vwap','vw')]}))
        for r in t.itertuples():
            start=pd.Timestamp(r.entry_time)-pd.Timedelta(minutes=60)
            first=[found[(symbol,(start+pd.Timedelta(minutes=j)).value)] for j in range(60)]
            mean=sum((D(b['vw'])*D(b['v']) for b in first),D(0))/sum((D(b['v']) for b in first),D(0))
            assert abs(float(mean)-r.vwap_at_signal)<1e-10
            if r.exit_reason=='vwap_next_open':
                prior=[found[(symbol,(start+pd.Timedelta(minutes=j)).value)] for j in range(r.exit_slot)]
                mean=sum((D(b['vw'])*D(b['v']) for b in prior),D(0))/sum((D(b['v']) for b in prior),D(0))
                assert r.sign*(D(prior[-1]['c'])-mean)>=0
    pd.DataFrame(quotes).to_csv(out/'raw_ohlcv_vwap_excerpts.csv',index=False)
    proof=dict(status='passed',selected_transactions=sum(len(t) for t in selected.values()),raw_minute_bars=len(quotes),numeric_fields_checked=len(quotes)*6,max_absolute_error=max_error,
        scope='Entire selected session prefixes through exit, original gzip OHLCV and vw vs prepared arrays; first-hour weighted VWAP and close-triggered VWAP exits recalculated from raw.',
        limitation='Deterministic sample, one provider; full exit bar fields are raw context and may postdate fill, never used as postexit marks. Other dates and previous20 ranges rely on full data extraction/audit separately.')
    (out/'RAW_EXCERPT_AUDIT.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');return proof


def main(out):
    audit=json.loads((out/'INDEPENDENT_AUDIT.json').read_text(encoding='utf-8'));assert audit['status']=='passed'
    c=pd.read_csv(out/'comparison_all.csv',float_precision='round_trip');main=c[(c['mode']=='both')&(c.quality=='complete_days')&(c.exit_policy=='vwap')&(c.slippage==.01)]
    choose=lambda s,p,slip=.01,mode='both',exit='vwap':c[(c.symbol==s)&(c.period==p)&(c['mode']==mode)&(c.quality=='complete_days')&(c.exit_policy==exit)&(c.slippage==slip)].iloc[0]
    daily=lambda r:pd.read_csv(out/r.label/'daily.csv');trades=lambda r:pd.read_csv(out/r.label/'trades.csv',float_precision='round_trip')
    figures=out/'figures';figures.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    specs=[('both','vwap','Retour VWAP LONG/SHORT'),('long_only','vwap','LONG seul'),('short_only','vwap','SHORT seul'),('both','eod_only','Même entrée, stop/EOD sans sortie VWAP')];colors=['#245d8b','#258255','#b07419','#82539d']
    for period in ('ALL','B'):
        fig,axes=plt.subplots(2,1,figsize=(10,7.5),sharex=True,layout='constrained')
        for ax,s in zip(axes,('SPY','QQQ')):
            for (mode,exit,label),color in zip(specs,colors):
                d=daily(choose(s,period,mode=mode,exit=exit));ax.plot(pd.to_datetime(d.date),d.equity,label=label,color=color,lw=1.2)
            ax.axhline(100000,color='#777777',ls='--',lw=.7);ax.grid(alpha=.2);ax.set_ylabel(s+' — capital net USD');ax.legend(fontsize=8)
        fig.suptitle(f'Retour VWAP après première heure — comptes conditionnels {period}\nFriction 0,01 USD/action/côté ; stop ADR20, plafond causal 1x')
        fig.savefig(figures/f'equity_{period}.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');x=np.arange(4)
    for ax,period in zip(axes,('ALL','B')):
        for j,s in enumerate(('SPY','QQQ')):
            bars=ax.bar(x+(j-.5)*.36,[choose(s,period,slip=z).total_return_pct for z in (.01,.02,.03,.05)],width=.36,color=colors[j],label=s);ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=8)
        ax.axhline(0,color='black',lw=.7);ax.set_xticks(x,['0,01','0,02','0,03','0,05']);ax.set_title(period);ax.set_xlabel('Friction USD/action/côté');ax.set_ylabel('Rendement net conditionnel (%)');ax.margins(y=.18);ax.grid(axis='y',alpha=.2);ax.legend()
    fig.suptitle('Retour VWAP — sensibilité aux coûts, commissions/emprunt inclus')
    fig.savefig(figures/'cost_sensitivity.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    for j,s in enumerate(('SPY','QQQ')):
        a=pd.read_csv(out/choose(s,'ALL').label/'by_year.csv');ax.bar(np.arange(len(a))+(j-.5)*.36,a.return_pct,width=.36,label=s,color=colors[j])
    ax.axhline(0,color='black',lw=.7);ax.set_xticks(np.arange(len(a)),a.year.astype(str));ax.set_ylabel('Rendement net conditionnel (%)');ax.set_title('Retour VWAP principal — années 2016–2026 (2026 partielle)');ax.grid(axis='y',alpha=.2);ax.legend()
    fig.savefig(figures/'annual_returns.png',dpi=150);plt.close(fig)
    markets,cash,profile=load_sources();selected={};manual=['# Transactions contrôlées dans les archives originales','Huit dates uniques/instrument : deux plus gros gains et pertes en USD, première ex-date, première demi-séance, première sortie VWAP et dernier trade ; compléter avec premières dates si doublons. Échantillon déterministe, non aléatoire. Prefixes complets jusqu’à la sortie relus dans les pages gzip hachées.']
    excluded=[];coverage=[]
    for s in ('SPY','QQQ'):
        t=trades(choose(s,'ALL'));divs=set(cash[s]);sample=pd.concat([t.nlargest(2,'net_pnl'),t.nsmallest(2,'net_pnl'),t[t.date.isin(divs)].head(1),t[t.half_session].head(1),t[t.exit_reason=='vwap_next_open'].head(1),t.tail(1),t.head(12)]).drop_duplicates('date').head(8).sort_values('date');selected[s]=sample
        manual += [f'## {s}',table(sample[['date','direction','quantity','adr20','vwap_at_signal','entry_reference','exit_reference','exit_reason','net_pnl']])]
        for r in sample.itertuples():manual.append(f'{r.date} {r.direction} {r.quantity} actions, {r.entry_time} → {r.exit_time} ({r.exit_resolution}) : mouvement {r.price_move_pnl:.6f} − friction {r.friction_cost:.6f} − commissions {r.commission:.6f} − emprunt {r.borrow_fee:.6f} = **{r.net_pnl:.6f} USD net**. Taille fondée sur close10:29={r.sizing_price:.6f}, ADR20={r.adr20:.6f}, stop={r.stop_price:.6f}.')
        d=daily(choose(s,'ALL'));e=d[d.conditionally_excluded][['date','eligibility']].copy();e.insert(0,'Instrument',s);excluded.append(e)
        for why,g in d.groupby('eligibility'):coverage.append(dict(Instrument=s,Motif=why,Séances=len(g),Trades=int(g.trades.sum())))
    raw=excerpts(out,selected,markets,profile);(out/'EXAMEN_TRANSACTIONS.md').write_text('\n\n'.join(manual)+'\n',encoding='utf-8')
    excluded=pd.concat(excluded,ignore_index=True);excluded.to_csv(out/'DATA_EXCLUSIONS.csv',index=False)
    h={'symbol':'Instrument','period':'Période','trades':'Trades','total_return_pct':'Net %','cagr_pct':'CAGR %','observed_close_drawdown_pct':'DD minute observé %','sharpe':'Sharpe','profit_factor':'Profit factor','slippage':'Friction USD/côté'}
    sections=['# Retour vers VWAP après première heure — rapport final',
        '**Décision : archiver cette version comme piste négative après coûts ; aucun nouveau bot justifié.** Les principaux SPY et QQQ perdent sur A, B et ALL. À coûts de base : SPY ALL −9,639 % et B −0,327 % ; QQQ ALL −15,792 % et B −0,868 %. Aucun seuil/horaire/stop n’a été optimisé après observation. Les variantes positives locales sont conservées sans remplacer le principal.',
        '**Portée conditionnelle et exploratoire.** Le filtre principal de séance actuelle complète est connu après coup ; les journées exclues ne représentent pas des rendements cash constatés. Les valeurs omettent ces journées (`observed_return=NaN`, zéro comptable de `return_net`). Les abstentions fondées sur warmup/historique déjà incomplet sont distinctes et causales. B réutilise l’historique déjà examiné : aucun nouveau hors-échantillon aveugle ni rendement prospectif.',
        '## Hypothèse et sources',
        'Tester si un écart important entre le close de la première heure et le VWAP de séance se corrige ensuite. C’est notre hypothèse figée, pas une stratégie rentable démontrée par les sources. [Alpaca définit le calcul VWAP et présente un autre signal de tendance](https://alpaca.markets/learn/algorithmic-trading-with-twap-and-vwap-using-alpaca) ; [construction officielle des barres](https://alpaca.markets/learn/stock-minute-bars) et [FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) précisent timestamps, champs et agrégation. Aucune performance publiée n’est attribuée à notre version contrariante.',
        'Nous utilisons le champ `vw` réel de chaque minute, pondéré par son volume : somme(vw×volume)/somme(volume) depuis09:30. Les CSV OHLCV n’avaient pas conservé ce champ, mais les 428 pages gzip originales le contenaient. Ce n’est pas une approximation HLC3. L’agrégation reste celle du fournisseur et de ses conditions de trades, sans reconstitution indépendante tick par tick.',
        '## Règles et coûts',
        'ADR20 = moyenne des amplitudes high-low RTH des20séances immédiatement antérieures complètes, sans saut de journée ni composante overnight. À close10:29 : LONG si close est sous VWAP de plus de0,25ADR ; SHORT si au-dessus de plus de0,25ADR ; égalité = plat. Entrée open10:30 ; q=floor(min(capital/close10:29,1 %capital/ADR20)), plafond causal1x. Stop de référence à une ADR de l’open d’entrée. Un trade maximum par séance, aucune réentrée.',
        'Sortie VWAP : attendre un close revenu au-delà du VWAP actualisé, puis exécuter au prochain open. Une touche intraminute ne suffit pas. Stop actif dès la minute d’entrée ; gap défavorable au stop rempli à l’open. Liquidation au dernier open15:59/12:59. Le délai de publication de10:29 peut empêcher le fill10:30 supposé. [Contrat complet avant P&L](../../PROTOCOL_EXECUTION.md).',
        'Mêmes frais : par côté max(0,35USD ; 0,0035×q), friction adverse0,01USD/action/côté, stress0,02/0,03/0,05 ; emprunt SHORT q×entrée après friction×1 %/360, un jour minimum. Pas d’intérêts sur cash ni tarif réglementaire séparé, disponibilité du prêt/quotes/latence/fills réels non observés. Ces coûts sont hypothétiques, pas une mesure d’exécution.',
        'ALL04/01/2016–16/10/2026 ; A jusqu’au30/04/2024 ; B01/05/2024–16/10/2026, chaque instrument/période réinitialisé séparément à100000USD. Les20jours de calcul avant B sont uniquement des informations passées connues, sans calibration. Les variantes et A/B/ALL se recouvrent ; les comptes ne constituent pas des observations indépendantes.',
        '## Principaux résultats',table(main[['symbol','period','trades','total_return_pct','cagr_pct','observed_close_drawdown_pct','sharpe','profit_factor']].rename(columns=h)),
        '![Capital B](figures/equity_B.png)','![Capital ALL](figures/equity_ALL.png)',
        '## Frais et variantes prédéfinies',table(c[(c['mode']=='both')&(c.quality=='complete_days')&(c.exit_policy=='vwap')][['symbol','period','slippage','total_return_pct']].rename(columns=h)),
        '![Frais](figures/cost_sensitivity.png)',table(c[(c.period=='B')&(c.slippage==.01)][['symbol','mode','quality','exit_policy','trades','total_return_pct']].rename(columns=h)),
        'SPY sans sortie VWAP, conservant stop et liquidation, donne +3,775 % ALL /+0,933 % A /+2,827 % B au coût de base. Cette variante préfigée a ses tailles/capital propres et ne constitue pas un témoin à exposition fixée. Son résultat modeste ne valide pas la sortie VWAP étudiée. QQQ SHORT seul est positif en B mais négatif sur ALL ; SPY LONG seul positif en B reste négatif sur ALL. Aucun choix du meilleur résultat après calcul. [Toutes les48comparaisons](comparison_all.csv).',
        '## Couverture des sources et abstentions',
        'Six caches et six CSV bruts vérifiés SHA, calendrier XNYS continu2714séances du31/12/2015 au16/10/2026, 2713séances dans ALL. Extraction des428pages gzip SHA contrôlées : 1054186barres RTH SPY et1054175QQQ rapprochées sur tous OHLCV. Aucun VWAP invalide avec volume positif, aucun horsOHLC et aucun volume nul dans ces barres. Le code accepte logiquement zéro volume sans poids et ne rejette pas automatiquement un VWAP horsOHLC, car les champs peuvent appliquer des conditions différentes. [Profil et empreintes](DATA_SOURCE_PROFILE.json).',
        table(pd.DataFrame(coverage)),table(excluded),
        'Warmup20 et invalid_prior20 sont des abstentions causales : aucune séance ancienne de remplacement ni entrée. La première heure invalide est un signal non observable. complete_days ajoute un filtre rétrospectif de qualité actuelle ; resolved_prefix conserve les exécutions démontrées avant un trou et classe les autres non résolues en omettant le trade entier, frais connus compris, avec intention exportée. Sur cette exécution aucune position entrée n’est devenue non résolue ; les principaux et cette sensibilité ont les mêmes P&L, sans que cela certifie un portefeuille continu ou la complétude du fournisseur.',
        table(main[['symbol','period','data_excluded_sessions','causal_history_abstention_sessions','no_signal_sessions','trades']].rename(columns=h)),
        '## Risque, exposition et décomposition',table(main[['symbol','period','price_move_pnl','friction_cost','commission','borrow_fee','regular_time_exposure_upper_pct','max_actual_entry_leverage','max_entry_risk_pct']].rename(columns=h)),
        'Les mouvements avant coûts sont déjà négatifs sur ALL pour les deux instruments ; SPY B légèrement positif avant coûts devient négatif après frais. La décomposition comptable n’identifie pas une cause économique ni une réfutation générale du retour à la moyenne. Budget1 % exclut frais et gaps ; 1x est un plafond au prix de taille, pas une garantie au fill. Durée de sortie intrabar bornée d’une minute ; DD aux closes et MAE/MFE sont partiellement observés. Aucun prix postexit de la minute de stop n’entre dans les marks.',
        '## Années, concentration et incertitude','![Années](figures/annual_returns.png)',table(main[['symbol','period','return_without_top3_days_pct','return_without_2020_daily_returns_pct','worst_trade_usd','half_session_trades']].rename(columns=h)),
        'Ablations descriptives : mettre à zéro les trois plus grands rendements quotidiens positifs, ou tous ceux de2020, puis recomposer les autres rendements conservés. Pas de nouveau portefeuille à tailles ou P&L fixes. Année2026 partielle. Les exports annuels, LONG/SHORT, demi-séances, raisons de sortie et abstentions restent disponibles.']
    intervals=[]
    for s in ('SPY','QQQ'):
        u=json.loads((out/f'{s}_B_uncertainty.json').read_text(encoding='utf-8'));lo,hi=u['annual_cluster']['mean_trade_bps_ci95'];sections.append(f'{s} B : IC95 % descriptif par groupes annuels sur la moyenne **par trade** [{lo:.3f}, {hi:.3f}] bps du notionnel. Seulement trois groupes annuels2024–2026 partiellement ou complètement observés.')
        for b in ('5','20'):
            lo,hi=u['blocks'][b]['conditional_daily_mean_ci95'];intervals.append(dict(Instrument=s,Bloc=int(b),Moyenne_quotidienne_basse_bps=lo*10000,Moyenne_quotidienne_haute_bps=hi*10000))
    sections += [table(pd.DataFrame(intervals)),
        'Le tableau mesure la moyenne **quotidienne du rendement du capital conditionnel**, unité différente des bps par transaction. Blocs circulaires5/20séances et années,3000réplications, seed20261020 ; années sans trade conservées. Les IC incluent les zéros comptables d’exclusions. Sans correction des essais multiples, avec B réutilisée et peu de groupes, ils restent descriptifs et couvrent zéro.',
        '## Audits et reproductibilité',
        f'Audit indépendant : {audit["executions"]}exécutions, **{audit["trade_rows"]}lignes recouvrantes et{audit["source_marks"]}marks**, ADR/VWAP/signaux/taille/trace/coûts/capital reconstruits en Decimal sans fonction moteur/statistiques. Erreur max champs monétaires par trade {audit["maximum_errors"]["currency_trade_usd"]:.3g}USD ; capital {audit["maximum_errors"]["capital_usd"]:.3g}USD ; tolérance monétaire3×10⁻⁶. [Preuve et unités](INDEPENDENT_AUDIT.json), [lignes](INDEPENDENT_TRADE_AUDIT.csv).',
        f'46tests contrôlés ; rapprochements secondaires des48scénarios et1776agrégats. {raw["selected_transactions"]}exemples avec{raw["raw_minute_bars"]}barres/{raw["numeric_fields_checked"]}champs OHLCV/VWAP relus dans les pages gzip et comparés, écart maximal {raw["max_absolute_error"]:.3g}. VWAP de première heure et sorties VWAP vérifiés depuis ces extraits. [Exemples](EXAMEN_TRANSACTIONS.md), [preuve](RAW_EXCERPT_AUDIT.json). Cela vérifie le traitement d’un seul fournisseur, sans validation croisée de ses prix ni preuve des fills.',
        'Protocole/code/sources/versions figés avant première boucle : [gel](PRE_EXECUTION_PROTOCOL.json), [snapshot](code_snapshot), [manifest initial](MANIFEST.json). Les scripts de rapport/audit ajoutés ensuite sont tracés dans le manifest final. L’ablation a été corrigée avant P&L pour respecter le classement par rendements ; eod_only ne demande pas un VWAP futur inutilisé. Aucun correctif financier après calcul. Les tests synthétiques ne sont pas des données de performance. [Guide](../../README.md).',
        '## Décision pratique et ORB',
        'Ne pas poursuivre cette version VWAP vers un bot. Elle apporte un résultat négatif utile et n’épuise pas toutes les stratégies de retour à la moyenne. ORB QQQ conserve un meilleur statut exploratoire, mais les coûts, les journées dominantes B, le filtre de couverture et les IC ne permettent pas de la qualifier validée. [Décision ORB et protocole proposé de suivi prospectif](../../../../docs/research/2026-10-20-orb-qqq-decision.md). Aucun nouveau bot ni automation ORB activé ; Noise Area QQQ garde son suivi distinct.']
    rendered='\n\n'.join(sections)
    rendered=re.sub(r'(?<=\d)(?=(?:USD|pages|barres|lignes|marks|tests|scénarios|agrégats|exécutions|exemples|champs|séances|jours|réplications|ADR))',' ',rendered)
    (out/'RAPPORT_FINAL.md').write_text(rendered+'\n',encoding='utf-8');print('REPORT READY',raw,flush=True)


if __name__=='__main__':main(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/2026-10-20')
