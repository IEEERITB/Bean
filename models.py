from typing import List, Optional
from pydantic import BaseModel, Field

class EventReport(BaseModel):
    event_title: str = Field(..., description="Official name of the event")
    date: str = Field(..., description="Standardized date format (e.g., YYYY-MM-DD) or 'UNKNOWN'")
    speaker_name: Optional[str] = Field(None, description="Name of the guest/speaker or 'UNKNOWN'")
    attendance_count: int | str = Field(..., description="Number of participants or 'UNKNOWN'")
    duration_hours: float | str = Field(..., description="Length of the event in hours or 'UNKNOWN'")
    executive_summary: str = Field(..., description="A formal 3-sentence summary or 'UNKNOWN'")
    key_takeaways: List[str] = Field(default_factory=list, description="3 bullet points highlighting outcomes or empty list if unknown")
    missing_info: List[str] = Field(default_factory=list, description="List of required fields that are currently 'UNKNOWN' or missing")
