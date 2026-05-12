# -*- coding: utf-8 -*-
import pytest
from parser import parse, find_table_by_header, parse_typical_charts
import pdfplumber, json
from pathlib import Path

PDF_PATH = str(Path(__file__).parent.parent.parent / "pdfs" / "VSP007N06MS-G.pdf")


@pytest.fixture(scope="module")
def result():
    return parse(PDF_PATH)


@pytest.fixture(scope="module")
def elec(result):
    return result["tables"]["electrical_characteristics"]


@pytest.fixture(scope="module")
def max_rat(result):
    return result["tables"]["max_ratings"]


@pytest.fixture(scope="module")
def thermal(result):
    return result["tables"]["thermal_characteristics"]


@pytest.fixture(scope="module")
def parts(result):
    return result["tables"]["parts"]


@pytest.fixture(scope="module")
def charts(result):
    return result["tables"]["typical_charts"]


@pytest.fixture(scope="module")
def charts_full():
    """Full records including image_bytes — for byte-level assertions."""
    return parse_typical_charts(PDF_PATH, "VSP007N06MS-G")


# --- Anchor resolution ---

def test_anchors_resolved(result):
    assert result["tables"]["parts"],                    "parts table empty"
    assert result["tables"]["max_ratings"],              "max_ratings table empty"
    assert result["tables"]["thermal_characteristics"], "thermal table empty"
    assert result["tables"]["electrical_characteristics"], "elec table empty"


def test_anchor_find_table_by_header():
    with pdfplumber.open(PDF_PATH) as pdf:
        pg, ti, tbl = find_table_by_header(
            pdf,
            ["Symbol", "Parameter", "Condition", "Min.", "Typ.", "Max.", "Unit"],
            search_pages=[2], col_count=8,
        )
    assert tbl is not None, "Electrical Characteristics table not found by anchor"
    assert pg == 2


# --- Row counts ---

def test_thermal_row_count(thermal):
    assert len(thermal) == 2, f"Expected 2 thermal rows, got {len(thermal)}"


def test_parts_row_count(parts):
    assert len(parts) == 1, f"Expected 1 parts row, got {len(parts)}"


def test_elec_row_count_range(elec):
    # 23 rows confirmed from VSP007N06MS-G; allow ±5 for family variation
    assert 20 <= len(elec) <= 30, f"Unexpected elec row count: {len(elec)}"


# --- Primary key uniqueness ---

def test_pk_unique_electrical(elec):
    keys = [(r["part_id"], r["symbol"], r["condition_normalized"]) for r in elec]
    assert len(keys) == len(set(keys)), "Duplicate primary keys in electrical_characteristics"


def test_pk_unique_max_ratings(max_rat):
    keys = [(r["part_id"], r["symbol"], r["condition_normalized"]) for r in max_rat]
    assert len(keys) == len(set(keys)), "Duplicate primary keys in max_ratings"


# --- Required fields ---

def test_required_fields_electrical(elec):
    for r in elec:
        assert r["part_id"],  f"Missing part_id: {r}"
        assert r["symbol"],   f"Missing symbol: {r}"
        assert r["unit"],     f"Missing unit: {r}"
        assert r["section"],  f"Missing section: {r}"
        assert r["source_page"] == 2
        assert r["table_ref"] == "P2-T0"


def test_required_fields_max_ratings(max_rat):
    for r in max_rat:
        assert r["part_id"],    f"Missing part_id: {r}"
        assert r["symbol"],     f"Missing symbol: {r}"
        assert r["value_raw"],  f"Missing value_raw: {r}"
        assert r["unit"],       f"Missing unit: {r}"
        assert r["source_page"] == 1


def test_required_fields_thermal(thermal):
    for r in thermal:
        assert r["symbol"]
        assert r["typ"] is not None
        assert r["source_page"] == 1


# --- Evidence trace ---

def test_evidence_trace(elec, max_rat, thermal):
    for r in elec:
        assert "source_page" in r and r["source_page"] is not None
        assert "table_ref" in r
    for r in max_rat + thermal:
        assert "source_page" in r


# --- Footnote detection ---

def test_footnotes_detected(result):
    fn = result["footnotes"]
    assert len(fn) >= 4, f"Expected ≥4 footnotes, got {len(fn)}: {list(fn.keys())}"


def test_footnote_ref_on_idm(max_rat):
    idm = [r for r in max_rat if r["symbol"] == "IDM"]
    assert idm, "IDM not found in max_ratings"
    assert idm[0]["footnote_ref"], "IDM missing footnote_ref"


# --- Sample value checks ---

def test_part_id(parts):
    assert parts[0]["part_id"] == "VSP007N06MS-G"
    assert parts[0]["package"] == "PDFN5x6"


def test_thermal_rtheta_jc(thermal):
    rjc = next((r for r in thermal if "JC" in r["symbol"]), None)
    assert rjc is not None, "RθJC not found"
    assert rjc["typ"] == pytest.approx(2.8)
    assert rjc["unit"] == "°C/W"


def test_vbrdss_in_max_ratings(max_rat):
    row = next((r for r in max_rat if "BR" in r["symbol"]), None)
    assert row is not None, "V(BR)DSS not found"
    assert row["value_num"] == pytest.approx(65.0)


def test_max_ratings_has_condition_kv(max_rat):
    rows_with_cond = [r for r in max_rat if r["condition_raw"]]
    assert rows_with_cond, "No max_ratings rows with condition"
    for r in rows_with_cond:
        assert r["condition_kv"] is not None, f"Missing condition_kv on {r['symbol']}"
        parsed = json.loads(r["condition_kv"])
        assert isinstance(parsed, dict)


def test_idsm_has_vgs_condition(max_rat):
    idsm = [r for r in max_rat if r["symbol"] == "IDSM"]
    assert idsm, "IDSM not found"
    for r in idsm:
        assert r["condition_kv"] is not None
        kv = json.loads(r["condition_kv"])
        assert "VGS" in kv, f"VGS missing from IDSM condition_kv: {kv}"
        assert kv["VGS"] == "10V"


def test_id_has_vgs_condition(max_rat):
    id_rows = [r for r in max_rat if r["symbol"] == "ID"]
    assert id_rows, "ID not found"
    for r in id_rows:
        assert r["condition_kv"] is not None
        kv = json.loads(r["condition_kv"])
        assert "VGS" in kv, f"VGS missing from ID condition_kv: {kv}"


def test_vgs_bipolar_in_max_ratings(max_rat):
    row = next((r for r in max_rat if r["symbol"] == "VGS"), None)
    assert row is not None, "VGS not found"
    assert "±" in (row["value_raw"] or ""), f"Expected ± in value_raw, got {row['value_raw']}"
    assert row["value_min"] == pytest.approx(-20.0)
    assert row["value_max_num"] == pytest.approx(20.0)


def test_temp_range_in_max_ratings(max_rat):
    row = next((r for r in max_rat if "STG" in r["symbol"] or "55" in (r["value_raw"] or "")), None)
    assert row is not None, "Storage temp range row not found"
    assert row["value_min"] == pytest.approx(-55.0)
    assert row["value_max_num"] == pytest.approx(150.0)


def test_rds_on_three_rows(elec):
    rds = [r for r in elec if r["symbol"] == "RDS(ON)"]
    assert len(rds) == 3, f"Expected 3 RDS(ON) rows, got {len(rds)}: {[r['condition_normalized'] for r in rds]}"


def test_rds_on_25c(elec):
    row = next((r for r in elec
                if r["symbol"] == "RDS(ON)" and "VGS=10V" in (r["condition_normalized"] or "")
                and "Tj=100" not in (r["condition_normalized"] or "")), None)
    assert row is not None, "RDS(ON) @ VGS=10V, Tj=25°C not found"
    assert row["typ"] == pytest.approx(4.5)
    assert row["max"] == pytest.approx(6.0)


def test_rds_on_100c(elec):
    row = next((r for r in elec
                if r["symbol"] == "RDS(ON)" and "Tj=100" in (r["condition_normalized"] or "")), None)
    assert row is not None, "RDS(ON) @ Tj=100°C not found"
    assert row["typ"] == pytest.approx(5.5)


def test_rds_on_4v5(elec):
    row = next((r for r in elec
                if r["symbol"] == "RDS(ON)" and "VGS=4.5V" in (r["condition_normalized"] or "")), None)
    assert row is not None, "RDS(ON) @ VGS=4.5V not found"
    assert row["typ"] == pytest.approx(7.0)
    assert row["max"] == pytest.approx(10.0)


def test_qg_symbol_normalized(elec):
    qg_rows = [r for r in elec if r["symbol"] == "Qg"]
    assert len(qg_rows) == 2, f"Expected 2 Qg rows, got {len(qg_rows)}"
    vgs_values = {r["condition_kv"] and json.loads(r["condition_kv"]).get("VGS") for r in qg_rows}
    assert "10V" in vgs_values, "Qg VGS=10V row missing"
    assert "4.5V" in vgs_values, "Qg VGS=4.5V row missing"


def test_qg_45v_condition(elec):
    row = next((r for r in elec
                if r["symbol"] == "Qg" and "VGS=4.5V" in (r["condition_normalized"] or "")), None)
    assert row is not None, "Qg @ VGS=4.5V not found"
    assert row["typ"] == pytest.approx(14.0)


def test_sections_all_present(elec):
    sections = {r["section"] for r in elec}
    assert "Static" in sections
    assert "Dynamic" in sections
    assert "Switching" in sections
    assert "DiodeCharacteristics" in sections


def test_igss_value_raw(elec):
    row = next((r for r in elec if r["symbol"] == "IGSS"), None)
    assert row is not None, "IGSS not found"
    assert row["value_raw"] and "±" in row["value_raw"], \
        f"Expected ± in IGSS value_raw, got {row['value_raw']}"
    assert row["max"] is None, "IGSS max should be NULL (non-numeric)"


def test_condition_kv_parseable(elec):
    for r in elec:
        if r["condition_kv"]:
            parsed = json.loads(r["condition_kv"])
            assert isinstance(parsed, dict)


# --- Typical Characteristics charts ---

def test_typical_charts_count(charts):
    # VSP007N06MS-G has Fig1-Fig11 across pages 3-4
    assert 10 <= len(charts) <= 14, f"Expected 10-14 charts, got {len(charts)}"


def test_typical_charts_required_fields(charts):
    for r in charts:
        assert r["part_id"] == "VSP007N06MS-G"
        assert r["caption"],                f"Empty caption: {r}"
        assert r["source_page"] in (3, 4),  f"Unexpected source_page: {r}"
        assert r["minio_key"],              f"Empty minio_key: {r}"
        assert r["table_ref"] == "P3-P4-charts"


def test_typical_charts_no_fig_prefix_in_caption(charts):
    import re
    fig_re = re.compile(r"^Fig\.?\s*\d+", re.IGNORECASE)
    for r in charts:
        assert not fig_re.match(r["caption"]), \
            f"FigXX. prefix not stripped: {repr(r['caption'])}"


def test_typical_charts_minio_key_format(charts):
    for r in charts:
        assert r["minio_key"].startswith("VSP007N06MS-G/fig"), \
            f"Unexpected minio_key: {r['minio_key']}"
        assert r["minio_key"].endswith(".png")


def test_typical_charts_image_bytes_nonempty(charts_full):
    for r in charts_full:
        assert r["image_bytes"], f"Empty image_bytes for {r['minio_key']}"
        assert r["image_bytes"][:4] == b"\x89PNG", \
            f"Not a PNG: {r['minio_key']}"


def test_typical_charts_no_image_bytes_in_parse_output(charts):
    for r in charts:
        assert "image_bytes" not in r, "image_bytes leaked into parse() output"


def test_typical_charts_known_caption(charts):
    captions = [r["caption"] for r in charts]
    assert any("Output Characteristics" in c for c in captions), \
        f"'Output Characteristics' not found in captions: {captions}"
    assert any("Gate Charge" in c for c in captions), \
        f"'Gate Charge' not found in captions: {captions}"
