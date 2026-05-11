## ADDED Requirements

### Requirement: Chunking pre-assessment guidance
The system SHALL provide guidance on how extraction results affect downstream chunking decisions.

#### Scenario: Extraction output contains section markers
- **WHEN** extracted data includes section/title markers
- **THEN** system SHALL note these in review markdown as recommended chunk boundaries

#### Scenario: Table spans multiple chunks
- **WHEN** a table is detected that may span chunk boundaries
- **THEN** system SHALL recommend keeping table intact as a single chunk or marking split points

#### Scenario: Page boundary awareness
- **WHEN** content crosses page boundaries
- **THEN** system SHALL preserve page_number metadata to inform chunking decisions