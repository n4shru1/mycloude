import yfinance as yf, json, glob, csv
from datetime import date, timedelta
from pathlib import Path

TRADING_DIR = Path(__file__).resolve().parents[2] / "data" / "trading"
LOG_FILE    = TRADING_DIR / 'trade_log.csv'
FIELDNAMES  = ['tanggal','kode','nama','tier','score','entry','tp1','tp2','cl',
               'close','high','status','pnl_pct','max_pnl_pct','hari_ke']

def cari_plan():
    for d in [0,1,2]:
        p = TRADING_DIR / f"plan_{(date.today()-timedelta(days=d)).strftime('%Y-%m-%d')}.json"
        if p.exists(): return p
    files = sorted(glob.glob(str(TRADING_DIR / 'plan_*.json')))
    return Path(files[-1]) if files else None

def fetch_harga(kode):
    try:
        tk=yf.Ticker(f'{kode}.JK'); info=tk.fast_info
        return float(info.last_price), float(info.day_high)
    except: return None, None

def run():
    plan_path=cari_plan()
    if not plan_path: print('Tidak ada plan.'); return
    with open(plan_path) as f: plan=json.load(f)
    stocks=plan.get('stocks',[]); plan_date=plan.get('date',str(date.today()))
    today=str(date.today())
    existing=set()
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            for row in csv.DictReader(f): existing.add((row['tanggal'],row['kode']))
    rows_baru=[]
    for s in stocks:
        kode=s['kode']
        if (today,kode) in existing: continue
        entry=s.get('entry_lo',0); tp1=s.get('tp1',0); tp2=s.get('tp2',0); cl=s.get('cl',0)
        close,high=fetch_harga(kode)
        if close is None: continue
        cp=round((close-entry)/entry*100,2) if entry else 0
        hp=round((high-entry)/entry*100,2) if entry else 0
        if close<=cl: status='LOSS'
        elif close>=tp1: status='WIN'
        elif hp>=3.0: status='TRAIL'
        else: status='HOLD'
        hari=(date.today()-date.fromisoformat(plan_date)).days+1
        rows_baru.append({'tanggal':today,'kode':kode,'nama':s.get('nama',''),
            'tier':s.get('tier',''),'score':s.get('score',0),
            'entry':entry,'tp1':tp1,'tp2':tp2,'cl':cl,
            'close':round(close),'high':round(high),
            'status':status,'pnl_pct':cp,'max_pnl_pct':hp,'hari_ke':hari})
    if not rows_baru: print('Tidak ada data baru.'); return
    write_header = not LOG_FILE.exists()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE,'a',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDNAMES)
        if write_header: w.writeheader()
        w.writerows(rows_baru)
    print(f'✓ {len(rows_baru)} baris dicatat ke trade_log.csv')
    for r in rows_baru: print(f"  {r['kode']} | {r['status']} | PnL {r['pnl_pct']:+.1f}% | Max {r['max_pnl_pct']:+.1f}%")

if __name__=='__main__': run()
