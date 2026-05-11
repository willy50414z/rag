# Workflow Artifacts

Use these artifacts as the stable layers of the workflow.

## 1. Classification Summary

Minimum fields:

```yaml
source_file: "<pdf path>"
document_type_guess: "digital-text | scanned | hybrid | uncertain"
backend_path: "<selected backend route>"
classification_reason:
  - "<reason 1>"
  - "<reason 2>"
```

## 2. Raw Extraction

Purpose:

- Preserve low-assumption structure
- Keep source evidence recoverable

Minimum shape:

```json
{
  "document_id": "sample-doc",
  "source_file": "sample.pdf",
  "classification": "digital-text",
  "pages": [
    {
      "page_number": 1,
      "blocks": [
        {
          "block_id": "p1_b1",
          "block_type": "text",
          "text": "Example text",
          "bbox": [0, 0, 100, 20],
          "reading_order": 1,
          "source_type": "text-layer"
        }
      ],
      "tables": [
        {
          "table_id": "p1_t1",
          "page_number": 1,
          "format": "grid",
          "rows": [
            ["Header A", "Header B", "Header C"],
            ["value 1",  "value 2",  "value 3"],
            ["value 4",  "value 5",  "value 6"]
          ],
          "note": null
        }
      ]
    }
  ]
}
```

If a backend cannot supply `bbox`, `reading_order`, or `source_type`, keep the field with `null` or omit it consistently and document the limitation.

### Raw Extraction：Table 行為規則

**禁止行為（此階段不得執行）：**

- 不得將 table 列轉為 key-value 對
- 不得合併、去重任何 cell 值（含重複值，如 Min / Typ / Max 跨多列出現）
- 不得省略任何 cell，空格以空字串 `""` 佔位
- 不得對 cell 內容做語意推斷或格式正規化

**格式選擇（依 backend 能力）：**

| 情境 | format | rows |
|------|--------|------|
| 數位文字、行列對齊可信 | `"grid"` | `List[List[str]]`，第一列為 header（若可辨識） |
| OCR / 行列對齊不確定 | `"raw-text"` | 省略，改用 `"raw"` 欄位保留原始字串 |
| merged cell / 跨列 header 等複雜結構 | `"raw-text"` | 同上，並在 `note` 說明結構限制 |

`raw-text` 範例：

```json
{
  "table_id": "p1_t2",
  "page_number": 1,
  "format": "raw-text",
  "raw": "Parameter | Min | Typ | Max\nVcc | 3.0 | 3.3 | 3.6",
  "note": "OCR alignment uncertain, cannot reliably grid"
}
```

candidate field 和 parser-spec 階段可自由將 table 內容轉為 KV 或其他格式，Raw Extraction 不限制後續處理。

## 3. Normalized Review State

Purpose:

- Make artifacts easier to inspect
- Preserve traceability back to raw blocks

Suggested shape:

```json
{
  "document_id": "sample-doc",
  "sections": [
    {
      "section_id": "s1",
      "page_number": 1,
      "section_type": "header",
      "text": "Example title",
      "source_blocks": ["p1_b1", "p1_b2"],
      "uncertain": false
    }
  ],
  "candidate_fields": [],
  "ambiguities": []
}
```

## 4. Candidate Field State

Suggested shape:

```json
{
  "field_name": "total_amount",
  "description": "Document total amount",
  "candidates": [
    {
      "candidate_id": "c1",
      "value": "1234.56",
      "page_number": 1,
      "source_blocks": ["p1_b9"],
      "evidence": "Total Amount 1234.56",
      "confidence": 0.78
    }
  ],
  "proposed_policy": {
    "required": true,
    "on_missing": "error",
    "strict_extraction": true,
    "validation_description": "Should be a positive number"
  },
  "policy_status": "provisional"
}
```

Use `policy_status` values consistently:

- `provisional`
- `user_confirmed`
- `user_modified`
- `unresolved`

## 5. Parser-Spec Draft

The final guaranteed artifact is a parser-spec draft, not parser code.

The spec should include:

- Document classification and backend path
- Field definitions
- Candidate selection notes
- User-confirmed and unresolved policies
- Ambiguities that still need review
