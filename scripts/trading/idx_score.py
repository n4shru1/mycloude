"""Adaptive Technical Scoring Engine untuk IDX."""
import numpy as np

def calc_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag = gain.ewm(com=period-1, min_periods=period).mean()
    al = loss.ewm(com=period-1, min_periods=period).mean()
    rs = ag / al.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def detect_regime(close):
    if len(close) < 50: return 'normal'
    ma50 = close.rolling(50).mean().iloc[-1]
    last = close.iloc[-1]
    return 'recovery' if (ma50 - last) / ma50 > 0.10 else 'normal'

def score_stock(df):
    if df is None or len(df) < 20:
        return 0, {}
    close  = df['Close']
    high   = df['High']
    low    = df['Low']
    volume = df['Volume']
    last   = close.iloc[-1]
    rsi_s  = calc_rsi(close, 14)
    rsi    = rsi_s.iloc[-1]
    regime = detect_regime(close)
    score = 0
    d = {'_regime': regime}
    if regime == 'recovery':
        if 30 <= rsi <= 65:   pts,lbl = 2, f'RSI {rsi:.0f} ok'
        elif 20<=rsi<30 or 65<rsi<=75: pts,lbl = 1, f'RSI {rsi:.0f} borderline'
        else:                  pts,lbl = 0, f'RSI {rsi:.0f} extreme'
    else:
        if 45 <= rsi <= 65:   pts,lbl = 2, f'RSI {rsi:.0f} sweet spot'
        elif 65 < rsi <= 72:  pts,lbl = 1, f'RSI {rsi:.0f} near OB'
        else:                  pts,lbl = 0, f'RSI {rsi:.0f} weak/OB'
    score += pts; d['RSI'] = {'pts':pts,'max':2,'val':f'{rsi:.1f}','label':lbl}
    if len(volume) >= 6:
        avg5 = volume.iloc[-6:-1].mean()
        vr   = volume.iloc[-1] / avg5 if avg5 > 0 else 0
    else: vr = 0
    if vr >= 2.0:   pts,lbl = 2, f'{vr:.1f}x surge'
    elif vr >= 1.5: pts,lbl = 1, f'{vr:.1f}x elevated'
    else:           pts,lbl = 0, f'{vr:.1f}x normal'
    score += pts; d['Volume'] = {'pts':pts,'max':2,'val':f'{vr:.1f}x','label':lbl}
    if regime == 'recovery':
        ema5  = close.ewm(span=5,  adjust=False).mean().iloc[-1]
        ema10 = close.ewm(span=10, adjust=False).mean().iloc[-1]
        pts3 = 1 if ema5 > ema10 else 0
        lbl3 = f'EMA5 {int(ema5):,} vs EMA10 {int(ema10):,}'
        d['EMA5>10'] = {'pts':pts3,'max':1,'val':f'{int(ema5):,}','label':lbl3}
        score += pts3
        prev_rsi = rsi_s.iloc[-6] if len(rsi_s) >= 6 else rsi
        pts4 = 1 if rsi > prev_rsi else 0
        lbl4 = f'RSI {prev_rsi:.0f} to {rsi:.0f}'
        d['RSI_trend'] = {'pts':pts4,'max':1,'val':f'{prev_rsi:.0f}>{rsi:.0f}','label':lbl4}
        score += pts4
    else:
        ma20 = close.rolling(20).mean().iloc[-1]
        pts3 = 1 if last > ma20 else 0
        d['MA20'] = {'pts':pts3,'max':1,'val':f'{int(ma20):,}','label':f'vs MA20 {int(ma20):,}'}
        score += pts3
        if len(close) >= 50:
            ma50 = close.rolling(50).mean().iloc[-1]
            pts4 = 1 if last > ma50 else 0
            d['MA50'] = {'pts':pts4,'max':1,'val':f'{int(ma50):,}','label':f'vs MA50 {int(ma50):,}'}
            score += pts4
    ret3d = (close.iloc[-1]/close.iloc[-4]-1)*100 if len(close)>=4 else 0
    if regime == 'recovery':
        if 1<=ret3d<=35:   pts,lbl = 2, f'{ret3d:+.1f}% recovery ok'
        elif 35<ret3d<=50 or 0<=ret3d<1: pts,lbl = 1, f'{ret3d:+.1f}% borderline'
        else:               pts,lbl = 0, f'{ret3d:+.1f}% neg/over'
    else:
        if 2<=ret3d<=12:   pts,lbl = 2, f'{ret3d:+.1f}% ideal'
        elif 0<=ret3d<2 or 12<ret3d<=18: pts,lbl = 1, f'{ret3d:+.1f}% early/ext'
        else:               pts,lbl = 0, f'{ret3d:+.1f}% weak/OB'
    score += pts; d['Mom3D'] = {'pts':pts,'max':2,'val':f'{ret3d:+.1f}%','label':lbl}
    if len(df) >= 2:
        p = df.iloc[-2]
        rng  = p['High']-p['Low']
        body = abs(p['Close']-p['Open'])
        br   = body/rng if rng>0 else 0
        pts  = 1 if (br>0.5 and p['Close']>p['Open']) else 0
        d['Candle'] = {'pts':pts,'max':1,'val':f'{br:.0%}','label':f'body {br:.0%}'}
        score += pts
    if regime == 'recovery' and len(low) >= 10:
        low10  = low.iloc[-10:].min()
        bounce = (last-low10)/low10*100
        pts = 1 if bounce >= 15 else 0
        d['Bounce'] = {'pts':pts,'max':1,'val':f'+{bounce:.0f}%','label':f'+{bounce:.0f}% from 10D-low'}
        score += pts
    elif regime == 'normal' and len(close) >= 10:
        h10  = high.iloc[-10:].max()
        dist = (h10-last)/h10
        pts  = 1 if dist <= 0.05 else 0
        d['Breakout'] = {'pts':pts,'max':1,'val':f'{int(h10):,}','label':f'{dist:.1%} from 10D-high'}
        score += pts
    return score, d

def tier_from_score(score):
    if score >= 7: return 'T1'
    elif score >= 5: return 'T2'
    elif score >= 3: return 'T3'
    return None
