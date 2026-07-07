import os
import requests, json
from datetime import datetime, date
from pathlib import Path

FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
ADHITAMA_USERNAME = os.environ["ADHITAMA_USERNAME"]
ADHITAMA_PASSWORD = os.environ["ADHITAMA_PASSWORD"]
CACHE_FILE = Path(__file__).resolve().parents[2] / "data" / "piutang" / "piutang_cache.json"
GROUPS = {
    "Manado": "120363402270321041@g.us",
    "Makassar": "120363406350666051@g.us",
    "Surabaya": "120363423882448709@g.us",
}
AREAS = {"Manado": 3, "Makassar": 2, "Surabaya": 4}
NOTES = {
    "Klinik Rafisa": "⚠️ Catatan: Kendala PLN, belum bisa selesai & tagih",
}

def login():
    r = requests.post('https://apps.adhitama.id/api/auth/login',
        json={'username': ADHITAMA_USERNAME, 'password': ADHITAMA_PASSWORD})
    return r.json()['token']

def fetch_projects(token, area_id):
    r = requests.get(f'https://apps.adhitama.id/api/projects?limit=200&area_id={area_id}',
        headers={'Authorization': token})
    data = r.json()
    return data.get('data', data) if isinstance(data, dict) else data

def format_rp(n):
    return "Rp " + f"{int(n):,}".replace(",", ".")

def get_note(nama):
    for key, note in NOTES.items():
        if key.lower() in nama.lower():
            return note
    return None

def load_cache():
    try: return json.loads(CACHE_FILE.read_text())
    except: return {}

def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

def analyze(projects, cache):
    results = []
    today = date.today().isoformat()
    for p in projects:
        start = p.get('start_time') or ''
        end = p.get('end_time') or ''
        if '2026' not in start and '2026' not in end:
            continue
        if p.get('status') == 'Selesai':
            continue
        nilai = float(p.get('nilai_anggaran') or 0)
        progress = float(p.get('progress_manual') or 0)
        pembayaran = p.get('pembayaranProjects') or []
        total_masuk = sum(float(x.get('nilai') or 0) for x in pembayaran)
        persen_masuk = (total_masuk / nilai * 100) if nilai > 0 else 0
        gap = (nilai * progress / 100) - total_masuk
        if gap <= 1000:
            continue
        nama = p.get('nama') or '(Tanpa Nama)'
        note = get_note(nama)
        pid = str(p.get('id'))
        if note:
            usia = "-"
        else:
            if pid not in cache:
                cache[pid] = today
            usia = f"{(date.today() - date.fromisoformat(cache[pid])).days} hari"
        results.append({
            'nama': nama, 'nilai': nilai, 'progress': progress,
            'total_masuk': total_masuk, 'persen_masuk': persen_masuk,
            'gap': gap,
            'start': (start[:10] if start else '-'),
            'end': (end[:10] if end else '-'),
            'status': p.get('status') or '-',
            'note': note,
            'usia': usia,
        })
    return results

def format_pesan(area, proyek_list):
    bulan = ['Januari','Februari','Maret','April','Mei','Juni','Juli',
             'Agustus','September','Oktober','November','Desember']
    now = datetime.now()
    tgl = f"{now.day} {bulan[now.month-1]} {now.year}"
    lines = [
        f"📋 *LAPORAN PIUTANG PROYEK - {area.upper()}*",
        f"📅 {tgl}",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "🔴 *PROYEK PERLU PENAGIHAN*", ""
    ]
    for i, p in enumerate(proyek_list, 1):
        lines += [
            f"*{i}. {p['nama']}*",
            f"💰 Nilai Kontrak: {format_rp(p['nilai'])}",
            f"📊 Progres: {int(p['progress'])}%",
            f"💵 Sudah Masuk: {format_rp(p['total_masuk'])} ({p['persen_masuk']:.1f}%)",
            f"🎯 Bisa Ditagih: *{format_rp(p['gap'])}*",
            f"🕐 Usia Piutang: *{p['usia']}*",
            f"📆 Periode: {p['start']} s/d {p['end']}",
            f"ℹ️ Status: {p['status']}",
        ]
        if p['note']:
            lines.append(p['note'])
        lines.append("")
    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "_Data bersumber dari adhitama.id — pastikan data proyek selalu diperbarui di aplikasi._",
        "⚙️ _Automation report by Adhitama_"
    ]
    return "\n".join(lines)

def send_wa(target, message):
    r = requests.post('https://api.fonnte.com/send',
        headers={'Authorization': FONNTE_TOKEN},
        data={'target': os.environ.get('WA_TEST_OVERRIDE') or target, 'message': message, 'countryCode': '62'})
    return r.json()

def main():
    cache = load_cache()
    token = login()
    for area, area_id in AREAS.items():
        proyek = analyze(fetch_projects(token, area_id), cache)
        if not proyek:
            print(f"[{area}] Tidak ada piutang → skip")
            continue
        pesan = format_pesan(area, proyek)
        result = send_wa(GROUPS[area], pesan)
        print(f"[{area}] Terkirim {len(proyek)} proyek → {result}")
    save_cache(cache)

if __name__ == "__main__":
    main()
