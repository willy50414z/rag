# -*- coding: utf-8 -*-
"""
Parser for VSP007N06MS-G
Generated from: pdf_field_spec.md
"""
import json
import re
import warnings
from pathlib import Path

import pdfplumber

try:
    import fitz as _fitz  # PyMuPDF — only used for typical_charts
    _FITZ_AVAILABLE = True
except ImportError:
    _fitz = None
    _FITZ_AVAILABLE = False

PDF_PATH = str(Path(__file__).parent.parent.parent / "pdfs" / "VSP007N06MS-G.pdf")

# PUA → printable mapping
_PUA_MAP = {
    "": "θ",
    "": "④",
}

# Circled digit pattern (U+2460–U+2468)
_FOOTNOTE_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨]")

# Section header keywords → section value
_SECTION_MAP = [
    ("Source-Drain", "DiodeCharacteristics"),
    ("Switching",    "Switching"),
    ("Dynamic",      "Dynamic"),
    ("Static",       "Static"),
]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_pua(s: str) -> str:
    for k, v in _PUA_MAP.items():
        s = s.replace(k, v)
    return s


def _norm_cell(cell) -> str:
    """Flatten a pdfplumber cell to a clean string."""
    if cell is None:
        return ""
    s = _apply_pua(str(cell))
    s = s.replace("", "④")   # belt-and-suspenders
    s = s.replace("℃", "°C")
    s = s.replace("Ω", "Ω")
    return s.strip()


def _norm_symbol(raw: str) -> str:
    """Flatten subscript newlines and PUA. Canonical mapping is applied by normalizer.py."""
    s = _apply_pua(raw)
    s = s.replace("\n", "")
    return s.strip()


def _extract_footnote(text: str):
    """Return (clean_text, footnote_ref_or_None)."""
    refs = _FOOTNOTE_RE.findall(text)
    clean = _FOOTNOTE_RE.sub("", text).strip()
    return clean, ("".join(refs) if refs else None)


def _parse_num(s: str):
    """Try to parse s as float; return None on failure."""
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_elec_value(s: str):
    """Return (min, typ, max, value_raw) for an electrical_characteristics cell."""
    s = s.strip()
    if s in ("--", "", "-"):
        return None, None
    if s.startswith("±"):
        return None, s   # non-standard; caller stores in value_raw
    v = _parse_num(s)
    return v, None


def _parse_rating_value(s: str):
    """Return (value_raw, value_num, value_min, value_max_num) for max_ratings."""
    s = s.strip()
    if not s or s == "--":
        return "--", None, None, None
    if s.startswith("±"):
        try:
            mag = float(re.sub(r"[^\d.]", "", s))
            return s, None, -mag, mag
        except ValueError:
            return s, None, None, None
    m = re.match(r"^(-?\d+\.?\d*)\s*to\s*(-?\d+\.?\d*)$", s)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return s, None, lo, hi
    v = _parse_num(s)
    if v is not None:
        return s, v, None, None
    return s, None, None, None


def _norm_condition_token(token: str) -> str:
    """Normalise a single condition token: fix ℃, subscript j, spaces."""
    token = token.replace("℃", "°C").replace("℃", "°C")
    token = re.sub(r"T\s*=\s*(\d+)", r"Tj=\1", token)   # T=100°C → Tj=100°C
    token = re.sub(r"\s*\nj\s*", "", token)               # strip trailing '\nj'
    return token.strip()


def _parse_condition(raw: str | None):
    """
    Parse a condition string into:
      condition_raw (str|None), condition_kv (dict|None), condition_normalized (str)
    """
    if not raw or not raw.strip():
        return None, None, ""

    # Flatten subscript-j artefact from pdfplumber
    raw = re.sub(r"\nj\b", "", raw)
    raw = raw.replace("℃", "°C").replace("℃", "°C")
    raw = re.sub(r"\bT\s*=\s*(\d+\s*°C)", r"Tj=\1", raw)

    # Strip outer parentheses if the entire condition is wrapped: "(Tj=25°C)" → "Tj=25°C"
    stripped = raw.strip()
    if stripped.startswith("(") and stripped.endswith(")"):
        inner = stripped[1:-1]
        if inner.count("(") == inner.count(")"):
            raw = inner

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    kv: dict[str, str] = {}
    raw_parts: list[str] = []
    for tok in tokens:
        if "=" in tok:
            k, _, v = tok.partition("=")
            # Strip leading "(" from key and matching trailing ")" from value
            # e.g. "(Tj=25°C)" → k="Tj", v="25°C"
            had_open = k.strip().startswith("(")
            k = k.strip().lstrip("(")
            v = v.strip().rstrip(")") if had_open else v.strip()
            if k:
                kv[k] = v
        elif len(tok) > 1:
            # Skip single-character tokens (pdfplumber subscript artifacts like "A", "j")
            raw_parts.append(tok)
    if raw_parts:
        kv["_raw"] = "; ".join(raw_parts)

    condition_raw_clean = ", ".join(
        f"{k}={v}" for k, v in kv.items() if k != "_raw"
    )
    if "_raw" in kv:
        condition_raw_clean += (", " if condition_raw_clean else "") + kv["_raw"]

    normalized = ",".join(f"{k}={v}" for k, v in sorted(kv.items()) if k != "_raw")
    return condition_raw_clean or raw.strip(), kv, normalized


def _override_vgs(kv: dict, new_vgs: str) -> dict:
    updated = dict(kv)
    updated["VGS"] = new_vgs
    return updated


def _kv_to_normalized(kv: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(kv.items()) if k != "_raw")


def _kv_to_raw(kv: dict) -> str:
    parts = [f"{k}={v}" for k, v in kv.items() if k != "_raw"]
    if "_raw" in kv:
        parts.append(kv["_raw"])
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Table finder
# ---------------------------------------------------------------------------

def find_table_by_header(pdf, expected_headers, search_pages=None, col_count=None):
    """
    Return (page_number, table_index, table_rows) for the first table whose
    header row contains all expected_headers (substring, case-insensitive).

    Uses find_tables() + table.extract(x_tolerance=1) so that cell text has
    proper inter-word spacing even when the PDF encodes words without space
    characters (same approach as VergigaDatasheetExtractor.extract_tables_from_page).
    """
    pages = pdf.pages if search_pages is None else [pdf.pages[i - 1] for i in search_pages]
    for page in pages:
        for ti, tbl_obj in enumerate(page.find_tables() or []):
            table = tbl_obj.extract(x_tolerance=1)
            if not table:
                continue
            if col_count and len(table[0]) != col_count:
                continue
            header_cells = [_norm_cell(c) for c in table[0]]
            header_joined = " ".join(header_cells)
            # Compare without spaces so kerning-split tokens like "Part ID" match "PartID"
            header_nospace = header_joined.replace(" ", "").lower()
            if all(h.replace(" ", "").lower() in header_nospace for h in expected_headers):
                return page.page_number, ti, table
    return None, None, None


# ---------------------------------------------------------------------------
# Footnote extraction
# ---------------------------------------------------------------------------

_CIRCLE_NUMS = "①②③④⑤⑥⑦⑧⑨"


def extract_footnotes_dynamic(pdf) -> dict[str, str]:
    """
    Scan all pages for footnote lines (circled-digit markers).
    Handles "NOTE: ① text" and standalone "② text" formats, including
    multi-line footnotes that wrap to the next line.

    Uses extract_words(x_tolerance=1) so word boundaries are correctly
    detected even when the PDF encodes words without space characters
    (same approach as VergigaDatasheetExtractor._extract_notes).
    """
    result: dict[str, str] = {}

    for page in pdf.pages:
        words = page.extract_words(x_tolerance=1)
        if not words:
            continue

        # Group words into text lines (3 pt y-tolerance, same as _extract_notes)
        line_map: dict[float, list] = {}
        for w in words:
            top = w["top"]
            placed = False
            for existing_top in line_map:
                if abs(existing_top - top) < 3:
                    line_map[existing_top].append(w)
                    placed = True
                    break
            if not placed:
                line_map[top] = [w]

        found_note_section = False
        current_marker: str | None = None
        current_text = ""

        for top in sorted(line_map):
            line_map[top].sort(key=lambda w: w["x0"])
            line = " ".join(
                _apply_pua(w["text"]).replace("℃", "°C") for w in line_map[top]
            ).strip()

            if not line:
                continue

            # Detect start of NOTE section
            if "NOTE:" in line or "Notes:" in line:
                found_note_section = True
                after_colon = line.split(":", 1)[1].strip() if ":" in line else ""
                if after_colon and after_colon[0] in _CIRCLE_NUMS:
                    # "NOTE: ① text..." — marker on same line as NOTE:
                    marker = after_colon[0]
                    text = after_colon[1:].strip()
                    if current_marker and current_text:
                        result[current_marker] = current_text
                    current_marker = marker
                    current_text = text
                continue

            if not found_note_section:
                continue

            first_char = line[0] if line else ""
            if first_char in _CIRCLE_NUMS:
                # Save previous and start new footnote
                if current_marker and current_text:
                    result[current_marker] = current_text
                current_marker = first_char
                current_text = line[1:].strip()
            elif current_marker:
                # Continuation line of current footnote
                current_text += " " + line

        if current_marker and current_text:
            result[current_marker] = current_text

    return result


# ---------------------------------------------------------------------------
# Part ID extraction
# ---------------------------------------------------------------------------

def _extract_part_id(pdf) -> str | None:
    """Extract part ID from the first page title text (e.g. VSP007N06MS-G)."""
    page = pdf.pages[0]
    text = page.extract_text() or ""
    m = re.search(r"\b(VS\w+(?:-G)?)\b", text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Table parsers
# ---------------------------------------------------------------------------

def parse_parts(pdf, part_id: str) -> list[dict]:
    pg, ti, table = find_table_by_header(
        pdf, ["PartID", "PackageType", "Marking", "Packing"], search_pages=[1]
    )
    records = []
    if table is None:
        # Fallback: extract from page text
        warnings.warn("P1-T1 anchor not found; trying page-text fallback")
        page = pdf.pages[0]
        text = page.extract_text() or ""
        m = re.search(
            r"(VS\S+)\s+(\S+)\s+(\S+)\s+(\d+\S*/Reel)",
            text.replace("\n", " ")
        )
        if m:
            records.append({
                "part_id": m.group(1), "package": m.group(2),
                "marking": m.group(3), "packing": m.group(4),
                "source_page": 1, "table_ref": "P1-T1",
            })
        return records

    for row in table[1:]:
        cells = [_norm_cell(c) for c in row]
        if not any(cells):
            continue
        records.append({
            "part_id":    cells[0] or part_id,
            "package":    cells[1] if len(cells) > 1 else None,
            "marking":    cells[2] if len(cells) > 2 else None,
            "packing":    cells[3] if len(cells) > 3 else None,
            "source_page": pg,
            "table_ref":  "P1-T1",
        })
    return records


def parse_max_ratings(pdf, part_id: str) -> list[dict]:
    pg, ti, table = find_table_by_header(
        pdf, ["Symbol", "Parameter", "Rating", "Unit"], search_pages=[1]
    )
    if table is None:
        raise ValueError("P1-T2 (max_ratings) anchor not found")

    records = []
    prev_symbol = None
    prev_parameter = None
    prev_param_vgs_cond = None   # forward-fill @VGS extracted from parameter

    for row in table[1:]:
        cells = [_norm_cell(c) for c in row]
        if not any(cells):
            continue

        # Detect rows: [Symbol, Parameter, Condition, Rating, Unit]
        # pdfplumber gives 5 cols for this table
        sym_raw  = cells[0] if len(cells) > 0 else ""
        param_raw= cells[1] if len(cells) > 1 else ""
        cond_raw = cells[2] if len(cells) > 2 else ""

        # Some datasheets embed a "Thermal Characteristics" section inside this
        # table. Stop here so those rows are handled by parse_thermal instead.
        if sym_raw and re.search(r"thermal\s+char", sym_raw, re.IGNORECASE):
            break
        val_raw  = cells[3] if len(cells) > 3 else ""
        unit_raw = cells[4] if len(cells) > 4 else ""

        # Forward-fill symbol
        if sym_raw:
            sym_norm = _norm_symbol(sym_raw)
            prev_symbol = sym_norm
        else:
            sym_norm = prev_symbol

        param_with_pua = _apply_pua(param_raw)
        param_clean, footnote_ref = _extract_footnote(param_with_pua)

        # Extract @VGS=xxx condition embedded in parameter text
        # e.g. "Continuousdraincurrent@VGS=10V" → param="Continuousdraincurrent", vgs_cond="VGS=10V"
        _at_vgs = re.search(r"@(VGS\s*=\s*\S+)", param_clean)
        if _at_vgs:
            param_vgs_cond = _at_vgs.group(1).replace(" ", "")
            param_clean = re.sub(r"\s*@VGS\s*=\s*\S+", "", param_clean).strip()
            if sym_raw:                          # new symbol: update tracked value
                prev_param_vgs_cond = param_vgs_cond
        elif sym_raw:
            param_vgs_cond = None                # new symbol with no @VGS: reset
            prev_param_vgs_cond = None
        else:
            param_vgs_cond = prev_param_vgs_cond # continuation row: inherit

        # Extract "(xxx limited)" qualifier: differentiates rows like
        # "Silicon limited" vs "Wire bond limited" for the same symbol+condition.
        # Stored as limit=<value> in condition so it becomes part of condition_normalized.
        _limit_m = re.search(r"\(\s*([^)]+\s+[Ll]imited)\s*\)", param_clean)
        if _limit_m:
            param_limit_cond = f"limit={_limit_m.group(1).strip()}"
            param_clean = (param_clean[:_limit_m.start()].rstrip()
                           + param_clean[_limit_m.end():]).strip()
        else:
            param_limit_cond = None

        if param_clean:
            prev_parameter = param_clean
        else:
            param_clean = prev_parameter

        if not sym_norm:
            continue

        # Condition normalisation
        # Normalise subscript temperature before stripping \n:
        # "T =25°C\nC" → "TC=25°C", "T =70°C\nA" → "TA=70°C", "T =25°C\nj" → "Tj=25°C"
        cond_clean = re.sub(
            r"T\s*=\s*(\d+(?:\.\d+)?)\s*°C\s*\n([CAj])",
            r"T\2=\1°C",
            cond_raw,
        ) if cond_raw else None
        if cond_clean:
            cond_clean = cond_clean.replace("\n", " ").strip()

        # Merge @VGS and limit conditions from parameter text into condition string
        if param_vgs_cond:
            cond_clean = f"{cond_clean}, {param_vgs_cond}" if cond_clean else param_vgs_cond
        if param_limit_cond:
            cond_clean = f"{cond_clean}, {param_limit_cond}" if cond_clean else param_limit_cond

        # Build condition_kv (same pattern as electrical_characteristics)
        cond_raw_str, cond_kv, cond_norm = _parse_condition(cond_clean)
        if cond_kv is not None:
            cond_kv_str  = json.dumps(
                {k: v for k, v in sorted(cond_kv.items())}, ensure_ascii=False
            )
            cond_norm_str = _kv_to_normalized(cond_kv)
        else:
            cond_kv_str  = None
            cond_norm_str = ""

        # Value parsing
        v_raw, v_num, v_min, v_max = _parse_rating_value(val_raw)

        unit = unit_raw.replace("\n", "").strip()

        records.append({
            "part_id":              part_id,
            "symbol":               sym_norm,
            "parameter":            param_clean,
            "condition_raw":        cond_raw_str if cond_raw_str else None,
            "condition_kv":         cond_kv_str,
            "condition_normalized": cond_norm_str,
            "value_raw":            v_raw,
            "value_num":            v_num,
            "value_min":            v_min,
            "value_max_num":        v_max,
            "unit":                 unit,
            "footnote_ref":         footnote_ref,
            "source_page":          pg,
            "table_ref":            "P1-T2",
        })
    return records


def _parse_thermal_from_combined(pdf, part_id: str) -> list[dict]:
    """Fallback: extract thermal rows embedded inside the max_ratings table.

    Some datasheets (e.g. VS6522AD) use a single combined table with a
    'Thermal Characteristics' section-header row instead of a dedicated table.
    Columns are [Symbol, Parameter, Condition, Rating, Unit]; Rating is treated
    as the typical value.
    """
    pg, _, table = find_table_by_header(
        pdf, ["Symbol", "Parameter", "Rating", "Unit"], search_pages=[1]
    )
    if table is None:
        return []
    records = []
    in_thermal = False
    for row in table[1:]:
        cells = [_norm_cell(c) for c in row]
        if not any(cells):
            continue
        sym_raw = cells[0] if len(cells) > 0 else ""
        if sym_raw and re.search(r"thermal\s+char", sym_raw, re.IGNORECASE):
            in_thermal = True
            continue
        if not in_thermal:
            continue
        param   = cells[1] if len(cells) > 1 else ""
        val_raw = cells[3] if len(cells) > 3 else ""   # Rating → Typical
        unit    = cells[4] if len(cells) > 4 else ""
        sym = _norm_symbol(sym_raw)
        if not sym:
            continue
        records.append({
            "part_id":    part_id,
            "symbol":     sym,
            "parameter":  param,
            "typ":        _parse_num(val_raw),
            "unit":       unit.replace("\n", "").strip(),
            "source_page": pg,
            "table_ref":  "P1-T2-thermal",
        })
    return records


def parse_thermal(pdf, part_id: str) -> list[dict]:
    pg, ti, table = find_table_by_header(
        pdf, ["Symbol", "Parameter", "Typical", "Unit"], search_pages=[1]
    )
    if table is None:
        return _parse_thermal_from_combined(pdf, part_id)

    records = []
    for row in table[1:]:
        cells = [_norm_cell(c) for c in row]
        if not any(cells):
            continue
        sym_raw  = cells[0] if len(cells) > 0 else ""
        param    = cells[1] if len(cells) > 1 else ""
        typ_raw  = cells[2] if len(cells) > 2 else ""
        unit     = cells[3] if len(cells) > 3 else ""

        sym = _norm_symbol(sym_raw)
        if not sym:
            continue

        typ_val = _parse_num(typ_raw)
        records.append({
            "part_id":    part_id,
            "symbol":     sym,
            "parameter":  param,
            "typ":        typ_val,
            "unit":       unit.replace("\n", "").strip(),
            "source_page": pg,
            "table_ref":  "P1-T3",
        })
    return records


def parse_electrical(pdf, part_id: str) -> list[dict]:
    pg, ti, table = find_table_by_header(
        pdf,
        ["Symbol", "Parameter", "Condition", "Min.", "Typ.", "Max", "Unit"],
        search_pages=[2],
    )
    if table is None:
        raise ValueError("P2-T0 (electrical_characteristics) anchor not found")

    # Detect column layout: 8-col has a split Condition (primary + secondary);
    # 7-col has a single Condition column.
    _split_cond = len(table[0]) >= 8

    records = []
    current_section = "Static"

    # Forward-fill state
    prev_sym   = None
    prev_param = None
    prev_cond_kv: dict | None = None   # kv dict of the last explicit condition

    # Qg VGS tracking: when we see Qg(10V), store the base condition kv
    # so Qg(4.5V) can override VGS
    qg_base_kv: dict | None = None

    for row in table[1:]:
        cells = [_norm_cell(c) for c in row]

        sym_raw   = cells[0] if len(cells) > 0 else ""
        param_raw = cells[1] if len(cells) > 1 else ""

        if _split_cond:
            # col layout: [Symbol, Parameter, Cond_primary, Cond_secondary, Min, Typ, Max, Unit]
            cond_pri  = cells[2] if len(cells) > 2 else ""
            cond_sec  = cells[3] if len(cells) > 3 else ""
            min_raw   = cells[4] if len(cells) > 4 else ""
            typ_raw   = cells[5] if len(cells) > 5 else ""
            max_raw   = cells[6] if len(cells) > 6 else ""
            unit_raw  = cells[7] if len(cells) > 7 else ""
        else:
            # col layout: [Symbol, Parameter, Condition, Min, Typ, Max, Unit]
            cond_pri  = cells[2] if len(cells) > 2 else ""
            cond_sec  = ""
            min_raw   = cells[3] if len(cells) > 3 else ""
            typ_raw   = cells[4] if len(cells) > 4 else ""
            max_raw   = cells[5] if len(cells) > 5 else ""
            unit_raw  = cells[6] if len(cells) > 6 else ""

        # --- Section header detection ---
        if sym_raw and not param_raw and not min_raw and not typ_raw and not max_raw:
            sym_compact = sym_raw.replace("- ", "-").replace(" -", "-")
            for key, sec_val in _SECTION_MAP:
                if key in sym_compact:
                    current_section = sec_val
                    break
            continue

        # --- Symbol normalisation ---
        if sym_raw:
            sym_norm_raw = _norm_symbol(sym_raw)

            # Qg(xV) special case — handles positive, negative, and malformed variants:
            # "Qg(10V)", "Qg(-10V)", "Qg(-4.5V)", "Q (-10Vg", "Q (-4.5Vg"
            # The subscript g sometimes appears after the voltage in malformed cells.
            qg_match = re.match(
                r"Q\s*g?\s*\(\s*(-?\d+(?:\.\d+)?)\s*V\s*g?\s*\)?$",
                sym_norm_raw,
            )
            if qg_match:
                extracted_vgs = qg_match.group(1) + "V"
                sym_norm = "Qg"
            else:
                extracted_vgs = None
                sym_norm = sym_norm_raw

            prev_sym = sym_norm
        else:
            sym_norm = prev_sym
            extracted_vgs = None
            qg_match = None

        # --- Parameter + footnote ---
        # Extract temperature embedded in parameter text (e.g. IDSS "ZeroGateDrainCurrent(T=125℃)")
        # This temperature is a condition differentiator, not part of the parameter name.
        _param_temp_m = re.search(r"\(\s*T[j]?\s*=\s*(\d+)\s*[℃°](?:C)?\)", param_raw)
        param_extracted_temp = f"Tj={_param_temp_m.group(1)}°C" if _param_temp_m else None

        param_with_pua = _apply_pua(param_raw)
        param_clean, footnote_ref = _extract_footnote(param_with_pua)
        # Remove temperature qualifier and trailing subscript artefacts from display text
        if param_extracted_temp:
            param_clean = re.sub(r"\s*\(\s*T[j]?\s*=\s*\d+\s*[℃°](?:C)?\)", "", param_clean).strip()
        param_clean = re.sub(r"\n[a-z]\s*$", "", param_clean).strip()

        if param_clean:
            prev_param = param_clean
        else:
            param_clean = prev_param

        # --- Condition assembly ---
        # cond_pri may contain '\n'-separated lines from pdfplumber merged-cell artefacts.
        # Rule: stop collecting when we hit a line that is a standalone temperature override
        # (matches T=xxx or Tj=xxx with no comma → it belongs to the continuation row).
        # Line-wrapped parameters (e.g. "VGS=10V" on line 2) are kept.
        if cond_pri and "\n" in cond_pri:
            lines = [l.strip() for l in cond_pri.split("\n")]
            main_parts: list[str] = []
            for line in lines:
                if not line:
                    continue
                if re.match(r"^[a-z]$", line):   # single subscript letter artefact (j, c…)
                    continue
                # Pure temperature override with no other tokens → stop (belongs to next row)
                if re.match(r"^T[j]?\s*=\s*\d+", line) and "," not in line:
                    break
                main_parts.append(line.rstrip(","))
            cond_pri = ",".join(main_parts) if main_parts else cond_pri.split("\n")[0]

        # cond_sec: secondary temperature override (e.g. "T=100°C\nj")
        if cond_sec:
            cond_sec_clean = re.sub(r"\nj\b", "", cond_sec)
            cond_sec_clean = cond_sec_clean.replace("℃", "°C").strip()
            cond_sec_clean = re.sub(r"\bT\s*=\s*(\d+)", r"Tj=\1", cond_sec_clean)
        else:
            cond_sec_clean = None

        if cond_pri:
            # New explicit primary condition
            _, kv, _ = _parse_condition(cond_pri)
            if kv is None:
                kv = {}
            if cond_sec_clean and "=" in cond_sec_clean:
                k2, _, v2 = cond_sec_clean.partition("=")
                kv[k2.strip()] = v2.strip()
            if param_extracted_temp:
                k2, _, v2 = param_extracted_temp.partition("=")
                kv[k2.strip()] = v2.strip()
            prev_cond_kv = kv
            # Track Qg base condition for Qg(4.5V) override
            if sym_norm == "Qg":
                qg_base_kv = dict(kv)
        else:
            # Inherit previous condition
            kv = dict(prev_cond_kv) if prev_cond_kv else {}
            if cond_sec_clean and "=" in cond_sec_clean:
                k2, _, v2 = cond_sec_clean.partition("=")
                kv[k2.strip()] = v2.strip()
            if param_extracted_temp:
                k2, _, v2 = param_extracted_temp.partition("=")
                kv[k2.strip()] = v2.strip()

        # Qg(4.5V): override VGS in inherited condition
        if extracted_vgs and sym_norm == "Qg" and not cond_pri:
            if qg_base_kv:
                kv = dict(qg_base_kv)
            kv["VGS"] = extracted_vgs

        condition_raw_str = _kv_to_raw(kv) if kv else None
        condition_kv_str  = json.dumps(
            {k: v for k, v in sorted(kv.items())}, ensure_ascii=False
        ) if kv else None
        condition_norm    = _kv_to_normalized(kv) if kv else ""

        # --- Min / Typ / Max ---
        min_v, min_raw_flag = _parse_elec_value(min_raw)
        typ_v, typ_raw_flag = _parse_elec_value(typ_raw)
        max_v, max_raw_flag = _parse_elec_value(max_raw)

        value_raw = max_raw_flag or typ_raw_flag or min_raw_flag

        unit = unit_raw.replace("\n", "").strip()

        if not sym_norm or not unit:
            continue

        records.append({
            "part_id":              part_id,
            "symbol":               sym_norm,
            "parameter":            param_clean,
            "section":              current_section,
            "condition_raw":        condition_raw_str,
            "condition_kv":         condition_kv_str,
            "condition_normalized": condition_norm,
            "min":                  min_v,
            "typ":                  typ_v,
            "max":                  max_v,
            "value_raw":            value_raw,
            "unit":                 unit,
            "footnote_ref":         footnote_ref,
            "source_page":          pg,
            "table_ref":            "P2-T0",
        })

    return records


# ---------------------------------------------------------------------------
# Typical Characteristics chart extraction (PyMuPDF)
# ---------------------------------------------------------------------------

_FIG_PREFIX_RE = re.compile(r"^Fig\.?\s*\d+\.?\s*", re.IGNORECASE)
_FIG_NUM_RE    = re.compile(r"^Fig\.?\s*(\d+)", re.IGNORECASE)


def _slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:80]


def parse_typical_charts(
    pdf_path: str,
    part_id: str,
    pages: list | None = None,
) -> list[dict]:
    """
    Extract typical-characteristic chart images from the given pages using PyMuPDF.

    pages: 1-based page numbers (default [3, 4]).

    Each record contains:
      part_id, caption, source_page, minio_key, image_bytes (PNG), table_ref.
    image_bytes is NOT included in parse() output (excluded from output.json).
    Callers that need bytes for MinIO upload should call this function directly.
    """
    if not _FITZ_AVAILABLE:
        warnings.warn("PyMuPDF (fitz) not installed; skipping typical_charts extraction")
        return []

    if pages is None:
        pages = [3, 4]

    doc = _fitz.open(pdf_path)
    records: list[dict] = []

    for page_num in pages:
        page_idx = page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            continue

        page      = doc[page_idx]
        pw        = page.rect.width
        ph        = page.rect.height
        tblocks   = page.get_text("blocks")
        words     = page.get_text("words")

        # -- Locate bottom of "Typical Characteristics" section heading
        title_bottom = 0.0
        for b in tblocks:
            if "Typical Characteristics" in b[4].strip() and b[1] < ph * 0.3:
                title_bottom = max(title_bottom, float(b[3]))
        if title_bottom == 0.0:
            title_bottom = 50.0

        # -- Collect captions (blocks whose lines start with "fig")
        captions: list[dict] = []
        for b in tblocks:
            fig_lines = [
                ln.strip()
                for ln in b[4].strip().split("\n")
                if ln.strip().lower().startswith("fig")
            ]
            if not fig_lines:
                continue

            if len(fig_lines) == 1:
                captions.append({
                    "text": fig_lines[0],
                    "center_x": (b[0] + b[2]) / 2,
                    "center_y": (b[1] + b[3]) / 2,
                    "y0": float(b[1]),
                    "y1": float(b[3]),
                })
            else:
                # Multiple captions in one block — locate each via word positions
                for fline in fig_lines:
                    marker = fline.split()[0]
                    found = next(
                        (w for w in words if w[5] == b[5] and marker in w[4]), None
                    )
                    if found:
                        captions.append({
                            "text": fline,
                            "center_x": (found[0] + found[2]) / 2,
                            "center_y": (found[1] + found[3]) / 2,
                            "y0": float(found[1]),
                            "y1": float(b[3]),
                        })
                    else:
                        captions.append({
                            "text": fline,
                            "center_x": (b[0] + b[2]) / 2,
                            "center_y": (b[1] + b[3]) / 2,
                            "y0": float(b[1]),
                            "y1": float(b[3]),
                        })

        # -- Cluster captions into visual rows (50 pt y-threshold)
        captions.sort(key=lambda c: c["center_y"])
        rows: list[list[dict]] = []
        if captions:
            cur_row = [captions[0]]
            for cap in captions[1:]:
                if abs(cap["center_y"] - cur_row[-1]["center_y"]) < 50:
                    cur_row.append(cap)
                else:
                    rows.append(cur_row)
                    cur_row = [cap]
            rows.append(cur_row)

        # -- Render image region above each caption
        current_top = title_bottom
        for row in rows:
            row.sort(key=lambda c: c["center_x"])
            row_bottom = max(c["y1"] for c in row)

            for i, cap in enumerate(row):
                col_w   = pw / len(row)
                x0, x1  = i * col_w, (i + 1) * col_w
                y1      = cap["y0"] if cap["y0"] > current_top else cap["y0"]
                clip    = _fitz.Rect(x0, current_top, x1, y1)
                pix     = page.get_pixmap(matrix=_fitz.Matrix(3, 3), clip=clip)

                raw_caption   = cap["text"]
                clean_caption = _FIG_PREFIX_RE.sub("", raw_caption).strip()
                fig_m         = _FIG_NUM_RE.match(raw_caption)
                fig_num       = int(fig_m.group(1)) if fig_m else (len(records) + 1)
                minio_key     = f"{part_id}/fig{fig_num:02d}_{_slugify(clean_caption)}.png"

                records.append({
                    "part_id":    part_id,
                    "caption":    clean_caption,
                    "source_page": page_num,
                    "minio_key":  minio_key,
                    "image_bytes": pix.tobytes("png"),
                    "table_ref":  "P3-P4-charts",
                })

            current_top = row_bottom

    return records


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse(pdf_path: str = PDF_PATH) -> dict:
    warnings_list: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        part_id = _extract_part_id(pdf)
        if not part_id:
            warnings_list.append("Could not extract part_id from page 1 title")
            part_id = "UNKNOWN"

        footnotes = extract_footnotes_dynamic(pdf)
        parts     = parse_parts(pdf, part_id)
        max_rat   = parse_max_ratings(pdf, part_id)
        thermal   = parse_thermal(pdf, part_id)
        electrical= parse_electrical(pdf, part_id)

    charts_full = parse_typical_charts(pdf_path, part_id)
    # Strip image_bytes — not JSON-serialisable; callers needing bytes use
    # parse_typical_charts() directly before MinIO upload.
    charts_meta = [
        {k: v for k, v in r.items() if k != "image_bytes"}
        for r in charts_full
    ]

    return {
        "tables": {
            "parts":                      parts,
            "max_ratings":                max_rat,
            "thermal_characteristics":    thermal,
            "electrical_characteristics": electrical,
            "typical_charts":             charts_meta,
        },
        "footnotes": footnotes,
        "warnings":  warnings_list,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    result = parse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
