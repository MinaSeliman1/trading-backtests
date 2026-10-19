"""Preuve synthétique pour le panneau Sources de la réponse, sans chemins privés."""
from pathlib import Path
import json
import pandas as pd


def main():
    out=Path('results/alpaca_sip_long')
    audit=json.loads((out/'audit_validation.json').read_text())
    validation=json.loads((out/'OUTPUT_VALIDATION.json').read_text())
    assert audit['status']==validation['status']=='passed'
    coverage=[]
    for source in audit['source_receipts']:
        coverage.append(dict(instrument=source['instrument'],bougies=source['bars_verified_against_raw_response'],
                             seances=source['retained_sessions']))
    df=pd.read_csv(out/'comparison_all.csv')
    main_rows=df[(df.segment=='OOS')&(df.test=='principal')&(df.slippage_ticks==1)]
    rows=[]
    for _,r in main_rows.iterrows():
        summary=json.loads((out/r.instrument/r.label/'summary.json').read_text())
        rows.append(dict(instrument=r.instrument,stop=r.stop_variant,debut=r.first_session,fin=r.last_session,
                         trades=int(r.trades),PnL_net_USD=float(r.net_pnl),PF=float(r.profit_factor),
                         esperance_R=float(r.expectancy_r),IC95_R_bloc5=str(summary['bootstrap_block5'].get('expectancy_r_ci95'))))
    payload=dict(schemaVersion=1,items=[
        dict(id='historique-minute',title='Historique minute réellement acquis',queries=[dict(
            id='alpaca-sip-coverage',source=dict(label='Alpaca SIP',
                files=[dict(label='SPY_manifest.json'),dict(label='QQQ_manifest.json'),dict(label='audit_validation.json')],
                links=[dict(label='FAQ Alpaca',href='https://docs.alpaca.markets/us/docs/market-data-faq')],
                metricDefinitions=[dict(label='Couverture',definition='Les bougies acquises sont des OHLCV SIP de 1 minute non ajustés ; les séances retenues contiennent toutes les minutes régulières attendues.')],
                filters=['feed=sip ; timeframe=1Min ; adjustment=raw','Séances 09:30 à clôture XNYS, America/New_York','Séance entière exclue si une minute manque ; aucun remplissage'],
                caveats=['Une clé API personnelle est nécessaire ; la FAQ permet le SIP historique sans abonnement si la fin de requête a plus de quinze minutes.'],
                evidenceFlow=[dict(kind='validation',title='Rapprochement des acquisitions',detail='Toutes les bougies des CSV ont été rapprochées des pages JSON brutes ; les SHA-256 des CSV et des pages concordent.')]),
            reportingPeriod='3 janvier 2023 au 18 septembre 2026',columns=['instrument','bougies','seances'],rows=coverage)]),
        dict(id='validation-oos',title='Validation hors échantillon SPY / QQQ',queries=[dict(
            id='principal-oos-results',source=dict(label='Backtest Python sur Alpaca',
                files=[dict(label='comparison_all.csv'),dict(label='audit_validation.json'),dict(label='OUTPUT_VALIDATION.json')],
                metricDefinitions=[dict(label='P&L',definition='Le P&L net soustrait les commissions et l’emprunt hypothétique aux gains et pertes des prix simulés avec slippage.'),
                                   dict(label='Espérance',definition='L’espérance en R est la moyenne du résultat net de chaque trade rapporté à son risque initial au fill, hors frais.')],
                filters=['30 % chronologiques finaux, dates de chaque instrument affichées','Stops A et B séparés ; 100 000 USD par scénario','Slippage nominal 1 tick par exécution et spread total 1 tick','Retest 15 minutes ; confirmation 0 à 2 minutes après retest ; TP 3R ; entrée avant 11:00 NY'],
                caveats=['Validation historique rétrospective ; une correction numérique symétrique a été appliquée après examen partiel, sans choix de paramètres économiques.','Les variantes partagent des trades et ne constituent pas des observations indépendantes. Les fills et la disponibilité d’emprunt réels restent inconnus.'],
                evidenceFlow=[dict(kind='validation',title='Contrôles exécutés',detail=f"{audit['trades_checked']} lignes de trades principaux IS/OOS rapprochées des bougies et recalculées indépendamment ; {validation['scenarios_checked']} exports rapprochés pour leurs totaux et invariants. Le découpage initial est inchangé.")]),
            reportingPeriod='SPY : 11 août 2025–18 septembre 2026 ; QQQ : 8 août 2025–18 septembre 2026',
            columns=['instrument','stop','debut','fin','trades','PnL_net_USD','PF','esperance_R','IC95_R_bloc5'],rows=rows,
            methods=[dict(language='calculation',code='P&L net = (prix de sortie − prix d’entrée) × sens × quantité − frais.\nR net = P&L net / (|prix d’entrée − stop| × quantité).\nIC95 : percentiles 2,5 % et 97,5 % de 5 000 bootstraps de blocs de cinq séances.')])])])
    (out/'SOURCE_RECEIPT.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Panneau Sources : deux constats, prix et résultats réels, sans chemins privés ni identifiants.')


if __name__=='__main__': main()
