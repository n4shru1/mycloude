#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import urllib.request
from datetime import date, timedelta, datetime
from pathlib import Path

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

from generate_html_report import collect_data as collect_dir, generate_html as gen_dir, get_output_file as outfile_dir
from generate_html_sales  import collect_data as collect_sales, generate_html as gen_sales, get_output_file as outfile_sales

BULAN_ID = {1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",
            7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"}


def send_telegram_doc(path, caption=""):
    url = "https://api.telegram.org/bot" + TG_TOKEN + "/sendDocument"
    boundary = "TGBoundary7x"
    with open(path, "rb") as f:
        file_data = f.read()

    def field(name, value):
        return ("--" + boundary + "\r\nContent-Disposition: form-data; "
                "name=\"" + name + "\"\r\n\r\n" + value + "\r\n").encode()

    body = (
        field("chat_id", TG_CHAT)
        + field("caption", caption)
        + ("--" + boundary + "\r\nContent-Disposition: form-data; "
           "name=\"document\"; filename=\"" + path.name + "\"\r\n"
           "Content-Type: text/html\r\n\r\n").encode()
        + file_data
        + ("\r\n--" + boundary + "--\r\n").encode()
    )
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary}
    )
    urllib.request.urlopen(req)
    print("Terkirim: " + path.name)


def main():
    today      = date.today()
    jumat_lalu = today - timedelta(days=7)
    mnum       = (jumat_lalu.day - 1) // 7 + 1
    bulan      = BULAN_ID[jumat_lalu.month]
    tahun      = jumat_lalu.year
    periode_akhir = jumat_lalu + timedelta(days=6)
    periode_str   = (jumat_lalu.strftime("%d") + " - "
                     + periode_akhir.strftime("%d ") + bulan + " " + str(tahun))

    print("=" * 50)
    print("Periode: " + periode_str + "  (M" + str(mnum) + ")")
    print("=" * 50)

    print("\n[1/4] Mengumpulkan data direktur...")
    data_dir, jl = collect_dir()
    print("[2/4] Membuat HTML direktur...")
    path_dir = outfile_dir(jl)
    path_dir.write_text(gen_dir(data_dir, jl), encoding="utf-8")
    print("      -> " + str(path_dir))

    print("[3/4] Mengumpulkan data + membuat HTML sales...")
    data_sales, jl2 = collect_sales()
    path_sales = outfile_sales(jl2)
    path_sales.write_text(gen_sales(data_sales, jl2), encoding="utf-8")
    print("      -> " + str(path_sales))

    print("[4/4] Mengirim via Telegram...")
    caption = ("Laporan Mingguan Sales M" + str(mnum) + " - " + bulan + " " + str(tahun) + "\n"
               "Periode: " + periode_str + "\n"
               "Dibuat: " + datetime.now().strftime("%d %b %Y %H:%M") + " WITA")
    send_telegram_doc(path_dir,   caption + "\n\nVersi Direktur (ada ranking)")
    send_telegram_doc(path_sales, caption + "\n\nVersi Sales (tanpa ranking)")
    print("\nSelesai!")


if __name__ == "__main__":
    main()
