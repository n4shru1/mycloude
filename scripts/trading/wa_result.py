import os
import yfinance as yf, json, glob, requests
from datetime import date, timedelta
from pathlib import Path

FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
WA_TARGET    = '120363427350363923@g.us'
TRADING_DIR  = Path(__file__).resolve().parents[2] / "data" / "trading"

def kirim_wa(pesan):
    resp = requests.post('https://api.fonnte.com/send',
        headers={'Authorization': FONNTE_TOKEN},
        data={'target': os.environ.get('WA_TEST_OVERRIDE') or WA_TARGET, 'message': pesan})
    return resp.json()

def cari_plan():
    for d in [0,1,2]:
        p = TRADING_DIR / f"plan_{(date.today()-timedelta(days=d)).strftime('%Y-%m-%d')}.json"
        if p.exists(): return p
    files = sorted(glob.glob(str(TRADING_DIR / 'plan_*.json')))
    return Path(files[-1]) if files else None

def fetch_harga(kode):
    try:
        tk=yf.Ticker(f'{kode}.JK')
        info=tk.fast_info
        hist=tk.history(period='1d',interval='1d')
        low=float(hist['Low'].iloc[-1]) if not hist.empty else None
        return float(info.last_price), float(info.day_high), low
    except: return None, None, None

def run():
    plan_path=cari_plan()
    if not plan_path: print('Tidak ada plan.'); return
    with open(plan_path) as f: plan=json.load(f)
    label=plan.get('label',''); stocks=plan.get('stocks',[])
    today=date.today().strftime('%d/%m/%Y')

    wins,losses,trails,holds,skips=[],[],[],[],[]

    for s in stocks:
        kode=s['kode']; tier=s.get('tier',''); score=s.get('score',0)
        entry_lo=s.get('entry_lo',0); entry_hi=s.get('entry_hi',0)
        tp1=s.get('tp1',0); tp2=s.get('tp2',0); cl=s.get('cl',0)

        # Fix: kalau entry_lo == entry_hi, hitung ulang
        if entry_lo >= entry_hi:
            entry_lo = int(entry_hi * 0.97)

        close,high,low=fetch_harga(kode)
        if close is None:
            holds.append(f"⬜ *{kode}* — data tidak tersedia\n"); continue

        cp=round((close-entry_lo)/entry_lo*100,1) if entry_lo else 0
        hp=round((high-entry_lo)/entry_lo*100,1) if entry_lo else 0

        zona_sentuh = low is not None and low <= entry_hi
        if zona_sentuh:
            zona_info=f"   ✅ Zona tersentuh (Low: {low:,.0f})"
        else:
            zona_info=f"   ❌ Zona tidak tersentuh (Low: {low:,.0f})" if low else "   ❓ Data low tidak tersedia"

        blok=(
            f"*{kode}* ({tier}·{score}/10)\n"
            f"   Zona Entry : {entry_lo:,}–{entry_hi:,}\n"
            f"{zona_info}\n"
            f"   Harga kini : {close:,.0f} ({cp:+.1f}% dari entry)\n"
            f"   High hari ini: {high:,.0f} ({hp:+.1f}%)\n"
        )

        if not zona_sentuh:
            skips.append(f"⬜ {blok}   → Skip, harga gap up\n")
        elif close <= cl:
            losses.append(
                f"❌ {blok}"
                f"   CL {cl:,} tertembus ⚠️\n"
                f"   → Posisi ditutup rugi\n")
        elif close >= tp1:
            wins.append(
                f"✅ {blok}"
                f"   TP1 {tp1:,} tercapai! 🎯\n"
                f"   → Jual 50%, sisa trail ke TP2 {tp2:,}\n")
        elif hp >= 3.0:
            aksi="Trail CL ke entry" if hp<8 else f"Trail CL ke TP1 {tp1:,}"
            trails.append(
                f"🔒 {blok}"
                f"   → {aksi}, modal aman\n")
        else:
            holds.append(
                f"🟡 {blok}"
                f"   TP1 {tp1:,} | CL {cl:,}\n"
                f"   → Tunggu, belum ada sinyal keluar\n")

    resolved=wins+trails+losses
    eff=len(wins)+len(trails)
    wr=eff/len(resolved)*100 if resolved else 0
    sep="─────────────────────"
    lines=[f"📋 *IDX Result — {today}*",f"_Plan: {label}_\n"]
    for grp in [wins,trails,holds,losses,skips]:
        for item in grp:
            lines.append(sep); lines.append(item)
    lines.append(sep)
    lines.append(
        f"\n📊 *RINGKASAN:*\n"
        f"✅ WIN: {len(wins)}  🔒 TRAIL: {len(trails)}  "
        f"❌ LOSS: {len(losses)}  🟡 HOLD: {len(holds)}  ⬜ SKIP: {len(skips)}\n"
        f"*Win Rate: {wr:.0f}%* ({eff}/{len(resolved)} resolved)")
    result=kirim_wa('\n'.join(lines))
    print(f"WA result terkirim: {result}")

if __name__=='__main__': run()
