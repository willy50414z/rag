# -*- coding: utf-8 -*-
"""Quick smoke test for db.validator — run with: python db/_test_validator.py"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from db.validator import validate_parsed, _PUA_RE

# --- regex sanity
assert _PUA_RE.search(chr(0xE000)), "PUA start not matched"
assert _PUA_RE.search(chr(0xF8FF)), "PUA end not matched"
assert not _PUA_RE.search("hello"), "false positive"
print("PUA regex OK\n")

BASE_PART = {"part_id": "VSP007N06MS-G", "package": "TO-252",
             "marking": "VS7", "source_page": 1, "table_ref": "T1"}
BASE_ELEC = {
    "part_id": "VSP007N06MS-G", "symbol": "RDS", "parameter": "On-Resistance",
    "section": "Static", "condition_raw": "VGS=10V",
    "condition_kv": '{"VGS": "10V"}', "condition_normalized": "VGS=10V",
    "min": None, "typ": 7.0, "max": 10.0, "value_raw": None,
    "unit": "mOhm", "footnote_ref": None, "source_page": 2, "table_ref": "P2-T0",
}

# ---- 測試 1：正常資料
p1 = {
    "tables": {
        "parts": [BASE_PART],
        "max_ratings": [{
            "part_id": "VSP007N06MS-G", "symbol": "VDSS",
            "parameter": "Drain-Source Voltage",
            "condition_raw": None, "condition_kv": None, "condition_normalized": "",
            "value_raw": "60", "value_num": 60.0, "value_min": None, "value_max_num": None,
            "unit": "V", "footnote_ref": None, "source_page": 1, "table_ref": "P1-T2",
        }],
        "thermal_characteristics": [{
            "part_id": "VSP007N06MS-G", "symbol": "Rth",
            "parameter": "Junction-to-Case", "typ": 1.5,
            "unit": "C/W", "source_page": 1, "table_ref": "P1-T3",
        }],
        "electrical_characteristics": [dict(BASE_ELEC)],
        "typical_charts": [],
    },
    "footnotes": {"1": "Pulse width limited by max junction temperature."},
}
r1 = validate_parsed(p1)
print("=== 正常資料 ===")
print(r1.summary())

# ---- 測試 2：symbol 含 PUA 字符
pua_char = chr(0xF001)
p2 = {
    "tables": {
        "parts": [BASE_PART],
        "max_ratings": [{
            "part_id": "VSP007N06MS-G",
            "symbol": "RDS" + pua_char + "ON",
            "parameter": "On-Resistance",
            "condition_raw": None, "condition_kv": None, "condition_normalized": "",
            "value_raw": "7", "value_num": 7.0, "value_min": None, "value_max_num": None,
            "unit": "mOhm", "footnote_ref": None, "source_page": 1, "table_ref": "P1-T2",
        }],
        "thermal_characteristics": [],
        "electrical_characteristics": [],
        "typical_charts": [],
    },
    "footnotes": {},
}
r2 = validate_parsed(p2)
print("\n=== symbol 含 PUA 字符 ===")
print(r2.summary())

# ---- 測試 3：condition_normalized 與 condition_kv 不一致
e3 = dict(BASE_ELEC)
e3["condition_kv"] = '{"Tj": "25C", "VGS": "10V"}'
e3["condition_normalized"] = "VGS=10V"   # 少了 Tj
p3 = {
    "tables": {
        "parts": [BASE_PART],
        "max_ratings": [],
        "thermal_characteristics": [],
        "electrical_characteristics": [e3],
        "typical_charts": [],
    },
    "footnotes": {},
}
r3 = validate_parsed(p3)
print("\n=== condition_normalized 與 condition_kv 不一致 ===")
print(r3.summary())

# ---- 測試 4：batch 內重複 key
e4a = dict(BASE_ELEC)
e4b = dict(BASE_ELEC)
e4b["parameter"] = "On-Resistance (dup)"
e4b["typ"] = 8.0
p4 = {
    "tables": {
        "parts": [BASE_PART],
        "max_ratings": [],
        "thermal_characteristics": [],
        "electrical_characteristics": [e4a, e4b],
        "typical_charts": [],
    },
    "footnotes": {},
}
r4 = validate_parsed(p4)
print("\n=== batch 內重複 key ===")
print(r4.summary())

# ---- 測試 5：unit 含換行
e5 = dict(BASE_ELEC)
e5["unit"] = "mOhm\n"
p5 = {
    "tables": {
        "parts": [BASE_PART],
        "max_ratings": [],
        "thermal_characteristics": [],
        "electrical_characteristics": [e5],
        "typical_charts": [],
    },
    "footnotes": {},
}
r5 = validate_parsed(p5)
print("\n=== unit 含換行（parser 未清除） ===")
print(r5.summary())
