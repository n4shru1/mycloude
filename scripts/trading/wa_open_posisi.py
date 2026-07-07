import json, os, glob, requests
from datetime import date
from pathlib import Path

FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
WA_TARGET    = '120363427350363923@g.us'
TRADING_DIR  = Path(__file__).resolve().parents[2] / "data" / "trading"

def kirim_wa(pesan):
    resp = requests.post(
        'https://api.fonnte.com/send',
        headers={'Authorization': FONNTE_TOKEN},
        data={'target': os.environ.get('WA_TEST_OVERRIDE') or WA_TARGET, 'message': pesan}
    )
    return resp.json()

def cari_plan():
    today = date.today().strftime('%Y-%m-%d')
    path  = TRADING_DIR / f'plan_{today}.json'
    if path.exists():
        return path
    files  = sorted(glob.glob(str(TRADING_DIR / 'plan_*.json')))
    return Path(files[-1]) if files else None

def run():
    plan_path = cari_plan()
    if not plan_path:
        print('Tidak ada plan.'); return

    with open(plan_path) as f:
        plan = json.load(f)

    label  = plan.get('label', str(date.today()))
    stocks = plan.get('stocks', [])

    if not stocks:
        kirim_wa(f"*IDX Open Posisi — {label}*\n\nTidak ada saham plan hari ini.")
        return

    lines = [f"*IDX Open Posisi — {label}*\n"]
    for s in stocks:
        tier = s.get('tier','?')
        icon = '🟢' if tier=='T1' else '🔵' if tier=='T2' else '🟡'
        lines.append(
            f"{icon} *{s['kode']}* ({tier} · {s.get('score',0)}/10)\n"
            f"   Entry : {s.get('entry_lo',0):,}–{s.get('entry_hi',0):,}\n"
            f"   TP1/2 : {s.get('tp1',0):,} / {s.get('tp2',0):,}\n"
            f"   CL    : {s.get('cl',0):,}\n"
        )
    lines.append("*Trail: naikkan CL ke entry setelah +3%*")
    lines.append("_Max hold 5 hari_")

    result = kirim_wa('\n'.join(lines))
    print(f"WA terkirim: {result}")

if __name__ == '__main__':
    run()
