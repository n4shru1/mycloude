import requests, re, time, json, urllib3, sys
from io import BytesIO
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from pdfminer.high_level import extract_text as pdf_extract
    PDF_OK = True
except ImportError:
    PDF_OK = False

BASE_URL   = "https://spse.inaproc.id"
NETLIFY    = "https://curious-moonbeam-ce5386.netlify.app"
CACHE_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/spse_pdf_cache.json")
STATE_FILE = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/spse_state.json")
PDF_DIR    = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/spse_pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

LPSE_LIST = [
    ("Provinsi Sulawesi Selatan","sulselprov","Makassar"),
    ("Kota Makassar","makassar","Makassar"),
    ("Kab. Gowa","gowakab","Makassar"),
    ("Kab. Maros","maroskab","Makassar"),
    ("Kab. Bone","bone","Makassar"),
    ("Kota Pare Pare","pareparekota","Makassar"),
    ("Kota Palopo","palopokota","Makassar"),
    ("Kab. Bulukumba","bulukumbakab","Makassar"),
    ("Kab. Sinjai","sinjaikab","Makassar"),
    ("Kab. Wajo","wajokab","Makassar"),
    ("Kab. Luwu","luwukab","Makassar"),
    ("Kab. Luwu Utara","luwuutarakab","Makassar"),
    ("Kab. Luwu Timur","luwutimurkab","Makassar"),
    ("Kab. Tana Toraja","tanatorajakab","Makassar"),
    ("Kab. Toraja Utara","torajautarakab","Makassar"),
    ("Kab. Pinrang","pinrangkab","Makassar"),
    ("Kab. Sidenreng Rappang","sidrapkab","Makassar"),
    ("Kab. Enrekang","enrekangkab","Makassar"),
    ("Kab. Takalar","takalarkab","Makassar"),
    ("Kab. Jeneponto","jenepontokab","Makassar"),
    ("Kab. Bantaeng","bantaengkab","Makassar"),
    ("Kab. Soppeng","soppeng","Makassar"),
    ("Kab. Barru","barrukab","Makassar"),
    ("Kab. Pangkep","pangkepkab","Makassar"),
    ("Kab. Kepulauan Selayar","kepulauanselayarkab","Makassar"),
    ("Provinsi Sulawesi Utara","sulutprov","Manado"),
    ("Kota Manado","manadokota","Manado"),
    ("Kota Bitung","bitungkota","Manado"),
    ("Kota Tomohon","tomohon","Manado"),
    ("Kota Kotamobagu","kotamobagu","Manado"),
    ("Kab. Minahasa","minahasa","Manado"),
    ("Kab. Minahasa Utara","minut","Manado"),
    ("Kab. Minahasa Selatan","minselkab","Manado"),
    ("Kab. Minahasa Tenggara","mitrakab","Manado"),
    ("Kab. Bolaang Mongondow","bolmongkab","Manado"),
    ("Kab. Bolaang Mongondow Utara","bolmutkab","Manado"),
    ("Kab. Bolaang Mongondow Selatan","bolselkab","Manado"),
    ("Kab. Bolaang Mongondow Timur","boltimkab","Manado"),
    ("Kab. Kepulauan Sangihe","sangihekab","Manado"),
    ("Kab. Kepulauan Talaud","talaudkab","Manado"),
    ("Kab. Kepulauan Sitaro","sitarokab","Manado"),
    ("Provinsi Jawa Timur","jatimprov","Surabaya"),
    ("Kota Surabaya","surabaya","Surabaya"),
    ("Kota Malang","malangkota","Surabaya"),
    ("Kota Kediri","kedirikota","Surabaya"),
    ("Kota Blitar","blitarkota","Surabaya"),
    ("Kota Madiun","madiunkota","Surabaya"),
    ("Kota Mojokerto","mojokertokota","Surabaya"),
    ("Kota Pasuruan","pasuruankota","Surabaya"),
    ("Kota Probolinggo","probolinggokota","Surabaya"),
    ("Kota Batu","batukota","Surabaya"),
    ("Kab. Sidoarjo","sidoarjokab","Surabaya"),
    ("Kab. Gresik","gresikkab","Surabaya"),
    ("Kab. Malang","malangkab","Surabaya"),
    ("Kab. Jember","jemberkab","Surabaya"),
    ("Kab. Banyuwangi","banyuwangikab","Surabaya"),
    ("Kab. Bojonegoro","bojonegorokab","Surabaya"),
    ("Kab. Lamongan","lamongankab","Surabaya"),
    ("Kab. Tuban","tubankab","Surabaya"),
    ("Kab. Mojokerto","mojokertokab","Surabaya"),
    ("Kab. Jombang","jombangkab","Surabaya"),
    ("Kab. Kediri","kedirikab","Surabaya"),
    ("Kab. Blitar","blitarkab","Surabaya"),
    ("Kab. Nganjuk","nganjukkab","Surabaya"),
    ("Kab. Ngawi","ngawikab","Surabaya"),
    ("Kab. Madiun","madiunkab","Surabaya"),
    ("Kab. Magetan","magetan","Surabaya"),
    ("Kab. Ponorogo","ponorogo","Surabaya"),
    ("Kab. Trenggalek","trenggalekkab","Surabaya"),
    ("Kab. Tulungagung","tulungagung","Surabaya"),
    ("Kab. Pacitan","pacitankab","Surabaya"),
    ("Kab. Situbondo","situbondokab","Surabaya"),
    ("Kab. Bondowoso","bondowosokab","Surabaya"),
    ("Kab. Probolinggo","probolinggokab","Surabaya"),
    ("Kab. Pasuruan","pasuruankab","Surabaya"),
    ("Kab. Lumajang","lumajangkab","Surabaya"),
    ("Kab. Sampang","sampangkab","Surabaya"),
    ("Kab. Pamekasan","pamekasankab","Surabaya"),
    ("Kab. Sumenep","sumenepkab","Surabaya"),
    ("Kab. Bangkalan","bangkalankab","Surabaya"),
]

AC_KW_NAME = [' ac ','air conditioner','pendingin ruangan','air cooler','chiller','hvac','ac split','vrv','vrf']
AC_KW_PDF  = ['tata udara',' ac ','air conditioner','pendingin ruangan','air cooler','chiller','hvac','ac split','vrv','vrf','pendingin']
BLD_KW   = ['gedung','bangunan','kantor','sekolah','rumah sakit','puskesmas','masjid','balai','asrama','ruang kelas','lantai','gudang','aula','perpustakaan','poliklinik','hunian','rumah dinas','wisma','pasar','terminal','stadion','klinik','laboratorium']
ACT_KW   = ['pembangunan','rehabilitasi','rehab','renovasi','revitalisasi','peningkatan','perbaikan']
SKIP_S   = ['sudah selesai','batal','gagal']
SKIP_INFRA = ['jalan','jembatan','irigasi','drainase','saluran','sungai','embung','bendung','sumur','spam','talud','pedestrian','kawasan','penataan','plengsengan','tanggul','tebing','betonisasi','paving','trotoar','taman','rth','ruang terbuka']
SKIP_PEKERJAAN = [
    'pagar','pengecatan','cat tembok','cat ulang',
    'atap','genteng','rangka atap',
    'toilet','kamar mandi',' wc ','septik','septic',
    'keramik','granit','lantai keramik',
    'sanitasi','plumbing','perpipaan',
    'kolam','sumur','pompa air',
    'landscape','penghijauan',
    'meubelair','meubel','furniture','perabot',
    'papan nama','neon box','signage',
    'paving blok','rabat beton',
    'makam','rumah pompa','ipal','cuci kendaraan','cuci mobil',
    'waduk','embung','tpa ','pju','penerangan jalan',
]

def load_cache():
    try: return json.loads(CACHE_FILE.read_text(encoding='utf-8'))
    except: return {}
def save_cache(c):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding='utf-8')
    except: pass

pdf_cache = load_cache()
cache_hits = 0
cache_new  = 0

def clean(s): return re.sub(r'<[^>]+>','',str(s)).strip()
def is_active(s): return not any(x in s.lower() for x in SKIP_S)
def is_bldg(n):
    l = n.lower()
    if any(s in l for s in SKIP_INFRA): return False
    if any(s in l for s in SKIP_PEKERJAAN): return False
    return any(a in l for a in ACT_KW) and any(b in l for b in BLD_KW)
def is_ac(n):
    l = ' ' + n.lower() + ' '
    return any(k in l for k in AC_KW_NAME)


def download_and_check_pdf(path, tid):
    """Download PDF dari halaman detail SPSE, parse link /dl/, cek isinya."""
    pdf_file = PDF_DIR / f"{tid}.pdf"
    listing_url = f'{BASE_URL}/{path}/lelang'
    try: session.get(listing_url, timeout=10)
    except: pass
    detail_url = f'{BASE_URL}/{path}/lelang/{tid}/pengumumanlelang'
    try:
        netlify_ref = f'https://curious-moonbeam-ce5386.netlify.app?lpse={path}&id={tid}&type=lelang'
        r = session.get(detail_url, timeout=15,
                        headers={'Referer': netlify_ref})
        if r.status_code != 200:
            return "UNCLEAR", None
        m = (re.search(r'href="(/'+re.escape(path)+r'/dl/[a-f0-9]+)"', r.text) or
             re.search(r'href="([^"]+/dl/[a-f0-9]+)"', r.text) or
             re.search(r'(/[^"\s]+/dl/[a-f0-9]+)', r.text))
        if not m:
            return "UNCLEAR", None
        pdf_url = BASE_URL + m.group(1)
        pdf_r = session.get(pdf_url, timeout=30, headers={'Referer': detail_url})
        if pdf_r.status_code != 200 or len(pdf_r.content) < 1000:
            return "UNCLEAR", None
        pdf_file.write_bytes(pdf_r.content)
    except Exception as e:
        return "UNCLEAR", None
    if PDF_OK:
        try:
            text = pdf_extract(BytesIO(pdf_file.read_bytes())).lower()
            if len(text.strip()) > 100:
                if any(k in text for k in AC_KW_PDF):
                    return "CONFIRMED_AC", None
                if text.count('pekerjaan') >= 3 or len(text) > 500:
                    return "NO_AC", None
                return "UNCLEAR", None
            else:
                return "PENDING_VISION", str(pdf_file)
        except:
            return "PENDING_VISION", str(pdf_file)
    return "PENDING_VISION", str(pdf_file)

def check_pdf_hybrid(path, tid):
    global cache_hits, cache_new
    if tid in pdf_cache:
        cache_hits += 1
        return pdf_cache[tid], None
    result, vpath = download_and_check_pdf(path, tid)
    if result != "PENDING_VISION":
        pdf_cache[tid] = result
        save_cache(pdf_cache)
    cache_new += 1
    if result == "PENDING_VISION":
        print(f"  [{tid}] -> PENDING_VISION")
    return result, vpath


def fetch_rows(path, ptype, kat, tahun):
    pu = 'nontender' if ptype=='nontender' else 'lelang'
    de = 'pl' if ptype=='nontender' else 'lelang'
    url = f'{BASE_URL}/{path}/{pu}?tahun={tahun}&kategoriId={kat}'
    try:
        r  = session.get(url, timeout=12)
        m  = re.search(r"authenticityToken = '([^']+)'", r.text)
        if not m: return []
        tok = m.group(1)
        dm  = re.search(r'url\s*:\s*"(/[^"]+/dt/'+de+r'[^"]*)"', r.text)
        dtu = BASE_URL+dm.group(1) if dm else f'{BASE_URL}/{path}/dt/{de}?tahun={tahun}&kategoriId={kat}'
        dr  = session.post(dtu, data={'draw':'1','start':'0','length':'200','authenticityToken':tok}, timeout=18, headers={'Referer':url})
        return dr.json().get('data',[])
    except: return []

def fetch_lpse(nama, path, grup):
    results = []
    for kat, ptype in [(2,'lelang'),(0,'lelang'),(0,'nontender')]:
        for row in fetch_rows(path, ptype, kat, 2026):
            p = clean(row[1]) if len(row)>1 else ''
            s = clean(row[3]) if len(row)>3 else ''
            h = str(row[4]) if len(row)>4 else '-'
            k = str(row[0]) if len(row)>0 else ''
            if ptype != 'nontender' and not is_active(s): continue
            results.append((nama, path, grup, p, h, s, k, ptype, kat))
        time.sleep(0.1)
    return results

print(f"=== SPSE Monitor Fase 1 === {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print(f"Cache PDF: {len(pdf_cache)} tender tersimpan")
print("-"*50)

all_rows = []
with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(fetch_lpse, n, p, g): n for n,p,g in LPSE_LIST}
    for f in as_completed(futures):
        try: all_rows.extend(f.result())
        except: pass

print(f"Total baris data: {len(all_rows)}")

vision_queue  = []
findings_done = {"Makassar":{},"Manado":{},"Surabaya":{}}

konstruksi_items = [r for r in all_rows if r[7]=='lelang' and r[8]==2 and is_bldg(r[3])]
cached_items = [r for r in konstruksi_items if r[6] in pdf_cache]
new_items    = [r for r in konstruksi_items if r[6] not in pdf_cache]

print(f"Konstruksi Gedung: {len(konstruksi_items)} total ({len(new_items)} baru, {len(cached_items)} cache)")

for item in cached_items:
    nama, path, grup, p, h, s, k, ptype, kat = item
    result = pdf_cache[k]
    cache_hits += 1
    if result == 'NO_AC': continue
    findings_done[grup].setdefault(nama,[]).append({
        'paket':p,'hps':h,'status':s,'kategori':'Konstruksi Gedung',
        'url':f'https://curious-moonbeam-ce5386.netlify.app?lpse={path}&id={k}&type=lelang',
        'pdf_note':'⚠️ PDF tidak detail — cek manual' if result=='UNCLEAR' else
                   ('✅ Konfirmed: Ada pekerjaan AC' if result in ('CONFIRMED_AC','HAS_AC') else '')
    })

def do_pdf_check(item):
    nama, path, grup, p, h, s, k, ptype, kat = item
    result, vpath = check_pdf_hybrid(path, k)
    return (nama, path, grup, p, h, s, k, result, vpath)

if new_items:
    print("Cooldown 30s sebelum PDF check...")
    time.sleep(30)
    for item in new_items:
        time.sleep(5)
        res = do_pdf_check(item)
        nama, path, grup, p, h, s, k, result, vpath = res
        if result == 'PENDING_VISION':
            vision_queue.append({
                'tender_id':k,'pdf_path':vpath,'nama_lpse':nama,
                'paket':p,'hps':h,'status':s,'grup':grup,'lpse_path':path
            })
        elif result != 'NO_AC':
            findings_done[grup].setdefault(nama,[]).append({
                'paket':p,'hps':h,'status':s,'kategori':'Konstruksi Gedung',
                'url':f'https://curious-moonbeam-ce5386.netlify.app?lpse={path}&id={k}&type=lelang',
                'pdf_note':'⚠️ PDF tidak detail — cek manual' if result=='UNCLEAR' else
                           ('✅ Konfirmed: Ada pekerjaan AC' if result in ('CONFIRMED_AC','HAS_AC') else '')
            })

for nama, path, grup, p, h, s, k, ptype, kat in all_rows:
    if kat == 0 and is_ac(p):
        findings_done[grup].setdefault(nama,[]).append({
            'paket':p,'hps':h,'status':s,'kategori':'Pengadaan AC',
            'url':f'https://curious-moonbeam-ce5386.netlify.app?lpse={path}&id={k}&type={"nontender" if ptype=="nontender" else "lelang"}',
            'pdf_note':''
        })

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
STATE_FILE.write_text(json.dumps({
    'findings_done':findings_done,'vision_queue':vision_queue,
    'cache_hits':cache_hits,'cache_new':cache_new,
    'tanggal':datetime.now().strftime('%d %B %Y'),
    'cache_file':str(CACHE_FILE)
}, ensure_ascii=False, indent=2))

print(f"Cache: {cache_hits} hit, {cache_new} baru dicek")
print(f"Vision queue: {len(vision_queue)} PDF perlu Claude vision")
print(f"Findings selesai: {sum(len(v) for d in findings_done.values() for v in d.values())} paket")
print("Fase 1 selesai.")
