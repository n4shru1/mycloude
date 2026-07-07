"""IDX Morning Plan Generator — murni perhitungan teknikal, tidak butuh AI."""
import yfinance as yf, pandas as pd, json, os
from datetime import datetime
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "data" / "trading"
DIR.mkdir(parents=True, exist_ok=True)
WATCHLIST = [
    ('TPIA','Chandra Asri Pacific','Petrokimia',True),
    ('DEWA','Darma Henwa Tbk','Mining Contractor',True),
    ('ADMR','Alamtri Minerals','Batubara',True),
    ('ANTM','Aneka Tambang','Mining',True),
    ('TLKM','Telkom Indonesia','Telekomunikasi',True),
    ('BUMI','Bumi Resources Tbk','Batubara',True),
    ('BIPI','Hindia Energi Tbk','Energi',True),
    ('CUAN','Petrindo Jaya Kreasi','Pertambangan',True),
    ('ASPR','Asia Pramulia Tbk','Logistik',True),
]

def score(df):
    if df is None or len(df)<20: return 0,'normal'
    c=df['Close']; v=df['Volume']
    d=c.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=g.ewm(com=13,min_periods=14).mean(); al=l.ewm(com=13,min_periods=14).mean().replace(0,1)
    rsi=float((100-(100/(1+ag/al))).iloc[-1])
    ma50=c.rolling(50).mean().iloc[-1] if len(c)>=50 else c.mean()
    regime='recovery' if (ma50-c.iloc[-1])/ma50>0.10 else 'normal'
    s=0
    if regime=='recovery': s+=2 if 30<=rsi<=65 else (1 if 20<=rsi<30 or 65<rsi<=75 else 0)
    else: s+=2 if 45<=rsi<=65 else (1 if 65<rsi<=72 else 0)
    vr=v.iloc[-1]/v.iloc[-6:-1].mean() if len(v)>=6 else 0
    s+=2 if vr>=2 else (1 if vr>=1.5 else 0)
    if regime=='recovery':
        e5=c.ewm(span=5,adjust=False).mean().iloc[-1]; e10=c.ewm(span=10,adjust=False).mean().iloc[-1]
        s+=1 if e5>e10 else 0
    else:
        ma20=c.rolling(20).mean().iloc[-1]; s+=1 if c.iloc[-1]>ma20 else 0
        if len(c)>=50: s+=1 if c.iloc[-1]>ma50 else 0
    r3=(c.iloc[-1]/c.iloc[-4]-1)*100 if len(c)>=4 else 0
    if regime=='recovery': s+=2 if 1<=r3<=35 else (1 if 0<=r3<1 else 0)
    else: s+=2 if 2<=r3<=12 else (1 if 0<=r3<2 or 12<r3<=18 else 0)
    if len(df)>=2:
        p=df.iloc[-2]; rng=p['High']-p['Low']; body=abs(p['Close']-p['Open'])
        s+=1 if rng>0 and body/rng>0.5 and p['Close']>p['Open'] else 0
    return s, regime

def tier(s): return 'T1' if s>=7 else 'T2' if s>=5 else 'T3' if s>=3 else None

def rpx(p,b):
    t=50 if b>=500 else 25 if b>=200 else 10 if b>=100 else 5
    return int(round(p/t)*t)

def main():
    now=datetime.now()
    HARI=['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu']
    BULAN=['','Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember']
    td=now.strftime('%Y-%m-%d')
    label=f"{HARI[now.weekday()]} {now.day} {BULAN[now.month]} {now.year}"
    tickers=[w[0]+'.JK' for w in WATCHLIST]
    raw=yf.download(tickers,period='60d',auto_adjust=True,progress=False)
    results=[]
    for w in WATCHLIST:
        try:
            k=w[0]+'.JK'
            df=pd.DataFrame({'Open':raw['Open'][k],'High':raw['High'][k],'Low':raw['Low'][k],'Close':raw['Close'][k],'Volume':raw['Volume'][k]}).dropna()
            sc,regime=score(df); t=tier(sc)
            if t is None: continue
            h=int(df['Close'].iloc[-1])
            P={'T1':(.97,1.0,1.08,1.16,.935),'T2':(.97,1.0,1.08,1.17,.930),'T3':(.96,.99,1.07,1.14,.920)}[t]
            results.append({'kode':w[0],'nama':w[1],'tier':t,'score':sc,'harga':h,
                'entry_lo':rpx(h*P[0],h),'entry_hi':rpx(h*P[1],h),
                'tp1':rpx(h*P[2],h),'tp2':rpx(h*P[3],h),'cl':rpx(h*P[4],h)})
            print(f"{w[0]}: {t} score={sc}")
        except Exception as e: print(f"skip {w[0]}: {e}")
    results.sort(key=lambda x:-x['score']); results=results[:3]
    jpath=DIR / f'plan_{td}.json'
    with open(jpath,'w') as f: json.dump({'date':td,'label':label,'stocks':results},f,ensure_ascii=False,indent=2)
    rows=''.join(f"<tr><td><b>{r['kode']}</b></td><td>{r['tier']}</td><td>{r['score']}/10</td><td>{r['entry_lo']:,}–{r['entry_hi']:,}</td><td style='color:#34D399'>{r['tp1']:,}/{r['tp2']:,}</td><td style='color:#F87171'>{r['cl']:,}</td></tr>" for r in results)
    html=f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>IDX Plan {td}</title><style>body{{font-family:sans-serif;background:#0A0E1A;color:#E2E8F0;padding:20px}}h2{{color:#F59E0B;margin-bottom:16px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #334155;padding:10px;text-align:left}}th{{background:#0D1117;color:#06B6D4}}</style></head><body><h2>IDX Trading Plan — {label}</h2><table><tr><th>Kode</th><th>Tier</th><th>Score</th><th>Entry</th><th>TP1/TP2</th><th>CL</th></tr>{rows}</table></body></html>"
    hpath=DIR / f'plan_{td}.html'
    with open(hpath,'w') as f: f.write(html)
    print(f"Selesai: {len(results)} saham | JSON: {jpath} | HTML: {hpath}")

if __name__ == "__main__":
    main()
