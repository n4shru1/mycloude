#!/usr/bin/env python3
"""
Generate HTML weekly report for sales team (no ranking/colors).
Usage: python3 generate_html_sales.py
Output: report_sales_{bulan}{tahun}_m{N}.html  (e.g. report_sales_jun2026_m4.html)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sales_reminder import (
    get_pipeline, get_laporan_harian, get_web_aktivitas,
    SALES_CONFIG, BASE_DIR, fmt_nilai, id_date
)
from datetime import date, timedelta, datetime
from pathlib import Path

BULAN_ID = {1:"jan",2:"feb",3:"mar",4:"apr",5:"mei",6:"jun",
            7:"jul",8:"agu",9:"sep",10:"okt",11:"nov",12:"des"}

def get_output_file(jumat_lalu):
    mnum  = (jumat_lalu.day - 1) // 7 + 1
    bulan = BULAN_ID[jumat_lalu.month]
    return Path(__file__).parent / f"report_sales_{bulan}{jumat_lalu.year}_m{mnum}.html"

OFFSETS   = [0, 1, 3, 4, 5, 6]
HARI_NAMA = ["Jumat", "Sabtu", "Senin", "Selasa", "Rabu", "Kamis"]
STAGE_LABEL = {"A": "On Process/PO", "B": "Deal/TTD", "C": "Negosiasi", "D": "Ada Respon", "E": "Quotation"}
STAGE_EMOJI = {"A": "\U0001f3c6", "B": "\U0001f535", "C": "\U0001f7e1", "D": "\U0001f7e0", "E": "\U0001f534"}


def collect_data():
    today = date.today()
    jumat_lalu = today - timedelta(days=7)
    all_data = {}
    for kota, cfg in SALES_CONFIG.items():
        print("  Loading " + kota + "...")
        pipeline = get_pipeline(BASE_DIR / cfg["rekap_file"], cfg.get("onedrive_rekap"))
        days = []
        total_knj = total_fu = total_boq = total_web = 0
        for i, offset in enumerate(OFFSETS):
            d = jumat_lalu + timedelta(days=offset)
            entries  = get_laporan_harian(BASE_DIR / cfg["monitoring_file"], d, cfg.get("onedrive_monitoring"))
            web_acts = get_web_aktivitas(cfg["web_user_id"], d)
            knj  = [e["customer"] for e in entries if e.get("customer")]
            fu   = [e for e in entries if e.get("followup")]
            boq  = [e for e in entries if e.get("quo_baru")]
            foto = [a for a in web_acts if a["ada_foto"]]
            total_knj += len(knj)
            total_fu  += len(fu)
            total_boq += len(boq)
            if foto: total_web += 1
            days.append({
                "hari": HARI_NAMA[i], "tanggal": d.strftime("%d/%m"),
                "kunjungan": knj, "fu": fu, "boq": boq,
                "web_acts": web_acts, "web_foto": bool(foto),
            })
        all_data[kota] = {
            "nama": cfg["nama"], "pipeline": pipeline, "days": days,
            "total_knj": total_knj, "total_fu": total_fu,
            "total_boq": total_boq, "total_web": total_web,
        }
    return all_data, jumat_lalu


def generate_html(all_data, jumat_lalu):
    periode_akhir = jumat_lalu + timedelta(days=6)
    periode_str   = jumat_lalu.strftime("%d %b") + " – " + periode_akhir.strftime("%d %b %Y")
    bulan_str     = id_date("%B %Y")
    now_str       = datetime.now().strftime("%d %b %Y %H:%M")

    # ── Ringkasan tabel ───────────────────────────────────────
    kota_list = list(all_data.keys())
    th = "".join(f"<th>{k}<br><small>{all_data[k]['nama']}</small></th>" for k in kota_list)

    def row(label, vals):
        cells = "".join(f"<td>{v}</td>" for v in vals)
        return f"<tr><td class='mn'>{label}</td>{cells}</tr>"

    trows = (
        row("Kunjungan",       [all_data[k]["total_knj"] for k in kota_list])
        + row("FU Quo",        [all_data[k]["total_fu"]  for k in kota_list])
        + row("New Quo",       [all_data[k]["total_boq"] for k in kota_list])
        + row("Hari Upload Web", [f'{all_data[k]["total_web"]}/6' for k in kota_list])
        + row("WIN Bulan Ini", [all_data[k]["pipeline"]["win_bulan_ini"] for k in kota_list])
        + row("Proyek Aktif",  [all_data[k]["pipeline"]["total_aktif"]   for k in kota_list])
    )

    # ── Detail per sales ──────────────────────────────────────
    detail_html = ""
    for kota, d in all_data.items():
        # Pipeline badges
        badges = ""
        for s in ["A", "B", "C", "D", "E"]:
            n = d["pipeline"]["per_stage"][s]
            if n:
                badges += (f'<span class="badge">{STAGE_EMOJI[s]} Stage {s} '
                           f'({STAGE_LABEL[s]}): <strong>{n}</strong></span>')
        if not badges:
            badges = "<em>Belum ada proyek aktif</em>"

        # ETD alerts
        alerts = ""
        if d["pipeline"]["etd_dekat"]:
            items = "".join(
                f'[{p["stage"]}] {p["nama"]} &mdash; {p["etd"]} ({p["days"]} hr lagi)<br>'
                for p in d["pipeline"]["etd_dekat"][:4]
            )
            alerts += f'<div class="alert warn"><strong>⚠️ ETD Dekat:</strong><br>{items}</div>'
        if d["pipeline"]["etd_terlewat"]:
            items = "".join(
                f'[{p["stage"]}] {p["nama"]} &mdash; sejak {p["etd"]}<br>'
                for p in d["pipeline"]["etd_terlewat"][:4]
            )
            alerts += f'<div class="alert danger"><strong>\U0001f6a8 ETD Terlewat:</strong><br>{items}</div>'

        # Daily rows
        day_rows = ""
        for day in d["days"]:
            knj_str = ("<br>".join(f"• {k}" for k in day["kunjungan"])
                       if day["kunjungan"] else "<em>-</em>")
            fu_str  = ("<br>".join(
                f"• {e['followup'][:40]}{fmt_nilai(e.get('nilai'))}"
                for e in day["fu"]) if day["fu"] else "<em>-</em>")
            boq_str = ("<br>".join(
                f"• {e['quo_baru'][:40]}{fmt_nilai(e.get('nilai'))}"
                for e in day["boq"]) if day["boq"] else "<em>-</em>")
            if day["web_acts"]:
                web_icon = "✅" if day["web_foto"] else "⚠️"
                web_str  = web_icon + "<br>" + "<br>".join(
                    f"• {a['judul'][:35]}" + (" \U0001f4f7" if a["ada_foto"] else "")
                    for a in day["web_acts"]
                )
            else:
                web_str = "❌"

            day_rows += f"""<tr>
              <td><strong>{day["hari"]}</strong><br><small>{day["tanggal"]}</small></td>
              <td>{knj_str}</td><td>{fu_str}</td><td>{boq_str}</td><td>{web_str}</td>
            </tr>"""

        win_bi   = d["pipeline"]["win_bulan_ini"]
        win_line = (f"✅ <strong>{win_bi} WIN</strong> bulan ini"
                    if win_bi else "❌ Belum ada WIN bulan ini")

        detail_html += f"""
      <div class="detail">
        <h3>\U0001f4cd {kota} &mdash; {d["nama"]}</h3>

        <div class="subsec">
          <div class="sublabel">\U0001f4c5 Aktivitas Pekan Ini</div>
          <table class="atbl">
            <thead><tr>
              <th>Hari</th><th>Kunjungan</th><th>FU Quo</th><th>New Quo</th><th>Web</th>
            </tr></thead>
            <tbody>{day_rows}</tbody>
          </table>
        </div>

        <div class="subsec">
          <div class="sublabel">\U0001f4c6 Update Bulanan &mdash; {bulan_str}</div>
          <p style="margin-bottom:10px;font-size:13px">{win_line}
            &nbsp;&nbsp;\U0001f4e6 Total aktif: <strong>{d["pipeline"]["total_aktif"]} proyek</strong>
          </p>
          <div class="badges">{badges}</div>
          {alerts}
        </div>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laporan Mingguan Sales &mdash; Adhitama</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f0f4f8;color:#1e293b;font-size:14px}}
.wrap{{max-width:980px;margin:0 auto;padding:24px 16px}}
h1{{font-size:1.4rem;color:#0f172a}}
.sub{{color:#64748b;font-size:.85rem;margin:4px 0 24px}}
h2{{font-size:.95rem;font-weight:700;color:#0f172a;margin:28px 0 12px;
    border-left:4px solid #3b82f6;padding-left:10px}}
h3{{font-size:.95rem;font-weight:700;margin-bottom:16px}}

.ctbl{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;
       overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.ctbl th{{background:#1e40af;color:#fff;padding:10px 14px;text-align:center;font-size:13px}}
.ctbl td{{padding:9px 14px;text-align:center;border-bottom:1px solid #e2e8f0;font-size:13px}}
.ctbl tr:last-child td{{border-bottom:none;background:#f8fafc}}
.mn{{text-align:left!important;color:#475569;font-weight:500}}

.detail{{background:#fff;border-radius:12px;padding:20px;
         margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.subsec{{margin-bottom:16px}}
.sublabel{{font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;
           letter-spacing:.05em;margin-bottom:10px}}
.badges{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}
.badge{{background:#f1f5f9;border-radius:6px;padding:4px 10px;font-size:12px}}
.alert{{padding:9px 13px;border-radius:8px;font-size:12px;margin-bottom:8px;line-height:1.6}}
.warn{{background:#fef9c3;border-left:4px solid #eab308}}
.danger{{background:#fee2e2;border-left:4px solid #ef4444}}
.atbl{{width:100%;border-collapse:collapse;font-size:12px}}
.atbl th{{background:#f8fafc;padding:7px 10px;text-align:left;
          border-bottom:1.5px solid #e2e8f0;white-space:nowrap;color:#475569}}
.atbl td{{padding:7px 10px;vertical-align:top;border-bottom:1px solid #f1f5f9;line-height:1.5}}
.atbl tr:last-child td{{border-bottom:none}}
.footer{{text-align:center;color:#94a3b8;font-size:.75rem;margin-top:24px}}
</style>
</head>
<body>
<div class="wrap">
  <h1>\U0001f4ca Laporan Mingguan Sales &mdash; Adhitama</h1>
  <p class="sub">Periode: {periode_str} &nbsp;&bull;&nbsp; Dibuat: {now_str}</p>

  <h2>\U0001f4cb Ringkasan Pekan Ini</h2>
  <table class="ctbl">
    <thead><tr><th>Metrik</th>{th}</tr></thead>
    <tbody>{trows}</tbody>
  </table>

  <h2>\U0001f4c1 Detail Per Sales</h2>
  {detail_html}

  <div class="footer">Adhitama Sales Monitoring &mdash; Laporan Otomatis</div>
</div>
</body>
</html>"""


def main():
    print("Mengumpulkan data...")
    all_data, jumat_lalu = collect_data()
    output_file = get_output_file(jumat_lalu)
    print("Membuat HTML...")
    html = generate_html(all_data, jumat_lalu)
    output_file.write_text(html, encoding="utf-8")
    print("Selesai! File: " + str(output_file))


if __name__ == "__main__":
    main()
