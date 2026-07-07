"""IDX Evening Report Generator — murni perhitungan, tidak butuh AI."""
import yfinance as yf, json, glob
from datetime import date, timedelta
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "data" / "trading"

def cari_plan():
    for d in [0,1,2]:
        p = DIR / f"plan_{(date.today()-timedelta(days=d)).strftime('%Y-%m-%d')}.json"
        if p.exists(): return p
    files = sorted(glob.glob(str(DIR / 'plan_*.json')))
    return Path(files[-1]) if files else None

def main():
    plan_path=cari_plan()
    if not plan_path: print('Tidak ada plan'); return
    with open(plan_path) as f: plan=json.load(f)
    label=plan.get('label',''); stocks=plan.get('stocks',[])
    today=date.today().strftime('%d/%m/%Y')
    rows=''; wins=0; losses=0; trails=0; holds=0
    for s in stocks:
        kode=s['kode']; entry=s.get('entry_lo',0); tp1=s.get('tp1',0); cl=s.get('cl',0)
        try:
            tk=yf.Ticker(f'{kode}.JK'); info=tk.fast_info
            close=float(info.last_price); high=float(info.day_high)
            cp=(close-entry)/entry*100 if entry else 0
            hp=(high-entry)/entry*100 if entry else 0
            if close<=cl: status='❌ LOSS'; color='#F87171'; losses+=1
            elif close>=tp1: status='✅ WIN'; color='#34D399'; wins+=1
            elif hp>=3.0: status='🔒 TRAIL'; color='#FBBF24'; trails+=1
            else: status='🟡 HOLD'; color='#94A3B8'; holds+=1
            rows+=f"<tr><td><b>{kode}</b></td><td>{s.get('tier','')}</td><td>{entry:,}–{s.get('entry_hi',0):,}</td><td>{tp1:,}</td><td>{cl:,}</td><td style='color:#60A5FA'>{close:,.0f} ({cp:+.1f}%)</td><td style='color:{color}'>{status}</td></tr>"
        except Exception as e:
            rows+=f"<tr><td>{kode}</td><td colspan=6>Error: {e}</td></tr>"
    total=len(stocks); eff=wins+trails
    wr=eff/total*100 if total else 0
    summary=f"WIN:{wins} TRAIL:{trails} LOSS:{losses} HOLD:{holds} | WinRate:{wr:.0f}%"
    html=f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>IDX Report {today}</title>
<style>body{{font-family:sans-serif;background:#0A0E1A;color:#E2E8F0;padding:20px}}
h2{{color:#F59E0B;margin-bottom:8px}}.sum{{background:#111827;border:1px solid #334155;padding:12px;border-radius:8px;margin-bottom:16px;color:#94A3B8}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #334155;padding:10px;text-align:left}}
th{{background:#0D1117;color:#06B6D4}}</style></head><body>
<h2>IDX Evening Report — {today}</h2>
<div class='sum'>Plan: {label} &nbsp;|&nbsp; {summary}</div>
<table><tr><th>Kode</th><th>Tier</th><th>Entry</th><th>TP1</th><th>CL</th><th>Close</th><th>Status</th></tr>
{rows}</table></body></html>"""
    td=date.today().strftime('%Y-%m-%d')
    hpath=DIR / f'Evening_Report_{td}.html'
    with open(hpath,'w') as f: f.write(html)
    print(f"Selesai | {summary} | HTML: {hpath}")

if __name__ == "__main__":
    main()
