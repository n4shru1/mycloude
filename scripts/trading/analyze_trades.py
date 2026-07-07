import csv, os, requests
from datetime import date, timedelta
from collections import defaultdict
from pathlib import Path

TRADING_DIR  = Path(__file__).resolve().parents[2] / "data" / "trading"
LOG_FILE     = TRADING_DIR / 'trade_log.csv'
FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
WA_TARGET    = '120363427350363923@g.us'

def kirim_wa(pesan):
    resp = requests.post('https://api.fonnte.com/send',
        headers={'Authorization': FONNTE_TOKEN},
        data={'target': WA_TARGET, 'message': pesan})
    return resp.json()

def baca_log(hari=7):
    if not LOG_FILE.exists(): return []
    cutoff=(date.today()-timedelta(days=hari)).isoformat()
    rows=[]
    with open(LOG_FILE) as f:
        for r in csv.DictReader(f):
            if r['tanggal']>=cutoff: rows.append(r)
    return rows

def baca_semua():
    if not LOG_FILE.exists(): return []
    with open(LOG_FILE) as f: return list(csv.DictReader(f))

def analisa(rows, label):
    if not rows: return f"Belum ada data untuk {label}."
    total=len(rows)
    wins=[r for r in rows if r['status']=='WIN']
    trails=[r for r in rows if r['status']=='TRAIL']
    losses=[r for r in rows if r['status']=='LOSS']
    holds=[r for r in rows if r['status']=='HOLD']
    resolved=wins+trails+losses
    eff=len(wins)+len(trails)
    wr=eff/len(resolved)*100 if resolved else 0
    def avg(lst,f='pnl_pct'):
        v=[float(r[f]) for r in lst if r.get(f)]
        return sum(v)/len(v) if v else 0
    avg_all=avg(rows); avg_max=avg(rows,'max_pnl_pct')
    avg_win=avg(wins+trails); avg_loss=avg(losses)
    tier_stats=defaultdict(lambda:{'total':0,'win':0})
    for r in resolved:
        t=r['tier']; tier_stats[t]['total']+=1
        if r['status'] in ('WIN','TRAIL'): tier_stats[t]['win']+=1
    if len(resolved)<10: verdict="⏳ Data belum cukup (min. 10 resolved)"
    elif wr>=60 and avg_all>0: verdict="✅ STRATEGI WORKS"
    elif wr>=50 and avg_all>0: verdict="🟡 CUKUP BAIK — optimasi T3"
    else: verdict="⚠️ EVALUASI — review kriteria entry"
    lines=[f"📊 *ANALISA IDX — {label}*\n",
        f"Total: {total} trade ({len(resolved)} resolved, {len(holds)} hold)\n",
        "─────────────────────",
        f"✅ WIN  : {len(wins)}",
        f"🔒 TRAIL: {len(trails)}",
        f"❌ LOSS : {len(losses)}",
        f"🟡 HOLD : {len(holds)}",
        f"\n*Win Rate: {wr:.1f}%* ({eff}/{len(resolved)})",
        f"Avg P&L   : {avg_all:+.1f}%",
        f"Avg MaxPnL: {avg_max:+.1f}%"]
    if wins+trails: lines.append(f"Avg Win   : {avg_win:+.1f}%")
    if losses:
        lines.append(f"Avg Loss  : {avg_loss:+.1f}%")
        ev=(wr/100*avg_win)+((1-wr/100)*avg_loss)
        lines.append(f"Expected  : {ev:+.1f}% per trade")
    tier_lines=[]
    for t in ['T1','T2','T3']:
        st=tier_stats[t]
        if st['total']>0:
            tier_lines.append(f"  {t}: {st['win']/st['total']*100:.0f}% ({st['win']}/{st['total']})")
    if tier_lines: lines+=["","*Win Rate per Tier:*"]+tier_lines
    lines.append(f"\n*VERDICT: {verdict}*")
    return '\n'.join(lines)

def run():
    rows_minggu=baca_log(hari=7)
    rows_all=baca_semua()
    label=f"Minggu {date.today().strftime('%d/%m/%Y')}"
    msg=analisa(rows_minggu,label)
    if len(rows_all)>len(rows_minggu):
        msg+=f"\n\n_All-time: {len(rows_all)} trade_"
    result=kirim_wa(msg)
    print(f"WA analisa terkirim: {result}")
    print(msg)

if __name__=='__main__': run()
