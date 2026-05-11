## ADDED Requirements

### Requirement: Label-value pair detection using coordinates
The system SHALL leverage bbox/coordinate information to identify label-value relationships in documents.

#### Scenario: Horizontal label-value pairs
- **WHEN** a text block (label) and another text block (value) are horizontally aligned within threshold
- **THEN** system SHALL candidate them as a label-value pair in review markdown

#### Scenario: Vertical label-value pairs
- **WHEN** a text block appears above another text block with column alignment
- **THEN** system SHALL candidate them as a potential field in review markdown

#### Scenario: Multiple candidate values for a label
- **WHEN** multiple text blocks could be the value for a single label
- **THEN** system SHALL present all candidates in review markdown for user confirmation