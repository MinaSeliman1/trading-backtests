"""Fixtures artificielles, réservées à la vérification du moteur."""
from dataclasses import replace
import pandas as pd
import pytest

from fvg_backtest.engine import Config, INSTRUMENTS, detect_setups, run, exit_fill, position_size


def session(day="2025-03-10", end="16:00"):
    idx = pd.date_range(f"{day} 09:30", f"{day} {end}", freq="min", inclusive="left", tz="America/New_York")
    df = pd.DataFrame({"open":102.1,"high":102.3,"low":101.9,"close":102.1,"volume":1000}, index=idx)
    df.iloc[:5, :4] = [100,101,99,100]
    values = [[100,100.5,99.8,100.2],[100.2,102,100,101.8],[101.8,102.2,101.5,102],
              [102,102,100.8,101],[101,102.3,100.9,102.1]]
    df.iloc[5:10, :4] = values
    return df


def test_signal_is_known_at_close_and_entry_at_next_open():
    s = detect_setups(session(), Config())[0]
    assert s.formation_time.strftime("%H:%M") == "09:38"
    assert s.retest_time.strftime("%H:%M") == "09:39"
    assert s.signal_time.strftime("%H:%M") == "09:40"
    assert s.entry_time == s.signal_time
    assert s.stop_a == pytest.approx(100.79)
    assert s.stop_b == pytest.approx(100.49)


def test_no_confirmation_from_future_or_formation_bar():
    df=session()
    assert detect_setups(df.iloc[:9], Config()) == []
    assert detect_setups(df.iloc[:8], Config()) == []


def test_body_must_cross_opening_range():
    df=session(); df.iloc[6,0]=101.1
    assert detect_setups(df, Config()) == []


def test_three_fvg_candles_must_all_be_after_0935():
    df=session(); df.iloc[5:8,:4]=[102,102.3,101.9,102.1]
    assert detect_setups(df, Config()) == []


def test_confirmation_can_be_retest_bar():
    df=session(); df.iloc[7,:4]=[102,102.2,101.5,101.6]
    df.iloc[8,:4]=[101.5,102.4,100.8,102.2]
    assert detect_setups(df, Config())[0].signal_time.strftime("%H:%M")=="09:39"


def test_window_and_deadline():
    df=session()
    assert detect_setups(df, replace(Config(),confirmation_bars=0)) == []
    assert detect_setups(df, replace(Config(),retest_minutes=0)) == []
    shifted=df.copy(); shifted.iloc[5:,:4]=[102.1,102.3,101.9,102.1]
    shifted.iloc[85:90,:4]=df.iloc[5:10,:4].values
    assert detect_setups(shifted, Config()) == []  # confirmation à 11:00 exclue


def test_one_trade_and_costs_and_integer_sizing():
    df=session(); trades, equity, rejects=run([df], INSTRUMENTS["SPY"], Config())
    assert len(trades)==1
    t=trades.iloc[0]
    assert t.quantity == int(t.quantity)
    assert t.entry_price > df.loc[t.entry_time,"open"]
    assert t.exit_price < df.iloc[-1].open
    assert t.fees > 0 and t.slippage_usd > 0
    assert t.estimated_loss_at_order_usd <= 500+1e-7
    assert t.exposure_usd <= 100000
    assert t.exit_reason == "session_end"
    assert t.exit_time == df.index[-1]
    assert equity.iloc[-1].equity == pytest.approx(100000+t.net_pnl)


def test_both_touched_is_stop_and_gap_stop_uses_open():
    ins=INSTRUMENTS["SPY"]; c=Config(spread_ticks=0)
    both=pd.Series({"open":100,"high":104,"low":98,"close":101})
    assert exit_fill(both,1,99,103,ins,c)==(pytest.approx(98.99),"stop",99)
    gap=both.copy(); gap["open"]=97
    assert exit_fill(gap,1,99,103,ins,c)[0] == pytest.approx(96.99)
    short=pd.Series({"open":100,"high":102,"low":96,"close":99})
    assert exit_fill(short,-1,101,97,ins,c)[1]=="stop"


def test_gap_tp_known_at_open_precedes_later_stop():
    b=pd.Series({"open":104,"high":105,"low":98,"close":100})
    assert exit_fill(b,1,99,103,INSTRUMENTS["SPY"],Config())[1]=="target"


def test_invalid_stop_and_insufficient_margin_rejected():
    df=session(); df.iloc[10,0]=100.4
    trades,_,rej=run([df],INSTRUMENTS["SPY"],replace(Config(),stop_variant="B"))
    assert trades.empty
    assert "invalid_stop" in set(rej.reason)
    assert position_size(1000,5000,4999,INSTRUMENTS["ES"],Config()) == 0


def test_futures_point_value_and_short_symmetry():
    df=session()
    mirror=df.copy()
    mirror["open"]=202-df.open; mirror["close"]=202-df.close
    mirror["high"]=202-df.low; mirror["low"]=202-df.high
    s=detect_setups(mirror,Config())[0]
    assert s.direction == -1
    assert s.stop_a==pytest.approx(101.21)
    assert INSTRUMENTS["ES"].tick*INSTRUMENTS["ES"].point_value==12.5
    assert INSTRUMENTS["NQ"].tick*INSTRUMENTS["NQ"].point_value==5


def test_future_prices_do_not_change_earlier_signal_or_quantity():
    df=session(); altered=df.copy(); altered.iloc[11:,:4]=[104,105,103,104]
    a=detect_setups(df,Config())[0]; b=detect_setups(altered,Config())[0]
    assert a==b
    ta,_,_=run([df],INSTRUMENTS["SPY"],Config())
    tb,_,_=run([altered],INSTRUMENTS["SPY"],Config())
    assert ta.iloc[0].quantity==tb.iloc[0].quantity


def test_exit_on_entry_bar_is_possible_and_pessimistic():
    df=session(); df.iloc[10,:4]=[102.1,110,99,102]
    t,_,_=run([df],INSTRUMENTS["SPY"],Config())
    assert t.iloc[0].exit_reason=="stop"
    assert t.iloc[0].entry_time==t.iloc[0].exit_time


def test_early_close_liquidation():
    df=session("2025-11-28","13:00")
    t,_,_=run([df],INSTRUMENTS["SPY"],Config())
    assert t.iloc[0].exit_time.strftime("%H:%M")=="12:59"


def test_bad_minutes_rejected_even_when_engine_called_directly():
    with pytest.raises(ValueError,match="consecutive"):
        detect_setups(session().drop(session().index[6]),Config())


def test_sizing_reserves_tick_rounded_stop_slippage():
    ins=replace(INSTRUMENTS["SPY"],commission=0,min_commission=0)
    c=replace(Config(),extra_fee_per_unit=0,spread_ticks=1)
    q=position_size(100000,100,99,ins,c)
    assert q*1.02<=500  # 1.5 tick is rounded to 2 ticks at executable stop


def test_outside_session_cannot_enter_and_repeated_day_cannot_trade_twice():
    df=session(); df.index=df.index+pd.Timedelta(hours=1)
    with pytest.raises(ValueError): detect_setups(df,Config())
    with pytest.raises(ValueError,match="unique"):
        run([session(),session()],INSTRUMENTS["SPY"],Config())


def test_margin_reserves_entry_fee():
    c=replace(Config(),risk_fraction=.5)
    q=position_size(100000,4000,3999,INSTRUMENTS["ES"],c)
    assert q*25000+q*2.5<=100000


def test_order_quantity_is_fixed_before_next_open_is_observed():
    df=session(); altered=df.copy()
    altered.iloc[10,:4]=[104,104.5,103.9,104]
    c=replace(Config(),max_volume_fraction=1)
    a,_,_=run([df],INSTRUMENTS["SPY"],c)
    b,_,_=run([altered],INSTRUMENTS["SPY"],c)
    assert a.iloc[0].quantity==b.iloc[0].quantity
    assert a.iloc[0].entry_price!=b.iloc[0].entry_price
    assert a.iloc[0].estimated_loss_at_order_usd<=500
