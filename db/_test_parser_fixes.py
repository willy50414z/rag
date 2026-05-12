# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding="utf-8")
from datasheet_parser.vdsemi_parser import _norm_symbol, _parse_condition

PASS = "OK"
FAIL = "FAIL"

def check(label, got, expected):
    status = PASS if got == expected else f"{FAIL}  expected={expected!r}"
    print(f"  {label:35s} got={got!r}  {status}")

print("=== _norm_symbol ===")
check("TJ,TSTG -> (unchanged, TSTG done in parse_max_ratings)", _norm_symbol("TJ,TSTG"), "TJ,TSTG")
check("Td(off) -> td(off)", _norm_symbol("Td(off)"), "td(off)")
check("Td(on)  -> td(on)",  _norm_symbol("Td(on)"),  "td(on)")
check("Tf      -> tf",      _norm_symbol("Tf"),       "tf")
check("Tr      -> tr",      _norm_symbol("Tr"),       "tr")
check("VGS(TH) -> VGS(th)", _norm_symbol("VGS(TH)"), "VGS(th)")
check("RDS(on) unchanged",  _norm_symbol("RDS(on)"),  "RDS(on)")

print("\n=== _parse_condition: (Tj fix ===")
_, kv, norm = _parse_condition("(Tj=25°C)")
print(f"  '(Tj=25°C)'  kv={kv}  norm={norm!r}")
assert kv.get("Tj") == "25°C", f"Tj key wrong: {kv}"
assert "(Tj" not in kv, f"spurious (Tj key still present: {kv}"
print("  OK")

_, kv2, norm2 = _parse_condition("VGS=10V, (Tj=125°C)")
print(f"  'VGS=10V, (Tj=125°C)'  kv={kv2}  norm={norm2!r}")
assert kv2.get("Tj") == "125°C", f"Tj wrong: {kv2}"
assert kv2.get("VGS") == "10V",  f"VGS wrong: {kv2}"
print("  OK")

print("\n=== _parse_condition: single-char _raw filter ===")
_, kv3, norm3 = _parse_condition("VGS=10V, ID=40A, A")
print(f"  'VGS=10V, ID=40A, A'  kv={kv3}  norm={norm3!r}")
assert "_raw" not in kv3, f"_raw should be absent: {kv3}"
assert kv3.get("VGS") == "10V"
assert kv3.get("ID") == "40A"
print("  OK — 'A' artifact dropped")

print("\n=== Qg regex ===")
_QG_RE = re.compile(r"Q\s*g?\s*\(\s*(-?\d+(?:\.\d+)?)\s*V\s*g?\s*\)?$")
cases = [
    ("Qg(10V)",    "10V"),
    ("Qg(-10V)",   "-10V"),
    ("Qg(-4.5V)",  "-4.5V"),
    ("Q (-10Vg",   "-10V"),
    ("Q (-4.5Vg",  "-4.5V"),
    ("Qg",         None),    # no match expected
    ("Qgd",        None),    # no match
]
for sym, expected_vgs in cases:
    m = _QG_RE.match(sym)
    if expected_vgs:
        if m:
            vgs = m.group(1) + "V"
            status = PASS if vgs == expected_vgs else f"{FAIL} expected={expected_vgs!r}"
            print(f"  {sym!r:20s} -> Qg  VGS={vgs!r}  {status}")
        else:
            print(f"  {sym!r:20s} -> {FAIL}: no match (expected VGS={expected_vgs!r})")
    else:
        status = PASS if not m else f"{FAIL}: matched unexpectedly group={m.group(1)!r}"
        print(f"  {sym!r:20s} -> no match  {status}")
