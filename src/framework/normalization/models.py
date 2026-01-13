import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class NormalizedIssue(BaseModel):
    """Normalized representation of a SAST finding"""
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the issue"
    )
    tool: str = Field(description="Name of the SAST tool")
    rule_id: str = Field(description="Rule identifier from the tool")
    rule_name: Optional[str] = Field(None, description="Human-readable rule name")
    file_path: str = Field(description="Path to the file (relative to project root)")
    line_number: int = Field(description="Line number where issue was found")
    column_number: Optional[int] = Field(None, description="Column number")
    end_line: Optional[int] = Field(None, description="End line number")
    end_column: Optional[int] = Field(None, description="End column number")
    severity: str = Field(description="Severity level (error, warning, info)")
    confidence: Optional[str] = Field(None, description="Confidence level")
    message: str = Field(description="Description of the issue")
    snippet: Optional[str] = Field(None, description="Code snippet")
    category: Optional[str] = Field(None, description="Issue category (security, performance, etc.)")
    cwe_id: Optional[str] = Field(None, description="CWE identifier")
    partial_fingerprint: Optional[str] = Field(None, description="Fingerprint for tracking same issues across runs")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Original raw data for debugging")

    @field_validator('severity')
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        """Normalize severity to lowercase"""
        return v.lower() if v else "info"

    def get_fingerprint(self) -> str:
        """Generate a fingerprint for issue comparison"""
        # Use partial_fingerprint if available, otherwise create our own
        if self.partial_fingerprint:
            return self.partial_fingerprint

        # Create fingerprint from key attributes
        fingerprint_parts = [
            self.tool,
            self.rule_id,
            self.file_path,
            str(self.line_number),
            self.severity,
            self.message[:100]  # First 100 chars of message
        ]
        return "|".join(fingerprint_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            **self.model_dump(exclude_none=True),
            "id": self.id,
            "tool": self.tool,
            "rule_id": self.rule_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "severity": self.severity,
            "message": self.message,
        }


class NormalizedResult(BaseModel):
    """Collection of normalized issues for a tool run"""
    tool: str
    project: str
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_seconds: Optional[float] = None
    issues: List[NormalizedIssue] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def issues_by_severity(self) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "tool": self.tool,
            "project": self.project,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": self.issue_count,
            "issues_by_severity": self.issues_by_severity,
            "metadata": self.metadata,
        }