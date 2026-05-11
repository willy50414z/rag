## 1. Update ppg-explore Skill

- [ ] 1.1 Add OCR pipeline section in Environment Check (backend options: pytesseract, docling, cloud OCR)
- [ ] 1.2 Add OCR routing logic when PDF classified as scanned/hybrid
- [ ] 1.3 Add table extraction as separate task in artifact structure (table_blocks vs text_blocks)
- [ ] 1.4 Add coordinate-based label-value detection logic in Review Markdown generation
- [ ] 1.5 Add chunking pre-assessment notes in review markdown (section boundaries, table intactness)
- [ ] 1.6 Add intermediate format selection guidance (Markdown vs JSON recommendation)

## 2. Add Reference Documents

- [ ] 2.1 Create ppg-ocr-reference.md with OCR tool options and quality considerations
- [ ] 2.2 Create ppg-table-extraction-guide.md with table detection patterns
- [ ] 2.3 Update workflow-artifacts.md to include table_blocks structure

## 3. Optional: Update ppg-apply Skill

- [ ] 3.1 Add support for JSON intermediate format output option
- [ ] 3.2 Add validation for coordinate-based extraction results

## 4. Testing

- [ ] 4.1 Test ppg-explore with a scanned PDF sample
- [ ] 4.2 Test ppg-explore with a PDF containing tables
- [ ] 4.3 Verify intermediate format outputs (Markdown and JSON)