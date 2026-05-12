# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from datasheet_parser.vdsemi_parser import parse_max_ratings
import pdfplumber

pdf_path = r"E:\tmp\datasheet\VS11170GMH_GL195N10L\VS11170GMH.pdf"
with pdfplumber.open(pdf_path) as pdf:
    rows = parse_max_ratings(pdf, "VS11170GMH")

tstg_rows = [r for r in rows if "TSTG" in r["symbol"].upper() or r["symbol"].upper().startswith("TJ")]
print("=== TSTG/TJ rows after fix ===")
for r in tstg_rows:
    print(f"  symbol={r['symbol']!r:15s}  value_raw={r['value_raw']!r}")

print()
print(f"Total max_ratings rows: {len(rows)}")
