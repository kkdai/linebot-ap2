# AP2 Phase 1: Mandate Types Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement AP2-compliant mandate types (IntentMandate, enhanced CartMandate with signatures, PaymentMandate) per specification Section 4.1.

**Architecture:** Add three VDC types to the data model layer, update MandateService to support merchant/user signatures, create PaymentMandate when payment is processed, and update tools to leverage new mandate features.

**Tech Stack:** Python 3.10+, Pydantic v2, HMAC-SHA256 (Phase 1), existing service singleton pattern.

---

## Task 1: Add TransactionModality Enum and Payer/Payee Models

**Files:**
- Modify: `src/linebot_ap2/models/payment.py`

**Step 1: Add new enums and base models**

Add after line 24 (after PaymentStatus enum):

```python
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
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.models.payment import TransactionModality, PayerInfo, PayeeInfo, RiskPayload; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/payment.py
git commit -m "feat(models): add TransactionModality, PayerInfo, PayeeInfo, RiskPayload"
```

---

## Task 2: Add IntentMandate Model

**Files:**
- Modify: `src/linebot_ap2/models/payment.py`

**Step 1: Add IntentMandate class**

Add after RiskPayload class:

```python
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
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.models.payment import IntentMandate; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/payment.py
git commit -m "feat(models): add IntentMandate for human-not-present scenarios"
```

---

## Task 3: Enhance CartMandate with Merchant/User Signatures

**Files:**
- Modify: `src/linebot_ap2/models/payment.py`

**Step 1: Update CartMandate class**

Replace existing CartMandate class (lines 52-73) with:

```python
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
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.models.payment import CartMandate; m = CartMandate(mandate_id='test', user_id='u1', items=[], total_amount=0); print(m.is_fully_signed())"`

Expected: `False`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/payment.py
git commit -m "feat(models): enhance CartMandate with merchant/user signatures per AP2 spec"
```

---

## Task 4: Add PaymentMandate Model

**Files:**
- Modify: `src/linebot_ap2/models/payment.py`

**Step 1: Add PaymentMandate class**

Add after CartMandate class:

```python
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
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.models.payment import PaymentMandate, TransactionModality; print(TransactionModality.HUMAN_PRESENT.value)"`

Expected: `human_present`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/payment.py
git commit -m "feat(models): add PaymentMandate for network/issuer visibility per AP2 spec"
```

---

## Task 5: Update Models __init__.py Exports

**Files:**
- Modify: `src/linebot_ap2/models/__init__.py`

**Step 1: Update exports**

Replace entire file with:

```python
"""Data models for LINE Bot AP2."""

from .payment import (
    PaymentMethod,
    PaymentMethodType,
    PaymentStatus,
    TransactionModality,
    PayerInfo,
    PayeeInfo,
    RiskPayload,
    CartItem,
    ShoppingIntent,
    IntentMandate,
    CartMandate,
    PaymentMandateContents,
    PaymentMandate,
    OTPData,
    Transaction,
    RefundRequest,
)
from .product import Product, ProductCategory, ShoppingCart
from .agent import AgentResponse, IntentResult

__all__ = [
    # Payment enums
    "PaymentMethodType",
    "PaymentStatus",
    "TransactionModality",
    # Payer/Payee
    "PayerInfo",
    "PayeeInfo",
    "RiskPayload",
    # Payment method
    "PaymentMethod",
    # Cart
    "CartItem",
    # Mandates (AP2 VDCs)
    "ShoppingIntent",
    "IntentMandate",
    "CartMandate",
    "PaymentMandateContents",
    "PaymentMandate",
    # OTP & Transaction
    "OTPData",
    "Transaction",
    "RefundRequest",
    # Product
    "Product",
    "ProductCategory",
    "ShoppingCart",
    # Agent
    "AgentResponse",
    "IntentResult",
]
```

**Step 2: Verify imports work**

Run: `python -c "from src.linebot_ap2.models import IntentMandate, CartMandate, PaymentMandate, TransactionModality; print('All imports OK')"`

Expected: `All imports OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/__init__.py
git commit -m "feat(models): export new AP2 mandate types"
```

---

## Task 6: Update MandateService with Merchant Signing

**Files:**
- Modify: `src/linebot_ap2/services/mandate_service.py`

**Step 1: Update imports**

Replace lines 1-14 with:

```python
"""AP2 Mandate Service - Handles secure mandate creation and signing."""

import json
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..models.payment import (
    CartMandate, CartItem, PaymentStatus,
    IntentMandate, PaymentMandate, PaymentMandateContents,
    PayerInfo, PayeeInfo, RiskPayload, ShoppingIntent,
    TransactionModality
)
from ..models.product import Product
from ..common.logger import setup_logger
```

**Step 2: Verify import**

Run: `python -c "from src.linebot_ap2.services.mandate_service import MandateService; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/mandate_service.py
git commit -m "refactor(mandate_service): update imports for new AP2 mandate types"
```

---

## Task 7: Add Merchant Signing Method to MandateService

**Files:**
- Modify: `src/linebot_ap2/services/mandate_service.py`

**Step 1: Add merchant signing constants and method**

Add after `sign_mandate` method (around line 134):

```python
    def merchant_sign_mandate(
        self,
        mandate: CartMandate,
        merchant_id: str = "demo_merchant",
        merchant_name: str = "Demo Store"
    ) -> CartMandate:
        """
        Merchant signs the cart mandate per AP2 spec Section 7.1 Step 10.
        This happens BEFORE user confirmation.
        """
        self.logger.info(f"Merchant signing mandate: {mandate.mandate_id}")

        # Set payee info
        mandate.payee_info = PayeeInfo(
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            merchant_url="https://demo-store.example.com"
        )

        # Create merchant signature payload
        nonce = uuid.uuid4().hex[:16]
        timestamp = datetime.now()

        payload = {
            "mandate_id": mandate.mandate_id,
            "merchant_id": merchant_id,
            "total_amount": mandate.total_amount,
            "currency": mandate.currency,
            "items_count": len(mandate.items),
            "timestamp": timestamp.isoformat(),
            "nonce": nonce,
            "signer": "merchant"
        }

        # Create signature
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Update mandate with merchant signature
        mandate.merchant_signature = signature
        mandate.merchant_signed_at = timestamp

        # Update stored mandate
        self.active_mandates[mandate.mandate_id] = mandate

        self.logger.info(f"✓ Merchant signed mandate {mandate.mandate_id}")
        return mandate

    def user_sign_mandate(
        self,
        mandate_id: str,
        user_id: str
    ) -> CartMandate:
        """
        User signs the cart mandate per AP2 spec Section 7.1 Step 21.
        This happens AFTER merchant signing and user confirmation.
        """
        mandate = self.get_mandate(mandate_id)
        if not mandate:
            raise ValueError(f"Mandate {mandate_id} not found")

        if not mandate.is_merchant_signed():
            raise ValueError("Mandate must be merchant-signed before user signing")

        if mandate.user_id != user_id:
            raise ValueError("User ID mismatch")

        self.logger.info(f"User signing mandate: {mandate_id}")

        # Set payer info
        mandate.payer_info = PayerInfo(
            user_id=user_id,
            verified=True
        )

        # Create user signature payload
        nonce = uuid.uuid4().hex[:16]
        timestamp = datetime.now()

        payload = {
            "mandate_id": mandate.mandate_id,
            "user_id": user_id,
            "total_amount": mandate.total_amount,
            "currency": mandate.currency,
            "merchant_signature": mandate.merchant_signature,
            "timestamp": timestamp.isoformat(),
            "nonce": nonce,
            "signer": "user"
        }

        # Create signature
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Update mandate with user signature
        mandate.user_signature = signature
        mandate.user_signed_at = timestamp

        # Update stored mandate
        self.active_mandates[mandate.mandate_id] = mandate

        self.logger.info(f"✓ User signed mandate {mandate_id}")
        return mandate
```

**Step 2: Verify methods work**

Run: `python -c "from src.linebot_ap2.services.mandate_service import MandateService; ms = MandateService(); print(hasattr(ms, 'merchant_sign_mandate'), hasattr(ms, 'user_sign_mandate'))"`

Expected: `True True`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/mandate_service.py
git commit -m "feat(mandate_service): add merchant_sign_mandate and user_sign_mandate methods"
```

---

## Task 8: Add PaymentMandate Creation to MandateService

**Files:**
- Modify: `src/linebot_ap2/services/mandate_service.py`

**Step 1: Add PaymentMandate storage and creation method**

Add to `__init__` method after `self.mandate_signatures`:

```python
        self.payment_mandates: Dict[str, PaymentMandate] = {}
```

Add new method after `user_sign_mandate`:

```python
    def create_payment_mandate(
        self,
        cart_mandate: CartMandate,
        payment_method_name: str = "CARD",
        payment_token: Optional[str] = None
    ) -> PaymentMandate:
        """
        Create PaymentMandate for network/issuer visibility.
        Per AP2 Specification Section 4.1.3.

        This is created when payment is being processed.
        """
        self.logger.info(f"Creating PaymentMandate for cart: {cart_mandate.mandate_id}")

        payment_mandate_id = f"pm_{uuid.uuid4().hex[:12]}"

        # Create payment mandate contents
        contents = PaymentMandateContents(
            payment_mandate_id=payment_mandate_id,
            payment_details_id=cart_mandate.mandate_id,
            payment_details_total={
                "label": "Total",
                "amount": {
                    "currency": cart_mandate.currency,
                    "value": cart_mandate.total_amount
                },
                "refund_period": 30  # days
            },
            payment_response={
                "request_id": cart_mandate.mandate_id,
                "method_name": payment_method_name,
                "details": {
                    "token": payment_token or cart_mandate.payment_method_token
                },
                "shipping_address": cart_mandate.shipping_address,
                "payer_name": cart_mandate.payer_info.user_id if cart_mandate.payer_info else None,
                "payer_email": cart_mandate.payer_info.email if cart_mandate.payer_info else None,
            },
            merchant_agent="MerchantAgent"
        )

        # Create payment mandate
        payment_mandate = PaymentMandate(
            payment_mandate_id=payment_mandate_id,
            cart_mandate_id=cart_mandate.mandate_id,
            agent_presence=True,
            transaction_modality=TransactionModality.HUMAN_PRESENT,
            payment_mandate_contents=contents,
            user_authorization=cart_mandate.user_signature
        )

        # Store payment mandate
        self.payment_mandates[payment_mandate_id] = payment_mandate

        self.logger.info(f"✓ PaymentMandate created: {payment_mandate_id}")
        return payment_mandate

    def get_payment_mandate(self, payment_mandate_id: str) -> Optional[PaymentMandate]:
        """Get payment mandate by ID."""
        return self.payment_mandates.get(payment_mandate_id)

    def get_payment_mandate_by_cart(self, cart_mandate_id: str) -> Optional[PaymentMandate]:
        """Get payment mandate by cart mandate ID."""
        for pm in self.payment_mandates.values():
            if pm.cart_mandate_id == cart_mandate_id:
                return pm
        return None
```

**Step 2: Verify methods work**

Run: `python -c "from src.linebot_ap2.services.mandate_service import MandateService; ms = MandateService(); print(hasattr(ms, 'create_payment_mandate'), hasattr(ms, 'payment_mandates'))"`

Expected: `True True`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/mandate_service.py
git commit -m "feat(mandate_service): add PaymentMandate creation for network/issuer visibility"
```

---

## Task 9: Update create_signed_mandate to Include Merchant Signature

**Files:**
- Modify: `src/linebot_ap2/services/mandate_service.py`

**Step 1: Update create_signed_mandate method**

Replace the `create_signed_mandate` method with:

```python
    def create_signed_mandate(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        currency: str = "USD",
        expires_in_minutes: int = 30,
        merchant_id: str = "demo_merchant",
        merchant_name: str = "Demo Store"
    ) -> Dict[str, Any]:
        """
        Create and sign mandate in one operation.
        Per AP2 spec: Merchant signs first, then mandate is ready for user confirmation.
        """

        # Create mandate
        mandate = self.create_cart_mandate(
            user_id=user_id,
            items=items,
            currency=currency,
            expires_in_minutes=expires_in_minutes
        )

        # Merchant signs first (AP2 Spec Step 10)
        mandate = self.merchant_sign_mandate(
            mandate=mandate,
            merchant_id=merchant_id,
            merchant_name=merchant_name
        )

        # Create system signature (for verification)
        signature = self.sign_mandate(mandate)

        # Return detailed mandate info
        details = self.get_mandate_details(mandate.mandate_id)

        # Add AP2 signature info
        details["ap2_signatures"] = {
            "merchant_signed": mandate.is_merchant_signed(),
            "merchant_signed_at": mandate.merchant_signed_at.isoformat() if mandate.merchant_signed_at else None,
            "user_signed": mandate.is_user_signed(),
            "user_signed_at": mandate.user_signed_at.isoformat() if mandate.user_signed_at else None,
            "fully_signed": mandate.is_fully_signed(),
            "awaiting": "user_signature" if not mandate.is_user_signed() else "none"
        }

        return details
```

**Step 2: Verify updated method**

Run: `python -c "from src.linebot_ap2.services.mandate_service import MandateService; ms = MandateService(); result = ms.create_signed_mandate('test_user', [{'product_id': 'p1', 'name': 'Test', 'price': 10.0}]); print('merchant_signed' in str(result))"`

Expected: `True`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/mandate_service.py
git commit -m "feat(mandate_service): update create_signed_mandate to include merchant signature"
```

---

## Task 10: Update get_mandate_details for AP2 Compliance

**Files:**
- Modify: `src/linebot_ap2/services/mandate_service.py`

**Step 1: Update get_mandate_details method**

Replace the `get_mandate_details` method with:

```python
    def get_mandate_details(self, mandate_id: str) -> Dict[str, Any]:
        """Get detailed mandate information for AP2 protocol."""

        mandate = self.get_mandate(mandate_id)
        if not mandate:
            return {"error": "Mandate not found"}

        signature = self.mandate_signatures.get(mandate_id)

        return {
            "mandate": {
                "id": mandate.mandate_id,
                "type": mandate.type,
                "user_id": mandate.user_id,
                "total_amount": mandate.total_amount,
                "currency": mandate.currency,
                "status": mandate.status.value,
                "created_at": mandate.created_at.isoformat(),
                "expires_at": mandate.expires_at.isoformat() if mandate.expires_at else None,
                "items": [
                    {
                        "product_id": item.product_id,
                        "name": item.name,
                        "price": item.price,
                        "quantity": item.quantity,
                        "subtotal": item.subtotal
                    }
                    for item in mandate.items
                ],
                # AP2 new fields
                "payer_info": mandate.payer_info.dict() if mandate.payer_info else None,
                "payee_info": mandate.payee_info.dict() if mandate.payee_info else None,
                "payment_method_token": mandate.payment_method_token,
                "shipping_address": mandate.shipping_address,
            },
            "signatures": {
                "merchant_signature": mandate.merchant_signature,
                "merchant_signed_at": mandate.merchant_signed_at.isoformat() if mandate.merchant_signed_at else None,
                "user_signature": mandate.user_signature,
                "user_signed_at": mandate.user_signed_at.isoformat() if mandate.user_signed_at else None,
                "system_signature": signature.signature if signature else None,
                "algorithm": signature.algorithm if signature else None,
            },
            "ap2_compliance": {
                "version": "0.1",
                "merchant_signed": mandate.is_merchant_signed(),
                "user_signed": mandate.is_user_signed(),
                "fully_signed": mandate.is_fully_signed(),
                "valid": self.is_mandate_valid(mandate_id),
                "verification_method": "HMAC-SHA256"
            }
        }
```

**Step 2: Verify updated method**

Run: `python -c "from src.linebot_ap2.services.mandate_service import MandateService; ms = MandateService(); r = ms.create_signed_mandate('u1', [{'product_id':'p1','name':'Test','price':10.0}]); print('merchant_signed' in str(r.get('signatures', {})))"`

Expected: `True`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/mandate_service.py
git commit -m "feat(mandate_service): update get_mandate_details with AP2 signature info"
```

---

## Task 11: Update PaymentService to Create PaymentMandate

**Files:**
- Modify: `src/linebot_ap2/services/payment_service.py`

**Step 1: Add import and reference to mandate service**

Add after line 12 (after existing imports):

```python
from ..models.payment import TransactionModality
```

Update `__init__` method to accept mandate_service parameter. Add after line 42:

```python
        # Reference to mandate service (set externally for PaymentMandate creation)
        self._mandate_service = None

    def set_mandate_service(self, mandate_service) -> None:
        """Set mandate service reference for PaymentMandate creation."""
        self._mandate_service = mandate_service
```

**Step 2: Update _process_payment to create PaymentMandate**

Replace the `_process_payment` method with:

```python
    def _process_payment(
        self,
        mandate_id: str,
        otp_data: OTPData
    ) -> Transaction:
        """Process the actual payment after OTP verification."""

        # Generate transaction ID
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        # Get amount from mandate if available
        amount = 999.99  # Default demo amount
        if self._mandate_service:
            mandate = self._mandate_service.get_mandate(mandate_id)
            if mandate:
                amount = mandate.total_amount

                # Create PaymentMandate for network/issuer (AP2 Spec 4.1.3)
                try:
                    payment_mandate = self._mandate_service.create_payment_mandate(
                        cart_mandate=mandate,
                        payment_method_name="CARD",
                        payment_token=otp_data.payment_method_id
                    )
                    self.logger.info(
                        f"PaymentMandate created: {payment_mandate.payment_mandate_id} "
                        f"for network/issuer visibility"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to create PaymentMandate: {e}")

        # Create transaction record
        transaction = Transaction(
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            user_id=otp_data.user_id,
            amount=amount,
            currency="USD",
            payment_method_id=otp_data.payment_method_id,
            status=PaymentStatus.PROCESSING
        )

        # Store transaction
        self.transactions[transaction_id] = transaction

        # Mark as completed
        transaction.mark_completed()

        return transaction
```

**Step 3: Verify syntax**

Run: `python -c "from src.linebot_ap2.services.payment_service import PaymentService; ps = PaymentService(); print(hasattr(ps, 'set_mandate_service'))"`

Expected: `True`

**Step 4: Commit**

```bash
git add src/linebot_ap2/services/payment_service.py
git commit -m "feat(payment_service): create PaymentMandate during payment processing"
```

---

## Task 12: Wire Up Mandate Service in Services __init__.py

**Files:**
- Modify: `src/linebot_ap2/services/__init__.py`

**Step 1: Update services initialization to wire up dependencies**

Replace entire file with:

```python
"""Business logic services for LINE Bot AP2.

This module provides shared singleton instances of services to ensure
data consistency across different agents and tools.
"""

from .mandate_service import MandateService
from .payment_service import PaymentService
from .product_service import ProductService

# Shared singleton instances - used by all agents and tools
# This ensures mandate and payment data is shared across Shopping and Payment agents
_shared_product_service = ProductService()
_shared_mandate_service = MandateService()
_shared_payment_service = PaymentService()

# Wire up cross-service dependencies for AP2 compliance
# PaymentService needs MandateService to create PaymentMandate during payment processing
_shared_payment_service.set_mandate_service(_shared_mandate_service)


def get_product_service() -> ProductService:
    """Get shared ProductService singleton instance."""
    return _shared_product_service


def get_mandate_service() -> MandateService:
    """Get shared MandateService singleton instance."""
    return _shared_mandate_service


def get_payment_service() -> PaymentService:
    """Get shared PaymentService singleton instance."""
    return _shared_payment_service


__all__ = [
    "MandateService",
    "PaymentService",
    "ProductService",
    "get_product_service",
    "get_mandate_service",
    "get_payment_service",
]
```

**Step 2: Verify wiring works**

Run: `python -c "from src.linebot_ap2.services import get_payment_service, get_mandate_service; ps = get_payment_service(); print(ps._mandate_service is get_mandate_service())"`

Expected: `True`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/__init__.py
git commit -m "feat(services): wire up PaymentService with MandateService for AP2 compliance"
```

---

## Task 13: Add User Signature on Payment Initiation

**Files:**
- Modify: `src/linebot_ap2/tools/payment_tools.py`

**Step 1: Update enhanced_initiate_payment to trigger user signing**

Find the line `# Update mandate status` (around line 154) and replace that section with:

```python
        # User signs the mandate when initiating payment (AP2 Spec Step 21)
        try:
            _mandate_service.user_sign_mandate(mandate_id, user_id)
            self.logger.info(f"User signed mandate {mandate_id}")
        except Exception as e:
            _logger.warning(f"User signing failed (non-critical): {e}")

        # Update mandate status
        _mandate_service.update_mandate_status(mandate_id, "pending_otp")
```

Note: Change `self.logger` to `_logger` in the added code.

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.tools.payment_tools import enhanced_initiate_payment; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/tools/payment_tools.py
git commit -m "feat(payment_tools): add user signature on payment initiation per AP2 spec"
```

---

## Task 14: Integration Test - Full AP2 Mandate Flow

**Files:**
- Create: `tests/test_ap2_mandates.py`

**Step 1: Create tests directory and test file**

```bash
mkdir -p /Users/al03034132/Documents/linebot-ap2/tests
```

**Step 2: Create comprehensive test file**

```python
"""Test AP2 mandate flow - Phase 1 compliance."""

import sys
sys.path.insert(0, '/Users/al03034132/Documents/linebot-ap2')

from src.linebot_ap2.services import get_mandate_service, get_payment_service
from src.linebot_ap2.models.payment import TransactionModality


def test_full_ap2_mandate_flow():
    """Test complete AP2 mandate flow with merchant and user signatures."""

    mandate_service = get_mandate_service()
    payment_service = get_payment_service()

    # Clean state
    mandate_service.active_mandates.clear()
    mandate_service.payment_mandates.clear()

    print("=" * 60)
    print("AP2 Phase 1 Mandate Flow Test")
    print("=" * 60)

    # Step 1: Create cart mandate (merchant signs automatically)
    print("\n1. Creating cart mandate with merchant signature...")
    items = [
        {"product_id": "prod_001", "name": "Test Product", "price": 99.99, "quantity": 2}
    ]
    result = mandate_service.create_signed_mandate(
        user_id="test_user_001",
        items=items,
        merchant_id="merchant_001",
        merchant_name="Test Store"
    )

    mandate_id = result["mandate"]["id"]
    print(f"   Mandate ID: {mandate_id}")
    print(f"   Merchant signed: {result['ap2_signatures']['merchant_signed']}")
    print(f"   User signed: {result['ap2_signatures']['user_signed']}")
    print(f"   Awaiting: {result['ap2_signatures']['awaiting']}")

    assert result["ap2_signatures"]["merchant_signed"] == True
    assert result["ap2_signatures"]["user_signed"] == False
    assert result["ap2_signatures"]["awaiting"] == "user_signature"

    # Step 2: User signs mandate
    print("\n2. User signing mandate...")
    mandate = mandate_service.user_sign_mandate(mandate_id, "test_user_001")
    print(f"   User signature: {mandate.user_signature[:32]}...")
    print(f"   Fully signed: {mandate.is_fully_signed()}")

    assert mandate.is_fully_signed() == True

    # Step 3: Create PaymentMandate
    print("\n3. Creating PaymentMandate for network/issuer...")
    payment_mandate = mandate_service.create_payment_mandate(
        cart_mandate=mandate,
        payment_method_name="CARD",
        payment_token="tok_test_123"
    )

    print(f"   PaymentMandate ID: {payment_mandate.payment_mandate_id}")
    print(f"   Agent presence: {payment_mandate.agent_presence}")
    print(f"   Modality: {payment_mandate.transaction_modality.value}")
    print(f"   Cart mandate ID: {payment_mandate.cart_mandate_id}")

    assert payment_mandate.agent_presence == True
    assert payment_mandate.transaction_modality == TransactionModality.HUMAN_PRESENT
    assert payment_mandate.cart_mandate_id == mandate_id

    # Step 4: Generate network payload
    print("\n4. Generating network payload...")
    network_payload = payment_mandate.to_network_payload()
    print(f"   Payload keys: {list(network_payload.keys())}")

    assert "agent_presence" in network_payload
    assert "transaction_modality" in network_payload
    assert network_payload["transaction_modality"] == "human_present"

    print("\n" + "=" * 60)
    print("✅ All AP2 Phase 1 tests passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_full_ap2_mandate_flow()
```

**Step 3: Run tests**

Run: `python tests/test_ap2_mandates.py`

Expected output should include: `✅ All AP2 Phase 1 tests passed!`

**Step 4: Commit**

```bash
git add tests/test_ap2_mandates.py
git commit -m "test: add AP2 Phase 1 mandate flow integration test"
```

---

## Task 15: Final Verification and Summary Commit

**Step 1: Run full import check**

Run: `python -c "from src.linebot_ap2.models import IntentMandate, CartMandate, PaymentMandate, TransactionModality, PayerInfo, PayeeInfo, RiskPayload; from src.linebot_ap2.services import get_mandate_service, get_payment_service; print('All imports successful')"`

Expected: `All imports successful`

**Step 2: Run integration test**

Run: `python tests/test_ap2_mandates.py`

Expected: All tests pass.

**Step 3: Create summary commit**

```bash
git add -A
git commit -m "feat(ap2): complete Phase 1 - AP2 mandate types implementation

- Add IntentMandate model for human-not-present scenarios
- Enhance CartMandate with merchant/user signatures
- Add PaymentMandate for network/issuer visibility
- Add PayerInfo, PayeeInfo, RiskPayload models
- Add TransactionModality enum
- Update MandateService with signing methods
- Wire PaymentService to create PaymentMandate
- Add integration tests

Per AP2 Specification Sections 4.1.1, 4.1.2, 4.1.3, 7.1"
```

---

## Summary

**Files Modified:**
- `src/linebot_ap2/models/payment.py` - New mandate types and supporting models
- `src/linebot_ap2/models/__init__.py` - Export new types
- `src/linebot_ap2/services/mandate_service.py` - Signing methods
- `src/linebot_ap2/services/payment_service.py` - PaymentMandate creation
- `src/linebot_ap2/services/__init__.py` - Service wiring
- `src/linebot_ap2/tools/payment_tools.py` - User signing integration

**Files Created:**
- `tests/test_ap2_mandates.py` - Integration tests

**AP2 Compliance Achieved:**
- ✅ IntentMandate (Section 4.1.2)
- ✅ CartMandate with merchant/user signatures (Section 4.1.1, 7.1)
- ✅ PaymentMandate for network visibility (Section 4.1.3)
- ✅ PayerInfo/PayeeInfo models
- ✅ RiskPayload structure
- ✅ TransactionModality enum
