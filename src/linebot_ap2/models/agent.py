"""Agent-related data models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class AgentType(str, Enum):
    """Agent types."""
    SHOPPING = "shopping"
    PAYMENT = "payment"


class ResponseStatus(str, Enum):
    """Response status types."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    ESCALATED = "escalated"


class AgentResponse(BaseModel):
    """Agent response model."""
    agent_type: AgentType
    user_id: str
    session_id: str
    message: str
    response: str
    status: ResponseStatus = ResponseStatus.SUCCESS
    processing_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    def mark_error(self, error: str) -> None:
        """Mark response as error."""
        self.status = ResponseStatus.ERROR
        self.error_message = error
    
    def mark_escalated(self, reason: str) -> None:
        """Mark response as escalated."""
        self.status = ResponseStatus.ESCALATED
        self.error_message = reason


class IntentResult(BaseModel):
    """Intent detection result."""
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    matched_keywords: List[str] = Field(default_factory=list)
    matched_patterns: List[str] = Field(default_factory=list)
    all_scores: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_confident(self) -> bool:
        """Check if detection confidence is high enough."""
        return self.confidence >= 0.7
    
    @property
    def has_matches(self) -> bool:
        """Check if any keywords or patterns were matched."""
        return len(self.matched_keywords) > 0 or len(self.matched_patterns) > 0


class AgentMetrics(BaseModel):
    """Agent performance metrics."""
    agent_type: AgentType
    total_requests: int = 0
    successful_responses: int = 0
    error_responses: int = 0
    escalated_responses: int = 0
    average_processing_time: float = 0.0
    last_activity: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_responses / self.total_requests
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.error_responses / self.total_requests
    
    def update_metrics(self, response: AgentResponse) -> None:
        """Update metrics with new response."""
        self.total_requests += 1
        self.last_activity = response.timestamp
        
        if response.status == ResponseStatus.SUCCESS:
            self.successful_responses += 1
        elif response.status == ResponseStatus.ERROR:
            self.error_responses += 1
        elif response.status == ResponseStatus.ESCALATED:
            self.escalated_responses += 1
        
        # Update average processing time
        total_time = self.average_processing_time * (self.total_requests - 1)
        self.average_processing_time = (total_time + response.processing_time) / self.total_requests


class UserSession(BaseModel):
    """User session data."""
    user_id: str
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    current_context: Dict[str, Any] = Field(default_factory=dict)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        self.message_count += 1
    
    @property
    def is_active(self) -> bool:
        """Check if session is recently active (within 30 minutes)."""
        from datetime import timedelta
        return datetime.now() - self.last_activity < timedelta(minutes=30)