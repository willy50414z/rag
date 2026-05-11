## ADDED Requirements

### Requirement: Table extraction as separate task
The system SHALL treat table extraction as an independent parsing task, not just as a field among other fields.

#### Scenario: PDF contains tables
- **WHEN** ppg-explore detects table-like structures in PDF
- **THEN** system SHALL extract table data with row/column structure preserved

#### Scenario: Table has no visible borders
- **WHEN** extracting tables without border lines
- **THEN** system SHALL attempt to infer row/column boundaries from alignment and whitespace

#### Scenario: Table spans multiple pages
- **WHEN** a table is split across multiple PDF pages
- **THEN** system SHALL mark the table as continuous with page references

### Requirement: Table metadata preservation
The system SHALL preserve table-level metadata for downstream processing.

#### Scenario: Table extracted successfully
- **WHEN** table extraction completes
- **THEN** output SHALL include table_id, page_number, row_count, column_count, and source coordinates

#### Scenario: Table extraction fails
- **WHEN** table structure cannot be reliably extracted
- **THEN** system SHALL fall back to raw text extraction and note the limitation in review markdown