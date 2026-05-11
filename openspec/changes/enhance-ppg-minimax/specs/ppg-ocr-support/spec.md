## ADDED Requirements

### Requirement: OCR pipeline guidance for scanned PDFs
The system SHALL provide clear OCR pipeline guidance when processing scanned or hybrid PDFs.

#### Scenario: PDF classified as scanned
- **WHEN** ppg-explore classifies PDF as `scanned` or `hybrid`
- **THEN** system SHALL route to OCR-aware extraction path with documented backend options

#### Scenario: OCR backend not available
- **WHEN** preferred OCR backend is not available in environment
- **THEN** system SHALL report which backend is missing, what capability is lost, and suggest downgrade path

#### Scenario: Multi-page scanned document
- **WHEN** processing a multi-page scanned PDF
- **THEN** system SHALL preserve page-level metadata and report per-page OCR confidence if available

### Requirement: OCR quality awareness
The system SHALL make users aware that OCR output may contain errors and requires validation.

#### Scenario: OCR result contains low-confidence characters
- **WHEN** OCR backend reports low-confidence characters in extraction
- **THEN** system SHALL flag these characters for human review in the review markdown

#### Scenario: Scanned PDF with tables
- **WHEN** processing a scanned PDF that contains tables
- **THEN** system SHALL note that table structure may be degraded and require manual verification