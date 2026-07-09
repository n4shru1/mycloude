import os
import sys
import requests, json
from pathlib import Path

FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
STATE_FILE_ARG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/spse_state.json")
VISION_RESULTS_ARG = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/spse_vision_results.json")
WA_GROUPS = {
    "Makassar": "120363406350666051@g.us",
    "Manado":   "120363402270321041@g.us",
    "Surabaya": "120363423882448709@g.us",
}
LPSE_ORDER = [
    "Provinsi Sulawesi Selatan","Kota Makassar","Kab. Gowa","Kab. Maros","Kab. Bone",
    "Kota Pare Pare","Kota Palopo","Kab. Bulukumba","Kab. Sinjai","Kab. Wajo",
    "Kab. Luwu","Kab. Luwu Utara","Kab. Luwu Timur","Kab. Tana Toraja","Kab. Toraja Utara",
    "Kab. Pinrang","Kab. Sidenreng Rappang","Kab. Enrekang","Kab. Takalar","Kab. Jeneponto",
    "Kab. Bantaeng","Kab. Soppeng","Kab. Barru","Kab. Pangkep","Kab. Kepulauan Selayar",
    "Provinsi Sulawesi Utara","Kota Manado","Kota Bitung","Kota Tomohon","Kota Kotamobagu",
    "Kab. Minahasa","Kab. Minahasa Utara","Kab. Minahasa Selatan","Kab. Minahasa Tenggara",
    "Kab. Bolaang Mongondow","Kab. Bolaang Mongondow Utara","Kab. Bolaang Mongondow Selatan",
    "Kab. Bolaang Mongondow Timur","Kab. Kepulauan Sangihe","Kab. Kepulauan Talaud","Kab. Kepulauan Sitaro",
    "Provinsi Jawa Timur","Kota Surabaya","Kota Malang","Kota Kediri","Kota Blitar","Kota Madiun",
    "Kota Mojokerto","Kota Pasuruan","Kota Probolinggo","Kota Batu","Kab. Sidoarjo","Kab. Gresik",
    "Kab. Malang","Kab. Jember","Kab. Banyuwangi","Kab. Bojonegoro","Kab. Lamongan","Kab. Tuban",
    "Kab. Mojokerto","Kab. Jombang","Kab. Kediri","Kab. Blitar","Kab. Nganjuk","Kab. Ngawi",
    "Kab. Madiun","Kab. Magetan","Kab. Ponorogo","Kab. Trenggalek","Kab. Tulungagung","Kab. Pacitan",
    "Kab. Situbondo","Kab. Bondowoso","Kab. Probolinggo","Kab. Pasuruan","Kab. Lumajang",
    "Kab. Sampang","Kab. Pamekasan","Kab. Sumenep","Kab. Bangkalan",
]
order_map = {n: i for i,n in enumerate(LPSE_ORDER)}

state = json.loads(STATE_FILE_ARG.read_text())
findings  = state['findings_done']
cache_file = Path(state['cache_file'])
tanggal   = state['tanggal']

vision_results_path = VISION_RESULTS_ARG
if vision_results_path.exists():
    vision_results = json.loads(vision_results_path.read_text())
    try: cache = json.loads(cache_file.read_text(encoding='utf-8'))
    except: cache = {}
    cache.update(vision_results)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding='utf-8')

    for item in state.get('vision_queue', []):
        tid    = item['tender_id']
        result = vision_results.get(tid, 'UNCLEAR')
        if result == 'NO_AC': continue
        grup = item['grup']
        nama = item['nama_lpse']
        findings.setdefault(grup, {}).setdefault(nama, []).append({
            'paket'   : item['paket'],
            'hps'     : item['hps'],
            'status'  : item['status'],
            'kategori': 'Konstruksi Gedung',
            'url'     : f'https://curious-moonbeam-ce5386.netlify.app?lpse={item["lpse_path"]}&id={tid}&type=lelang',
            'pdf_note': '✅ Konfirmed: Ada pekerjaan AC' if result == 'HAS_AC' else
                        ('✅ Konfirmed: Ada pekerjaan AC' if result == 'CONFIRMED_AC' else
                         '⚠️ PDF tidak detail — cek manual')
        })
    print(f"Vision results merged: {len(vision_results)} PDF")

def kirim_wa(target, pesan):
    requests.post('https://api.fonnte.com/send',
        headers={'Authorization': FONNTE_TOKEN},
        data={'target': os.environ.get('WA_TEST_OVERRIDE') or target, 'message': pesan, 'countryCode': '62'}, timeout=15)

total_semua = 0
for wilayah, lpse_data in findings.items():
    total = sum(len(v) for v in lpse_data.values())
    total_semua += total
    if total == 0:
        print(f"{wilayah}: tidak ada temuan"); continue
    sorted_lpse = sorted(lpse_data.items(), key=lambda x: order_map.get(x[0], 999))
    out = [
        "🔔 *MONITORING SPSE ADHITAMA*",
        f"📅 {tanggal}",
        f"📍 Wilayah: *{wilayah.upper()}*",
        f"📦 Ditemukan *{total} paket* dari {len(sorted_lpse)} LPSE\n"
    ]
    for ln, items in sorted_lpse:
        out.append(f"━━━ 🏙️ *{ln}* ({len(items)} paket)")
        for i, it in enumerate(items, 1):
            ikon = "🏗️" if it['kategori']=='Konstruksi Gedung' else "❄️"
            out.append(f"\n{ikon} *{i}. {it['paket']}*")
            out.append(f"💰 HPS: Rp {it['hps']}")
            out.append(f"📊 Status: {it['status']}")
            if it.get('pdf_note'): out.append(it['pdf_note'])
            out.append(f"🔗 {it['url']}")
        out.append("")
    out.append("_Adhitama Monitoring System_")
    pesan = "\n".join(out)
    print(pesan)
    kirim_wa(WA_GROUPS[wilayah], pesan)
    print(f"\n✅ Terkirim ke grup {wilayah}: {total} paket\n")

print(f"Selesai! Total: {total_semua} paket")
