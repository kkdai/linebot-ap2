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


class ShoppingIntent(BaseModel):
    """Shopping intent parameters for human-not-present scenarios."""
    product_categories: List[str] = Field(default_factory=list)
    specific_skus: List[str] = Field(default_factory=list)
    budget_max: Optional[float] = None
    budget_currency: str = "USD"
    criteria: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"refundable": True}


class IntentMandate(BaseModel):
    """
    Intent Mandate for human-not-present scenarios.
    Per AP2 Specification Section 4.1.2.
    """
    mandate_id: str
    type: str = "intent_mandate"
    user_id: str

    # AP2 Spec 4.1.2 required fields
    prompt_playback: str  # Agent's understanding of user request
    shopping_intent: ShoppingIntent
    chargeable_payment_methods: List[str] = Field(default_factory=list)
    time_to_live: datetime

    # Payer/Payee info
    payer_info: PayerInfo
    payee_info: Optional[PayeeInfo] = None  # May be determined later

    # Risk & Security
    risk_payload: RiskPayload = Field(default_factory=RiskPayload)
    user_signature: Optional[str] = None  # Hardware-backed signature placeholder

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    status: PaymentStatus = PaymentStatus.PENDING

    def is_expired(self) -> bool:
        """Check if intent mandate has expired."""
        return datetime.now() > self.time_to_live


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


class CredentialStatus(str, Enum):
    """Status of a payment credential."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class PaymentCredential(BaseModel):
    """
    Encrypted payment credential managed by Credential Provider.
    Per AP2 Specification Section 3.1.
    """
    credential_id: str
    user_id: str
    type: PaymentMethodType

    # Display info (non-sensitive)
    last_four: str
    brand: str
    nickname: Optional[str] = None

    # Encrypted sensitive data (card number, etc.)
    encrypted_data: Optional[str] = None

    # User preferences
    is_default: bool = False
    priority: int = 0  # Higher = preferred

    # Transaction limits
    supported_currencies: List[str] = Field(default_factory=lambda: ["USD", "TWD"])
    max_transaction_amount: Optional[float] = None
    min_transaction_amount: float = 0.0

    # Status and validity
    status: CredentialStatus = CredentialStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if credential is valid for use."""
        if self.status != CredentialStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    def supports_transaction(self, amount: float, currency: str) -> bool:
        """Check if credential supports the transaction."""
        if not self.is_valid():
            return False
        if currency not in self.supported_currencies:
            return False
        if amount < self.min_transaction_amount:
            return False
        if self.max_transaction_amount and amount > self.max_transaction_amount:
            return False
        return True


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
    """
    Cart Mandate for human-present scenarios.
    Per AP2 Specification Section 4.1.1.

    Flow: Merchant signs first (step 10), then user confirms (step 21).
    """
    mandate_id: str
    type: str = "cart_mandate"
    user_id: str

    # Cart contents
    items: List[CartItem]
    total_amount: float
    currency: str = "USD"

    # AP2 Spec 4.1.1 new fields
    payer_info: Optional[PayerInfo] = None
    payee_info: Optional[PayeeInfo] = None
    payment_method_token: Optional[str] = None  # Tokenized payment method
    shipping_address: Optional[Dict[str, Any]] = None
    risk_payload: RiskPayload = Field(default_factory=RiskPayload)

    # Signatures (AP2 Spec Section 7.1 Steps 10-11, 21-22)
    merchant_signature: Optional[str] = None  # Merchant signs first
    merchant_signed_at: Optional[datetime] = None
    user_signature: Optional[str] = None  # User confirms
    user_signed_at: Optional[datetime] = None

    # Timestamps and status
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: PaymentStatus = PaymentStatus.PENDING
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def calculate_total(self) -> float:
        """Calculate total amount from items."""
        return sum(item.subtotal for item in self.items)

    def is_expired(self) -> bool:
        """Check if mandate is expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False

    def is_merchant_signed(self) -> bool:
        """Check if merchant has signed."""
        return self.merchant_signature is not None

    def is_user_signed(self) -> bool:
        """Check if user has signed."""
        return self.user_signature is not None

    def is_fully_signed(self) -> bool:
        """Check if both merchant and user have signed."""
        return self.is_merchant_signed() and self.is_user_signed()


class PaymentMandateContents(BaseModel):
    """Contents of the payment mandate per AP2 spec 4.1.3."""
    payment_mandate_id: str
    payment_details_id: str  # Reference to cart/order
    payment_details_total: Dict[str, Any]  # {label, amount: {currency, value}, refund_period}
    payment_response: Dict[str, Any]  # {request_id, method_name, details, shipping_address, ...}
    merchant_agent: str
    timestamp: datetime = Field(default_factory=datetime.now)


class PaymentMandate(BaseModel):
    """
    Payment Mandate for network/issuer visibility.
    Per AP2 Specification Section 4.1.3.

    This VDC is shared with network/issuer along with transaction authorization.
    """
    payment_mandate_id: str
    type: str = "payment_mandate"

    # Bound to cart/intent mandate
    cart_mandate_id: Optional[str] = None
    intent_mandate_id: Optional[str] = None

    # AP2 Spec 4.1.3 required fields
    agent_presence: bool = True  # AI agent involved
    transaction_modality: TransactionModality = TransactionModality.HUMAN_PRESENT

    # Payment details
    payment_mandate_contents: PaymentMandateContents

    # User authorization (JWT/signature for future PKI)
    user_authorization: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    def to_network_payload(self) -> Dict[str, Any]:
        """Generate payload for network/issuer per AP2 spec."""
        return {
            "payment_mandate_id": self.payment_mandate_id,
            "agent_presence": self.agent_presence,
            "transaction_modality": self.transaction_modality.value,
            "cart_mandate_id": self.cart_mandate_id,
            "intent_mandate_id": self.intent_mandate_id,
            "payment_details": {
                "id": self.payment_mandate_contents.payment_details_id,
                "total": self.payment_mandate_contents.payment_details_total,
                "merchant_agent": self.payment_mandate_contents.merchant_agent,
            },
            "user_authorization": self.user_authorization,
            "timestamp": self.created_at.isoformat()
        }


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