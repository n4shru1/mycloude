import os
import requests
from datetime import datetime, date

FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]
ADHITAMA_USERNAME = os.environ["ADHITAMA_USERNAME"]
ADHITAMA_PASSWORD = os.environ["ADHITAMA_PASSWORD"]
GROUPS = {
    "Manado": "120363402270321041@g.us",
    "Makassar": "120363406350666051@g.us",
    "Surabaya": "120363423882448709@g.us",
}
POLAR_GROUP = "120363421796568152@g.us"
AREAS = {"Manado": 3, "Makassar": 2, "Surabaya": 4}
SKIP_IDS = [135]
NOTES = {
    "Klinik Rafisa": "📝 *Catatan: Kendala PLN di lokasi, bukan kendala internal*",
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

def get_note(nama):
    for key, note in NOTES.items():
        if key.lower() in nama.lower():
            return note
    return None

def analisis(progress, persen_masuk):
    if persen_masuk > progress + 20:
        return "⚡ Pembayaran lebih maju dari progres — percepat penyelesaian pekerjaan!"
    elif progress > persen_masuk + 20:
        return "💰 Progres bagus, segera kejar penagihan!"
    elif progress >= 90 and persen_masuk >= 90:
        return "🎯 Hampir selesai, segera tuntaskan!"
    else:
        return "✅ On track"

def deadline_info(end_str):
    if not end_str or end_str == '-':
        return None
    try:
        end_date = date.fromisoformat(end_str[:10])
        sisa = (end_date - date.today()).days
        if sisa < 0:
            return f"🔴 *OVERDUE* — deadline {end_str[:10]}, belum selesai!"
        elif sisa <= 7:
            return f"⚠️ Deadline {end_str[:10]} — sisa *{sisa} hari*!"
        else:
            return f"⏳ Sisa: {sisa} hari"
    except:
        return None

def get_hasil(projects):
    hasil = []
    for p in projects:
        if p.get('id') in SKIP_IDS:
            continue
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
        nama = p.get('nama') or '(Tanpa Nama)'
        hasil.append({
            'nama': nama, 'progress': progress, 'persen_masuk': persen_masuk,
            'start': (start[:10] if start else '-'),
            'end': (end[:10] if end else '-'),
            'analisis': analisis(progress, persen_masuk),
            'deadline_label': deadline_info(end[:10] if end else '-'),
            'note': get_note(nama),
        })
    return hasil

def format_blok_area(area, proyek_list):
    lines = [f"📍 *{area.upper()}*", ""]
    if not proyek_list:
        lines.append("📭 Tidak ada proyek ongoing saat ini.\n")
    else:
        for i, p in enumerate(proyek_list, 1):
            lines += [f"*{i}. {p['nama']}*", f"📆 Periode: {p['start']} s/d {p['end']}"]
            if p['deadline_label']:
                lines.append(p['deadline_label'])
            lines += [
                f"📊 Progres Pekerjaan: {int(p['progress'])}%",
                f"💵 Pembayaran Masuk: {p['persen_masuk']:.1f}%",
                f"🔍 Analisis: {p['analisis']}",
            ]
            if p['note']:
                lines.append(p['note'])
            lines.append("")
    return "\n".join(lines)

def format_pesan_area(area, proyek_list):
    bulan = ['Januari','Februari','Maret','April','Mei','Juni','Juli',
             'Agustus','September','Oktober','November','Desember']
    now = datetime.now()
    tgl = f"{now.day} {bulan[now.month-1]} {now.year}"
    lines = [
        f"📊 *UPDATE PROYEK ONGOING - {area.upper()}*",
        f"📅 {tgl}",
        "━━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    if not proyek_list:
        lines.append("📭 Tidak ada proyek ongoing saat ini.\n")
    else:
        for i, p in enumerate(proyek_list, 1):
            lines += [f"*{i}. {p['nama']}*", f"📆 Periode: {p['start']} s/d {p['end']}"]
            if p['deadline_label']:
                lines.append(p['deadline_label'])
            lines += [
                f"📊 Progres Pekerjaan: {int(p['progress'])}%",
                f"💵 Pembayaran Masuk: {p['persen_masuk']:.1f}%",
                f"🔍 Analisis: {p['analisis']}",
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

def format_pesan_polar(semua_area):
    bulan = ['Januari','Februari','Maret','April','Mei','Juni','Juli',
             'Agustus','September','Oktober','November','Desember']
    now = datetime.now()
    tgl = f"{now.day} {bulan[now.month-1]} {now.year}"
    lines = [
        "📊 *UPDATE PROYEK ONGOING - SEMUA AREA*",
        f"📅 {tgl}",
        "━━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    for area, proyek_list in semua_area.items():
        lines.append(format_blok_area(area, proyek_list))
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
    lines += [
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
    token = login()
    semua_area = {}

    for area, area_id in AREAS.items():
        projects = fetch_projects(token, area_id)
        hasil = get_hasil(projects)
        semua_area[area] = hasil
        pesan = format_pesan_area(area, hasil)
        send_wa(GROUPS[area], pesan)
        print(f"[{area}] Terkirim {len(hasil)} proyek")

    pesan_polar = format_pesan_polar(semua_area)
    send_wa(POLAR_GROUP, pesan_polar)
    print(f"[Polar] Terkirim semua area")

if __name__ == "__main__":
    main()
