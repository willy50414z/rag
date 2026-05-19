# -*- coding: utf-8 -*-
"""End-to-end test: parser -> normalizer -> expected symbols."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pdfplumber
from datasheet_parser.vdsemi_parser import parse_max_ratings, parse_electrical
from datasheet_parser.normalizer import normalize_parsed, normalize_symbol, normalize_channel, normalize_package, PACKAGE_WHITELIST

PASS = "OK"
FAIL = "FAIL"

# ---- unit: normalize_symbol ---
print("=== normalize_symbol unit tests ===")
cases = [
    ("TJ,TSTG",     "TSTG,TJ"),
    ("T , TSTG J",  "TSTG,TJ"),
    ("T TSTG J",    "TSTG,TJ"),
    ("TSTG,TJ",     "TSTG,TJ"),
    ("Td(off)",     "td(off)"),
    ("Td(on)",      "td(on)"),
    ("Tf",          "tf"),
    ("Tr",          "tr"),
    ("VGS(TH)",     "VGS(th)"),
    ("RDS(on)",     "RDS(on)"),
    ("Qg",          "Qg"),
    ("Qgd",         "Qgd"),
]
all_ok = True
for raw, expected in cases:
    got = normalize_symbol(raw)
    ok = got == expected
    all_ok = all_ok and ok
    print(f"  {raw!r:20s} -> {got!r:15s}  {'OK' if ok else 'FAIL expected=' + repr(expected)}")

# ---- end-to-end: real PDF ---
print()
pdf_path = r"E:\tmp\datasheet\VS11170GMH_GL195N10L\VS11170GMH.pdf"
print(f"=== end-to-end: {pdf_path} ===")

with pdfplumber.open(pdf_path) as pdf:
    raw_max = parse_max_ratings(pdf, "VS11170GMH")
    raw_elec = parse_electrical(pdf, "VS11170GMH")

# Before normalization
tstg_before = {r["symbol"] for r in raw_max if "TSTG" in r["symbol"].upper() or r["symbol"].upper().startswith("TJ")}
print(f"  max_ratings TSTG/TJ symbols BEFORE: {sorted(tstg_before)}")

# Apply normalization
parsed = {
    "tables": {
        "parts": [],
        "max_ratings": raw_max,
        "thermal_characteristics": [],
        "electrical_characteristics": raw_elec,
        "typical_charts": [],
    },
    "footnotes": {},
}
normed = normalize_parsed(parsed)

tstg_after = {r["symbol"] for r in normed["tables"]["max_ratings"]
              if "TSTG" in r["symbol"].upper() or r["symbol"].upper().startswith("TJ")}
print(f"  max_ratings TSTG/TJ symbols AFTER:  {sorted(tstg_after)}")
assert tstg_after == {"TSTG,TJ"}, f"Expected {{'TSTG,TJ'}}, got {tstg_after}"
print("  TSTG normalization OK")

elec_syms_before = {r["symbol"] for r in raw_elec}
elec_syms_after  = {r["symbol"] for r in normed["tables"]["electrical_characteristics"]}
changed = {(b, a) for b in elec_syms_before
           for a in [normalize_symbol(b)] if a != b}
if changed:
    print(f"  electrical symbol changes: {sorted(changed)}")
else:
    print("  electrical symbols: no changes (as expected for this PDF)")

print()
print("All normalize_symbol tests passed." if all_ok else "Some normalize_symbol tests FAILED.")

# ---- unit: normalize_channel ---
print()
print("=== normalize_channel unit tests ===")
channel_cases = [
    ("N-Channel Advanced Power MOSFET", ("Single", "N")),
    ("P-Channel Enhancement Mode",      ("Single", "P")),
    ("100V/120A N-Channel",             ("Single", "N")),
    ("Dual N-Channel MOSFET",           ("Dual",   "N")),
    ("Dual P-Channel MOSFET",           ("Dual",   "P")),
    ("Comp N-Channel",                  ("Comp",   "N")),
    ("Comp2 P-Channel",                 ("Comp2",  "P")),
    ("Asymmetric N-Channel",            ("Asymmetric", "N")),
    ("Complementary MOSFET N-Channel",  ("Comp",   "N")),
    ("N",                               ("Single", "N")),
    ("P",                               ("Single", "P")),
]
ch_ok = True
for raw, expected in channel_cases:
    got = normalize_channel(raw)
    ok  = got == expected
    ch_ok = ch_ok and ok
    print(f"  {raw!r:45s} -> {str(got):20s}  {'OK' if ok else 'FAIL expected=' + str(expected)}")

# ---- unit: normalize_package ---
print()
print("=== normalize_package unit tests ===")
for pkg in sorted(PACKAGE_WHITELIST):
    result = normalize_package(pkg)
    print(f"  {pkg!r:20s} -> OK")

try:
    normalize_package("INVALID-PKG")
    print("  FAIL: should have raised ValueError for INVALID-PKG")
    ch_ok = False
except ValueError as e:
    print(f"  INVALID-PKG correctly raised ValueError: {e}")

print()
if all_ok and ch_ok:
    print("All tests passed.")
else:
    print("Some tests FAILED.")
