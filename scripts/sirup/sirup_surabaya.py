import os
from playwright.sync_api import sync_playwright
import re, requests, calendar
from datetime import datetime
from collections import defaultdict
FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
TARGET_WA    = "120363423882448709@g.us"
TEST_MODE    = False
LOKASI_STR = "14839,14825,14819,14847"
KEYWORDS = ['rsud', 'rumah sakit', 'puskesmas', 'kesehatan', 'gedung']
# Dinamis: bulan ini sampai Desember
_now = datetime.now()
_year = _now.year
_bulan_list = list(range(_now.month, 13))
BULAN_STR = ','.join(str(b) for b in _bulan_list)
BULAN_OK = {calendar.month_name[m].lower() + f' {_year}' for m in _bulan_list}
def clean(s):
    return re.sub(r'\s+', ' ', str(s)).strip()
def fmt_rp(s):
    try:
        return f"Rp {int(float(str(s).replace(',',''))):,}".replace(',','.')
    except:
        return str(s)
def parse_kabkota(lokasi_raw):
    part = lokasi_raw.split('|')[0].strip()
    return ','.join(part.split(',')[1:]).strip() if ',' in part else part
today = datetime.now().strftime('%d/%m/%Y')
results = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ).new_page()
    print("Buka SiRUP ...")
    page.goto("https://sirup.inaproc.id/sirup/caripaketctr/index", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=60000)
    print(f"OK — filter bulan: {BULAN_STR}\n")
    for kw in KEYWORDS:
        print(f"Cari: '{kw}' ...", end=" ", flush=True)
        data = page.evaluate(f"""(async function(){{
            var params = [
                'tahunAnggaran=2026','jenisPengadaan=2','metodePengadaan=13',
                'minPagu=','maxPagu=','bulan={BULAN_STR}',
                'lokasi={LOKASI_STR}','kldi=','pdn=','ukm=',
                'draw=1','start=0','length=500',
                'search%5Bvalue%5D={kw}','search%5Bregex%5D=false',
                'columns%5B0%5D%5Bdata%5D=','columns%5B1%5D%5Bdata%5D=paket',
                'columns%5B2%5D%5Bdata%5D=pagu','columns%5B3%5D%5Bdata%5D=jenisPengadaan',
                'columns%5B4%5D%5Bdata%5D=isPDN','columns%5B5%5D%5Bdata%5D=isUMK',
                'columns%5B6%5D%5Bdata%5D=metode','columns%5B7%5D%5Bdata%5D=pemilihan',
                'columns%5B8%5D%5Bdata%5D=kldi','columns%5B9%5D%5Bdata%5D=satuanKerja',
                'columns%5B10%5D%5Bdata%5D=lokasi','columns%5B11%5D%5Bdata%5D=id',
                'order%5B0%5D%5Bcolumn%5D=5','order%5B0%5D%5Bdir%5D=DESC'
            ].join('&');
            try {{
                var r = await fetch('../caripaketctr/search?' + params);
                return await r.json();
            }} catch(e) {{ return {{error: e.toString()}}; }}
        }})()""")
        if not data or 'error' in (data or {}):
            print("ERROR"); continue
        masuk = 0
        for row in data.get('data', []):
            nama_paket = clean(row.get('paket',''))
            bulan_txt  = clean(row.get('pemilihan',''))
            if bulan_txt.lower().strip() not in BULAN_OK: continue
            key = (nama_paket, clean(row.get('satuanKerja','')))
            if key not in results and nama_paket:
                results[key] = {
                    "nama_paket": nama_paket,
                    "satker":     clean(row.get('satuanKerja','')),
                    "lokasi_raw": clean(row.get('lokasi','')),
                    "pagu":       row.get('pagu', 0),
                    "bulan":      bulan_txt,
                    "id_rup":     str(row.get('id','')),
                }
                masuk += 1
        print(f"{data.get('recordsFiltered',0)} total → {masuk} masuk")
    browser.close()
items = list(results.values())
print(f"\nTOTAL: {len(items)} paket\n")
grup = defaultdict(list)
for item in items:
    grup[parse_kabkota(item['lokasi_raw'])].append(item)
label_bulan = f"{calendar.month_name[_now.month][:3]}-Des {_year}"
pesan = f"📋 *SiRUP Surabaya & Sekitarnya*\n📅 {today}\n"
pesan += f"_Konstruksi · Tender · {label_bulan} · {len(items)} paket_\n"
for kabkota in sorted(grup.keys()):
    pesan += f"\n📍 *{kabkota}* ({len(grup[kabkota])} paket)\n"
    n = 0
    for item in grup[kabkota]:
        n += 1
        pesan += f"  {n}. {item['nama_paket'][:55]}\n"
        pesan += f"     🏛️ {item['satker'][:45]}\n"
        pesan += f"     💰 {fmt_rp(item['pagu'])}\n"
        pesan += f"     🗓️ {item['bulan']}\n"
        if item.get('id_rup'):
            pesan += f"     🔗 sirup.inaproc.id/sirup/rup/detailPaketPenyedia2020?idPaket={item['id_rup']}\n\n"
pesan += f"\n🌐 Source: sirup.inaproc.id — data rencana pengadaan\n⚠️ Mohon di-follow up & konfirmasi scope HVAC\n⚙️ Automation report by Adhitama"
print(pesan)
if not TEST_MODE:
    res = requests.post("https://api.fonnte.com/send",
        headers={"Authorization": FONNTE_TOKEN},
        data={"target": os.environ.get("WA_TEST_OVERRIDE") or TARGET_WA, "message": pesan}, timeout=15).json()
    print(f"\nKirim: {res}")
else:
    print("\n[TEST_MODE — WA tidak dikirim]")
