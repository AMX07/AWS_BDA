"""Configuration objects for the Bedrock Data Automation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BlueprintField:
    """Represents a single data field to extract from documents."""

    name: str
    instructions: str
    data_type: str = "string"
    allow_multiple: bool = True
    synonyms: List[str] = field(default_factory=list)

    def to_blueprint(self) -> Dict[str, object]:
        """Return the field definition expressed as BDA blueprint JSON."""

        extraction: Dict[str, object] = {
            "name": self.name,
            "type": self.data_type,
            "allowMultiple": self.allow_multiple,
            "instructions": self.instructions,
        }
        if self.synonyms:
            extraction["synonyms"] = self.synonyms
        return extraction


@dataclass
class PipelineConfig:
    """Runtime configuration for executing the BDA pipeline."""

    blueprint_name: str
    input_s3_uri: str
    output_s3_uri: str
    output_csv_path: str
    region_name: str = "us-east-1"
    blueprint_description: str = (
        "Extract, transform, and load entity data from insurance documents into CSV."
    )
    job_tags: Optional[Dict[str, str]] = None
    role_arn: Optional[str] = None
    job_name: Optional[str] = None
    field_definitions: List[BlueprintField] = field(default_factory=list)

    def ensure_field_definitions(self) -> List[BlueprintField]:
        """Return the configured field definitions, populating defaults when needed."""

        if not self.field_definitions:
            self.field_definitions = default_field_definitions()
        return self.field_definitions


def default_field_definitions() -> List[BlueprintField]:
    """Default blueprint fields covering all requested data entities."""

    return [
        BlueprintField(
            name="SiteOnForm",
            instructions=(
                "Identify every website, URL, or domain on the document. Include full paths "
                "when available. Detect hyperlinks even when URLs are hidden, mapping known "
                "phrases like 'Online Account Manager' to 'OAM'. Return comma separated list." 
            ),
            data_type="list",
        ),
        BlueprintField(
            name="NameOnForm",
            instructions=(
                "List every organization, insurer, or company name appearing on the document." 
            ),
            data_type="list",
        ),
        BlueprintField(
            name="LogoOnForm",
            instructions=(
                "Detect and classify every logo present using the provided reference catalog."
                "Return catalog identifiers separated by commas with no spaces."
            ),
            data_type="list",
        ),
        BlueprintField(
            name="EmailOnForm",
            instructions="Extract every email address.",
            data_type="list",
        ),
        BlueprintField(
            name="PhoneOnForm",
            instructions=(
                "Capture every phone or fax number including area codes and repeated service "
                "numbers such as 1-833-327-8787."
            ),
            data_type="list",
        ),
        BlueprintField(
            name="AddressOnForm",
            instructions=(
                "Return all physical mailing addresses or PO Boxes. Use brackets when multiple "
                "addresses are present and omit entries lacking street or PO Box details."
            ),
            data_type="list",
        ),
        BlueprintField(
            name="SignatureOnForm",
            instructions=(
                "Identify signatures, matching them to the known signer reference list when possible."
            ),
            data_type="list",
        ),
        BlueprintField(
            name="LOB",
            instructions=(
                "Extract an explicit form identifier such as '031-077'. Use digits before the first "
                "hyphen to map to the provided series and return the corresponding line of business "
                "description. Leave blank if no identifier is visible."
            ),
        ),
        BlueprintField(
            name="State",
            instructions=(
                "Return the two-letter state code. Prefer 'IN' for Indiana Farm Bureau Insurance and "
                "'OH' when East Street Insurance or its logo is present."
            ),
        ),
        BlueprintField(
            name="Language",
            instructions="Return the document's primary language in plain text (e.g., English).",
        ),
    ]
