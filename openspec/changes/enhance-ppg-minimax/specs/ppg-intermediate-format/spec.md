## ADDED Requirements

### Requirement: Optional intermediate format output
The system SHALL support producing Markdown or JSON intermediate formats alongside the field specification.

#### Scenario: Markdown output requested
- **WHEN** user requests Markdown intermediate format
- **THEN** system SHALL produce a Markdown file with preserved heading hierarchy, paragraph structure, and table representation

#### Scenario: JSON output requested
- **WHEN** user requests JSON intermediate format
- **THEN** system SHALL produce a JSON structure with page_number, blocks, bbox, and metadata fields

#### Scenario: Both formats requested
- **WHEN** user requests both Markdown and JSON
- **THEN** system SHALL produce both files in the output directory

### Requirement: Format selection guidance
The system SHALL provide guidance on when to use Markdown vs JSON based on downstream needs.

#### Scenario: Downstream is LLM processing
- **WHEN** the extraction result will be fed to an LLM
- **THEN** system SHALL recommend Markdown as the primary format

#### Scenario: Downstream is structured extraction
- **WHEN** the extraction result will be used for structured field extraction
- **THEN** system SHALL recommend JSON as the primary format