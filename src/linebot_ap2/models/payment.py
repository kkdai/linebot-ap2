"""Payment-related data models."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class PaymentMethodType(str, Enum):
    """Payment method types."""
    CARD = "card"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, Enum):
    """Payment status types."""
    PENDING = "pending"
    PENDING_OTP = "pending_otp"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TransactionModality(str, Enum):
    """AP2 transaction modality per spec Section 4.1.3."""
    HUMAN_PRESENT = "human_present"
    HUMAN_NOT_PRESENT = "human_not_present"


class PayerInfo(BaseModel):
    """Verifiable payer identity per AP2 spec 4.1.1."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    device_id: Optional[str] = None
    verified: bool = False


class PayeeInfo(BaseModel):
    """Verifiable merchant/payee identity per AP2 spec 4.1.1."""
    merchant_id: str
    merchant_name: str
    merchant_url: Optional[str] = None
    credential_provider_id: Optional[str] = None


class RiskPayload(BaseModel):
    """Risk signals for fraud prevention per AP2 spec 4.1.1."""
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    user_behavior_score: Optional[float] = None
    previous_transactions: int = 0
    account_age_days: int = 0
    challenge_completed: Optional[str] = None  # "3ds", "otp", etc.


class PaymentMethod(BaseModel):
    """Payment method model."""
    id: str
    type: PaymentMethodType
    last_four: str = Field(..., description="Last 4 digits of payment method")
    brand: str = Field(..., description="Brand (e.g., Visa, Mastercard)")
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CartItem(BaseModel):
    """Cart item model."""
    product_id: str
    name: str
    price: float
    quantity: int = Field(ge=1, description="Quantity must be positive")
    subtotal: float
    
    def calculate_subtotal(self) -> float:
        """Calculate subtotal for this item."""
        return self.price * self.quantity


class CartMandate(BaseModel):
    """Cart mandate for AP2 payment processing."""
    mandate_id: str
    type: str = "cart_mandate"
    user_id: str
    items: List[CartItem]
    total_amount: float
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.now)
    status: PaymentStatus = PaymentStatus.PENDING
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def calculate_total(self) -> float:
        """Calculate total amount from items."""
        return sum(item.subtotal for item in self.items)
    
    def is_expired(self) -> bool:
        """Check if mandate is expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False


class OTPData(BaseModel):
    """OTP verification data."""
    otp: str
    user_id: str
    mandate_id: str
    payment_method_id: str
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """Check if OTP is expired."""
        return datetime.now() > self.expires_at
    
    def is_blocked(self) -> bool:
        """Check if OTP is blocked due to too many attempts."""
        return self.attempts >= self.max_attempts
    
    def increment_attempts(self) -> None:
        """Increment attempt counter."""
        self.attempts += 1


class Transaction(BaseModel):
    """Transaction model."""
    transaction_id: str
    mandate_id: str
    user_id: str
    amount: float
    currency: str = "USD"
    payment_method_id: str
    status: PaymentStatus
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def mark_completed(self) -> None:
        """Mark transaction as completed."""
        self.status = PaymentStatus.COMPLETED
        self.processed_at = datetime.now()
    
    def mark_failed(self, error: str) -> None:
        """Mark transaction as failed."""
        self.status = PaymentStatus.FAILED
        self.error_message = error
        self.processed_at = datetime.now()


class RefundRequest(BaseModel):
    """Refund request model."""
    refund_id: str
    transaction_id: str
    amount: float
    reason: str = ""
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    estimated_arrival: str = "3-5 business days"