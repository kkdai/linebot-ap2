# Credential Provider Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement AP2-compliant Credential Provider service to manage user payment credentials, select optimal payment methods, and issue payment tokens.

**Architecture:** Create a dedicated CredentialProviderService that separates credential management from payment processing. The service manages encrypted credentials, provides eligible payment methods based on transaction context, and issues one-time tokens for secure payment processing.

**Tech Stack:** Python 3.10+, Pydantic v2, cryptography (Fernet for symmetric encryption), existing service singleton pattern.

---

## Task 1: Add PaymentCredential Model

**Files:**
- Modify: `src/linebot_ap2/models/payment.py`

**Step 1: Add PaymentCredential class after PaymentMethod class**

Add after the `PaymentMethod` class (around line 37):

```python
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
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.models.payment import PaymentCredential, CredentialStatus; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/payment.py
git commit -m "feat(models): add PaymentCredential model for Credential Provider"
```

---

## Task 2: Add PaymentToken Model

**Files:**
- Modify: `src/linebot_ap2/models/payment.py`

**Step 1: Add PaymentToken class after PaymentCredential**

```python
class TokenType(str, Enum):
    """Type of payment token."""
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"
    RECURRING = "recurring"


class PaymentToken(BaseModel):
    """
    One-time payment token issued by Credential Provider.
    Binds a credential to a specific mandate for secure payment.
    """
    token_id: str
    credential_id: str
    user_id: str
    mandate_id: str

    # Token value (used by payment processor)
    token_value: str
    token_type: TokenType = TokenType.SINGLE_USE

    # Transaction binding
    amount: float
    currency: str

    # Validity
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime

    # Usage tracking
    used: bool = False
    used_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Check if token is valid for use."""
        if self.used:
            return False
        if datetime.now() > self.expires_at:
            return False
        return True

    def consume(self) -> None:
        """Mark token as used."""
        self.used = True
        self.used_at = datetime.now()
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.models.payment import PaymentToken, TokenType; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/payment.py
git commit -m "feat(models): add PaymentToken model for secure payment processing"
```

---

## Task 3: Update Models Exports

**Files:**
- Modify: `src/linebot_ap2/models/__init__.py`

**Step 1: Update imports and exports**

Add to the imports from `.payment`:
```python
from .payment import (
    # ... existing imports ...
    CredentialStatus,
    PaymentCredential,
    TokenType,
    PaymentToken,
)
```

Add to `__all__`:
```python
    # Credential Provider
    "CredentialStatus",
    "PaymentCredential",
    "TokenType",
    "PaymentToken",
```

**Step 2: Verify imports**

Run: `python -c "from src.linebot_ap2.models import PaymentCredential, PaymentToken; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/models/__init__.py
git commit -m "feat(models): export Credential Provider models"
```

---

## Task 4: Create CredentialProviderService - Core Structure

**Files:**
- Create: `src/linebot_ap2/services/credential_provider.py`

**Step 1: Create the service file with core structure**

```python
"""AP2 Credential Provider Service - Manages user payment credentials."""

import uuid
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet

from ..models.payment import (
    PaymentCredential, PaymentToken, PaymentMethodType,
    CredentialStatus, TokenType
)
from ..common.logger import setup_logger


class CredentialProviderService:
    """
    AP2 Credential Provider - Manages user payment credentials.
    Per AP2 Specification Section 3.1.

    Responsibilities:
    - Secure storage of payment credentials
    - Selection of optimal payment method
    - Issuance of payment tokens
    - Token validation and consumption
    """

    def __init__(self, encryption_key: Optional[bytes] = None):
        self.logger = setup_logger("credential_provider")

        # Encryption for sensitive data
        if encryption_key:
            self._fernet = Fernet(encryption_key)
        else:
            # Generate key for demo (in production, use secure key management)
            self._fernet = Fernet(Fernet.generate_key())

        # Storage (in production, use secure persistent storage)
        self._credentials: Dict[str, PaymentCredential] = {}  # credential_id -> credential
        self._user_credentials: Dict[str, List[str]] = {}  # user_id -> [credential_ids]
        self._tokens: Dict[str, PaymentToken] = {}  # token_id -> token

        # Initialize demo credentials
        self._init_demo_credentials()

        self.logger.info("✓ Credential Provider initialized")

    def _init_demo_credentials(self):
        """Initialize demo credentials for testing."""
        demo_users = ["demo_user", "test_user"]

        for user_id in demo_users:
            # Visa card
            self.register_credential(
                user_id=user_id,
                credential_type=PaymentMethodType.CARD,
                credential_data={
                    "card_number": "4111111111111234",
                    "exp_month": 12,
                    "exp_year": 2027,
                    "cvv": "123"
                },
                brand="Visa",
                is_default=True,
                nickname="My Visa Card"
            )

            # Mastercard
            self.register_credential(
                user_id=user_id,
                credential_type=PaymentMethodType.CARD,
                credential_data={
                    "card_number": "5555555555555678",
                    "exp_month": 8,
                    "exp_year": 2026,
                    "cvv": "456"
                },
                brand="Mastercard",
                is_default=False,
                nickname="My Mastercard"
            )

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self._fernet.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self._fernet.decrypt(encrypted_data.encode()).decode()
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.services.credential_provider import CredentialProviderService; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/credential_provider.py
git commit -m "feat(credential_provider): create service with core structure"
```

---

## Task 5: Add Credential Registration Methods

**Files:**
- Modify: `src/linebot_ap2/services/credential_provider.py`

**Step 1: Add credential management methods after _decrypt**

```python
    def register_credential(
        self,
        user_id: str,
        credential_type: PaymentMethodType,
        credential_data: Dict[str, Any],
        brand: str,
        is_default: bool = False,
        nickname: Optional[str] = None,
        supported_currencies: Optional[List[str]] = None,
        max_transaction_amount: Optional[float] = None
    ) -> PaymentCredential:
        """
        Register a new payment credential for a user.

        Args:
            user_id: User identifier
            credential_type: Type of credential (CARD, WALLET, etc.)
            credential_data: Sensitive credential data to encrypt
            brand: Brand name (Visa, Mastercard, PayPal, etc.)
            is_default: Set as default payment method
            nickname: User-friendly name
            supported_currencies: List of supported currencies
            max_transaction_amount: Maximum transaction limit

        Returns:
            Created PaymentCredential
        """
        credential_id = f"cred_{uuid.uuid4().hex[:12]}"

        # Extract last four digits for display
        if credential_type == PaymentMethodType.CARD:
            card_number = credential_data.get("card_number", "")
            last_four = card_number[-4:] if len(card_number) >= 4 else "****"
        else:
            last_four = credential_data.get("last_four", "****")

        # Encrypt sensitive data
        import json
        encrypted_data = self._encrypt(json.dumps(credential_data))

        # If setting as default, unset other defaults
        if is_default and user_id in self._user_credentials:
            for cred_id in self._user_credentials[user_id]:
                if cred_id in self._credentials:
                    self._credentials[cred_id].is_default = False

        # Create credential
        credential = PaymentCredential(
            credential_id=credential_id,
            user_id=user_id,
            type=credential_type,
            last_four=last_four,
            brand=brand,
            nickname=nickname,
            encrypted_data=encrypted_data,
            is_default=is_default,
            priority=len(self._user_credentials.get(user_id, [])),
            supported_currencies=supported_currencies or ["USD", "TWD"],
            max_transaction_amount=max_transaction_amount,
            status=CredentialStatus.ACTIVE
        )

        # Store credential
        self._credentials[credential_id] = credential

        if user_id not in self._user_credentials:
            self._user_credentials[user_id] = []
        self._user_credentials[user_id].append(credential_id)

        self.logger.info(f"✓ Credential registered: {credential_id} for user {user_id}")
        return credential

    def get_user_credentials(self, user_id: str) -> List[PaymentCredential]:
        """Get all credentials for a user."""
        credential_ids = self._user_credentials.get(user_id, [])
        return [
            self._credentials[cid]
            for cid in credential_ids
            if cid in self._credentials
        ]

    def get_credential(self, credential_id: str) -> Optional[PaymentCredential]:
        """Get a specific credential by ID."""
        return self._credentials.get(credential_id)

    def deactivate_credential(self, credential_id: str) -> bool:
        """Deactivate a credential."""
        credential = self._credentials.get(credential_id)
        if not credential:
            return False

        credential.status = CredentialStatus.SUSPENDED
        self.logger.info(f"✓ Credential deactivated: {credential_id}")
        return True
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.services.credential_provider import CredentialProviderService; cp = CredentialProviderService(); print(len(cp.get_user_credentials('demo_user')))"`

Expected: `2`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/credential_provider.py
git commit -m "feat(credential_provider): add credential registration and management"
```

---

## Task 6: Add Payment Method Selection Methods

**Files:**
- Modify: `src/linebot_ap2/services/credential_provider.py`

**Step 1: Add selection methods after deactivate_credential**

```python
    def get_eligible_methods(
        self,
        user_id: str,
        amount: float,
        currency: str,
        merchant_accepted_types: Optional[List[str]] = None
    ) -> List[PaymentCredential]:
        """
        Get payment credentials eligible for a transaction.
        Per AP2 spec: Filter based on merchant requirements and transaction context.

        Args:
            user_id: User identifier
            amount: Transaction amount
            currency: Transaction currency
            merchant_accepted_types: Payment types accepted by merchant

        Returns:
            List of eligible credentials sorted by priority
        """
        credentials = self.get_user_credentials(user_id)
        eligible = []

        for cred in credentials:
            # Check if credential supports the transaction
            if not cred.supports_transaction(amount, currency):
                continue

            # Check if merchant accepts this type
            if merchant_accepted_types:
                if cred.type.value not in merchant_accepted_types:
                    continue

            eligible.append(cred)

        # Sort by: default first, then priority (descending)
        eligible.sort(key=lambda c: (not c.is_default, -c.priority))

        self.logger.info(
            f"Found {len(eligible)} eligible methods for user {user_id} "
            f"(amount={amount} {currency})"
        )
        return eligible

    def select_optimal_method(
        self,
        user_id: str,
        amount: float,
        currency: str,
        merchant_accepted_types: Optional[List[str]] = None,
        preference_hints: Optional[Dict[str, Any]] = None
    ) -> Optional[PaymentCredential]:
        """
        Automatically select the optimal payment method.
        Per AP2 spec: Select based on user preferences and transaction context.

        Args:
            user_id: User identifier
            amount: Transaction amount
            currency: Transaction currency
            merchant_accepted_types: Payment types accepted by merchant
            preference_hints: Additional hints (e.g., {"prefer_rewards": True})

        Returns:
            Optimal credential or None if none eligible
        """
        eligible = self.get_eligible_methods(
            user_id=user_id,
            amount=amount,
            currency=currency,
            merchant_accepted_types=merchant_accepted_types
        )

        if not eligible:
            self.logger.warning(f"No eligible payment methods for user {user_id}")
            return None

        # Apply preference hints if provided
        if preference_hints:
            preferred_brand = preference_hints.get("preferred_brand")
            if preferred_brand:
                for cred in eligible:
                    if cred.brand.lower() == preferred_brand.lower():
                        self.logger.info(f"Selected {cred.credential_id} based on brand preference")
                        return cred

        # Return first eligible (already sorted by default/priority)
        selected = eligible[0]
        self.logger.info(f"Selected optimal method: {selected.credential_id}")
        return selected
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.services.credential_provider import CredentialProviderService; cp = CredentialProviderService(); m = cp.select_optimal_method('demo_user', 100, 'USD'); print(m.brand if m else 'None')"`

Expected: `Visa`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/credential_provider.py
git commit -m "feat(credential_provider): add payment method selection per AP2 spec"
```

---

## Task 7: Add Token Issuance and Validation Methods

**Files:**
- Modify: `src/linebot_ap2/services/credential_provider.py`

**Step 1: Add token methods after select_optimal_method**

```python
    def issue_payment_token(
        self,
        credential_id: str,
        mandate_id: str,
        amount: float,
        currency: str,
        expires_in_minutes: int = 30
    ) -> Optional[PaymentToken]:
        """
        Issue a one-time payment token for a transaction.
        Per AP2 spec: Token binds credential to specific mandate.

        Args:
            credential_id: Credential to tokenize
            mandate_id: Mandate this token is for
            amount: Transaction amount
            currency: Transaction currency
            expires_in_minutes: Token validity period

        Returns:
            PaymentToken or None if credential invalid
        """
        credential = self._credentials.get(credential_id)
        if not credential:
            self.logger.error(f"Credential not found: {credential_id}")
            return None

        if not credential.supports_transaction(amount, currency):
            self.logger.error(f"Credential {credential_id} does not support transaction")
            return None

        # Generate secure token
        token_id = f"tok_{uuid.uuid4().hex[:12]}"
        token_value = secrets.token_urlsafe(32)

        token = PaymentToken(
            token_id=token_id,
            credential_id=credential_id,
            user_id=credential.user_id,
            mandate_id=mandate_id,
            token_value=token_value,
            token_type=TokenType.SINGLE_USE,
            amount=amount,
            currency=currency,
            expires_at=datetime.now() + timedelta(minutes=expires_in_minutes)
        )

        # Store token
        self._tokens[token_id] = token

        self.logger.info(f"✓ Token issued: {token_id} for mandate {mandate_id}")
        return token

    def validate_token(self, token_id: str) -> bool:
        """Validate a payment token."""
        token = self._tokens.get(token_id)
        if not token:
            return False
        return token.is_valid()

    def consume_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Consume a token and return credential info for payment processing.

        Returns:
            Dict with credential info or None if token invalid
        """
        token = self._tokens.get(token_id)
        if not token:
            self.logger.error(f"Token not found: {token_id}")
            return None

        if not token.is_valid():
            self.logger.error(f"Token invalid or expired: {token_id}")
            return None

        credential = self._credentials.get(token.credential_id)
        if not credential:
            self.logger.error(f"Credential not found for token: {token_id}")
            return None

        # Mark token as used
        token.consume()

        # Decrypt credential data for payment processing
        import json
        decrypted_data = json.loads(self._decrypt(credential.encrypted_data))

        self.logger.info(f"✓ Token consumed: {token_id}")

        return {
            "credential_id": credential.credential_id,
            "type": credential.type.value,
            "brand": credential.brand,
            "last_four": credential.last_four,
            "token_id": token_id,
            "mandate_id": token.mandate_id,
            "amount": token.amount,
            "currency": token.currency,
            # Sensitive data for payment processor
            "_credential_data": decrypted_data
        }

    def get_token(self, token_id: str) -> Optional[PaymentToken]:
        """Get token by ID."""
        return self._tokens.get(token_id)
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.services.credential_provider import CredentialProviderService; cp = CredentialProviderService(); creds = cp.get_user_credentials('demo_user'); tok = cp.issue_payment_token(creds[0].credential_id, 'mandate_123', 100, 'USD'); print(tok.token_id[:4] if tok else 'None')"`

Expected: `tok_`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/credential_provider.py
git commit -m "feat(credential_provider): add token issuance and consumption"
```

---

## Task 8: Add Utility Methods

**Files:**
- Modify: `src/linebot_ap2/services/credential_provider.py`

**Step 1: Add utility methods after get_token**

```python
    def get_credential_for_display(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Get credential info safe for display (no sensitive data)."""
        credential = self._credentials.get(credential_id)
        if not credential:
            return None

        return {
            "credential_id": credential.credential_id,
            "type": credential.type.value,
            "brand": credential.brand,
            "last_four": credential.last_four,
            "nickname": credential.nickname,
            "is_default": credential.is_default,
            "status": credential.status.value,
            "supported_currencies": credential.supported_currencies,
            "max_transaction_amount": credential.max_transaction_amount
        }

    def get_user_credentials_for_display(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all user credentials safe for display."""
        credentials = self.get_user_credentials(user_id)
        return [
            self.get_credential_for_display(c.credential_id)
            for c in credentials
            if c.is_valid()
        ]

    def set_default_credential(self, user_id: str, credential_id: str) -> bool:
        """Set a credential as default for user."""
        credential = self._credentials.get(credential_id)
        if not credential or credential.user_id != user_id:
            return False

        # Unset other defaults
        for cred_id in self._user_credentials.get(user_id, []):
            if cred_id in self._credentials:
                self._credentials[cred_id].is_default = False

        # Set new default
        credential.is_default = True
        self.logger.info(f"✓ Set default credential: {credential_id} for user {user_id}")
        return True

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens. Returns count of cleaned tokens."""
        expired = [
            token_id for token_id, token in self._tokens.items()
            if not token.is_valid()
        ]

        for token_id in expired:
            del self._tokens[token_id]

        if expired:
            self.logger.info(f"Cleaned up {len(expired)} expired tokens")

        return len(expired)
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.services.credential_provider import CredentialProviderService; cp = CredentialProviderService(); display = cp.get_user_credentials_for_display('demo_user'); print(len(display))"`

Expected: `2`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/credential_provider.py
git commit -m "feat(credential_provider): add utility methods for display and cleanup"
```

---

## Task 9: Wire CredentialProvider into Services

**Files:**
- Modify: `src/linebot_ap2/services/__init__.py`

**Step 1: Update services __init__.py**

Replace entire file with:

```python
"""Business logic services for LINE Bot AP2.

This module provides shared singleton instances of services to ensure
data consistency across different agents and tools.
"""

from .mandate_service import MandateService
from .payment_service import PaymentService
from .product_service import ProductService
from .credential_provider import CredentialProviderService

# Shared singleton instances - used by all agents and tools
# This ensures mandate and payment data is shared across Shopping and Payment agents
_shared_product_service = ProductService()
_shared_mandate_service = MandateService()
_shared_payment_service = PaymentService()
_shared_credential_provider = CredentialProviderService()

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


def get_credential_provider() -> CredentialProviderService:
    """Get shared CredentialProviderService singleton instance."""
    return _shared_credential_provider


__all__ = [
    "MandateService",
    "PaymentService",
    "ProductService",
    "CredentialProviderService",
    "get_product_service",
    "get_mandate_service",
    "get_payment_service",
    "get_credential_provider",
]
```

**Step 2: Verify wiring**

Run: `python -c "from src.linebot_ap2.services import get_credential_provider; cp = get_credential_provider(); print(len(cp.get_user_credentials('demo_user')))"`

Expected: `2`

**Step 3: Commit**

```bash
git add src/linebot_ap2/services/__init__.py
git commit -m "feat(services): add CredentialProviderService singleton"
```

---

## Task 10: Add Shopping Tools for Credential Provider

**Files:**
- Modify: `src/linebot_ap2/tools/shopping_tools.py`

**Step 1: Add import for credential provider**

Add to imports at top:

```python
from ..services import get_product_service, get_mandate_service, get_credential_provider
```

Add after existing service assignments:

```python
_credential_provider = get_credential_provider()
```

**Step 2: Add new tool function at end of file**

```python
def get_eligible_payment_methods(
    user_id: str,
    amount: float,
    currency: str = "USD",
    merchant_accepted_types: str = ""
) -> str:
    """
    Get eligible payment methods for a transaction.
    Per AP2 spec: Credential Provider returns methods matching transaction context.

    Args:
        user_id: User identifier
        amount: Transaction amount
        currency: Transaction currency (default: USD)
        merchant_accepted_types: Comma-separated list of accepted types (e.g., "card,wallet")

    Returns:
        JSON string with eligible payment methods
    """
    try:
        _logger.info(f"Getting eligible payment methods for user {user_id}, amount={amount} {currency}")

        accepted_types = None
        if merchant_accepted_types:
            accepted_types = [t.strip() for t in merchant_accepted_types.split(",")]

        eligible = _credential_provider.get_eligible_methods(
            user_id=user_id,
            amount=amount,
            currency=currency,
            merchant_accepted_types=accepted_types
        )

        # Get display-safe info
        methods = []
        for cred in eligible:
            methods.append({
                "credential_id": cred.credential_id,
                "type": cred.type.value,
                "brand": cred.brand,
                "last_four": cred.last_four,
                "nickname": cred.nickname,
                "is_default": cred.is_default
            })

        response = {
            "user_id": user_id,
            "eligible_methods": methods,
            "total": len(methods),
            "transaction_context": {
                "amount": amount,
                "currency": currency
            }
        }

        if not methods:
            response["message"] = "No eligible payment methods found. Please add a payment method."

        _logger.info(f"Found {len(methods)} eligible methods")
        return json.dumps(response, default=str)

    except Exception as e:
        _logger.error(f"Get eligible methods error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get eligible methods: {str(e)}",
            "user_id": user_id,
            "eligible_methods": []
        })
```

**Step 3: Verify syntax**

Run: `python -c "from src.linebot_ap2.tools.shopping_tools import get_eligible_payment_methods; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add src/linebot_ap2/tools/shopping_tools.py
git commit -m "feat(shopping_tools): add get_eligible_payment_methods tool"
```

---

## Task 11: Add Token Issuance Tool

**Files:**
- Modify: `src/linebot_ap2/tools/shopping_tools.py`

**Step 1: Add token issuance tool after get_eligible_payment_methods**

```python
def issue_payment_token_for_mandate(
    user_id: str,
    credential_id: str,
    mandate_id: str
) -> str:
    """
    Issue a payment token for a mandate.
    Per AP2 spec: Token binds credential to specific mandate for secure payment.

    Args:
        user_id: User identifier
        credential_id: Selected payment credential
        mandate_id: Mandate to bind token to

    Returns:
        JSON string with token info
    """
    try:
        _logger.info(f"Issuing payment token: user={user_id}, credential={credential_id}, mandate={mandate_id}")

        # Get mandate to verify and get amount
        mandate = _mandate_service.get_mandate(mandate_id)
        if not mandate:
            return json.dumps({
                "error": "Mandate not found",
                "mandate_id": mandate_id
            })

        if mandate.user_id != user_id:
            return json.dumps({
                "error": "User ID mismatch",
                "mandate_id": mandate_id
            })

        # Issue token
        token = _credential_provider.issue_payment_token(
            credential_id=credential_id,
            mandate_id=mandate_id,
            amount=mandate.total_amount,
            currency=mandate.currency
        )

        if not token:
            return json.dumps({
                "error": "Failed to issue token. Credential may be invalid or does not support this transaction.",
                "credential_id": credential_id,
                "mandate_id": mandate_id
            })

        # Update mandate with token
        mandate.payment_method_token = token.token_id
        _mandate_service.active_mandates[mandate_id] = mandate

        response = {
            "token_id": token.token_id,
            "credential_id": credential_id,
            "mandate_id": mandate_id,
            "amount": token.amount,
            "currency": token.currency,
            "expires_at": token.expires_at.isoformat(),
            "status": "issued",
            "message": "Payment token issued successfully. Proceed to payment."
        }

        _logger.info(f"✓ Token issued: {token.token_id}")
        return json.dumps(response, default=str)

    except Exception as e:
        _logger.error(f"Issue token error: {str(e)}")
        return json.dumps({
            "error": f"Failed to issue token: {str(e)}",
            "credential_id": credential_id,
            "mandate_id": mandate_id
        })
```

**Step 2: Verify syntax**

Run: `python -c "from src.linebot_ap2.tools.shopping_tools import issue_payment_token_for_mandate; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add src/linebot_ap2/tools/shopping_tools.py
git commit -m "feat(shopping_tools): add issue_payment_token_for_mandate tool"
```

---

## Task 12: Update Payment Tools to Use Token

**Files:**
- Modify: `src/linebot_ap2/tools/payment_tools.py`

**Step 1: Add credential provider import**

Update imports to add:

```python
from ..services import get_payment_service, get_mandate_service, get_product_service, get_credential_provider
```

Add after existing service assignments:

```python
_credential_provider = get_credential_provider()
```

**Step 2: Add token-based payment initiation function**

Add new function after `enhanced_initiate_payment`:

```python
def initiate_payment_with_token(
    mandate_id: str,
    token_id: str,
    user_id: str
) -> str:
    """
    Initiate payment using a pre-issued token.
    Per AP2 spec: Uses token from Credential Provider for secure payment.

    Args:
        mandate_id: Cart mandate ID
        token_id: Payment token from Credential Provider
        user_id: User identifier

    Returns:
        JSON string with payment initiation details
    """
    try:
        _logger.info(f"Initiating payment with token: mandate={mandate_id}, token={token_id}")

        # Validate token
        if not _credential_provider.validate_token(token_id):
            return json.dumps({
                "error": "Invalid or expired token",
                "token_id": token_id,
                "status": "failed"
            })

        # Get token info
        token = _credential_provider.get_token(token_id)
        if not token or token.mandate_id != mandate_id:
            return json.dumps({
                "error": "Token not bound to this mandate",
                "token_id": token_id,
                "mandate_id": mandate_id,
                "status": "failed"
            })

        # Verify mandate
        if not _mandate_service.is_mandate_valid(mandate_id):
            return json.dumps({
                "error": "Invalid or expired mandate",
                "mandate_id": mandate_id,
                "status": "failed"
            })

        # Get credential info for display
        cred_display = _credential_provider.get_credential_for_display(token.credential_id)

        # Use existing payment initiation with the credential's payment method ID
        # This preserves the OTP flow
        result = _payment_service.initiate_payment(
            mandate_id=mandate_id,
            payment_method_id=token.credential_id,  # Use credential_id as payment_method_id
            user_id=user_id,
            amount=token.amount
        )

        # User signs the mandate when initiating payment (AP2 Spec Step 21)
        try:
            _mandate_service.user_sign_mandate(mandate_id, user_id)
            _logger.info(f"User signed mandate {mandate_id}")
        except Exception as e:
            _logger.warning(f"User signing failed (non-critical): {e}")

        # Update mandate status
        _mandate_service.update_mandate_status(mandate_id, "pending_otp")

        # Add token and credential info to result
        result["token_info"] = {
            "token_id": token_id,
            "credential": cred_display
        }

        _logger.info(f"Payment initiated with token: {token_id}")
        return json.dumps(result, default=str)

    except Exception as e:
        _logger.error(f"Token payment error: {str(e)}")
        return json.dumps({
            "error": f"Payment initiation failed: {str(e)}",
            "mandate_id": mandate_id,
            "status": "failed"
        })
```

**Step 3: Verify syntax**

Run: `python -c "from src.linebot_ap2.tools.payment_tools import initiate_payment_with_token; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add src/linebot_ap2/tools/payment_tools.py
git commit -m "feat(payment_tools): add initiate_payment_with_token for AP2 token flow"
```

---

## Task 13: Create Integration Test

**Files:**
- Create: `tests/test_credential_provider.py`

**Step 1: Create test file**

```python
"""Test Credential Provider - Phase 2 AP2 compliance."""

import sys
sys.path.insert(0, '/Users/al03034132/Documents/linebot-ap2')

from src.linebot_ap2.services import get_credential_provider, get_mandate_service


def test_credential_provider_flow():
    """Test complete Credential Provider flow."""

    cp = get_credential_provider()
    mandate_service = get_mandate_service()

    # Clean state
    mandate_service.active_mandates.clear()

    print("=" * 60)
    print("AP2 Phase 2: Credential Provider Test")
    print("=" * 60)

    # Step 1: Get user credentials
    print("\n1. Getting user credentials...")
    credentials = cp.get_user_credentials("demo_user")
    print(f"   Found {len(credentials)} credentials")
    for cred in credentials:
        print(f"   - {cred.brand} ****{cred.last_four} (default: {cred.is_default})")

    assert len(credentials) >= 2

    # Step 2: Get eligible methods for transaction
    print("\n2. Getting eligible methods for $150 USD...")
    eligible = cp.get_eligible_methods(
        user_id="demo_user",
        amount=150.0,
        currency="USD"
    )
    print(f"   Found {len(eligible)} eligible methods")

    assert len(eligible) >= 1

    # Step 3: Select optimal method
    print("\n3. Selecting optimal payment method...")
    optimal = cp.select_optimal_method(
        user_id="demo_user",
        amount=150.0,
        currency="USD"
    )
    print(f"   Selected: {optimal.brand} ****{optimal.last_four}")

    assert optimal is not None
    assert optimal.is_default == True

    # Step 4: Create a mandate
    print("\n4. Creating cart mandate...")
    mandate_result = mandate_service.create_signed_mandate(
        user_id="demo_user",
        items=[{"product_id": "prod_001", "name": "Test Item", "price": 150.0}]
    )
    mandate_id = mandate_result["mandate"]["id"]
    print(f"   Mandate ID: {mandate_id}")

    # Step 5: Issue payment token
    print("\n5. Issuing payment token...")
    token = cp.issue_payment_token(
        credential_id=optimal.credential_id,
        mandate_id=mandate_id,
        amount=150.0,
        currency="USD"
    )
    print(f"   Token ID: {token.token_id}")
    print(f"   Expires: {token.expires_at.isoformat()}")

    assert token is not None
    assert token.mandate_id == mandate_id

    # Step 6: Validate token
    print("\n6. Validating token...")
    is_valid = cp.validate_token(token.token_id)
    print(f"   Valid: {is_valid}")

    assert is_valid == True

    # Step 7: Consume token
    print("\n7. Consuming token for payment...")
    consumed = cp.consume_token(token.token_id)
    print(f"   Credential: {consumed['brand']} ****{consumed['last_four']}")
    print(f"   Amount: {consumed['amount']} {consumed['currency']}")

    assert consumed is not None
    assert "_credential_data" in consumed

    # Step 8: Verify token is now invalid
    print("\n8. Verifying token is consumed...")
    is_still_valid = cp.validate_token(token.token_id)
    print(f"   Still valid: {is_still_valid}")

    assert is_still_valid == False

    print("\n" + "=" * 60)
    print("✅ All Credential Provider tests passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_credential_provider_flow()
```

**Step 2: Run test**

Run: `python tests/test_credential_provider.py`

Expected: `✅ All Credential Provider tests passed!`

**Step 3: Commit**

```bash
git add tests/test_credential_provider.py
git commit -m "test: add Credential Provider integration test"
```

---

## Task 14: Final Verification

**Step 1: Run all imports check**

Run: `python -c "from src.linebot_ap2.models import PaymentCredential, PaymentToken; from src.linebot_ap2.services import get_credential_provider; from src.linebot_ap2.tools.shopping_tools import get_eligible_payment_methods, issue_payment_token_for_mandate; print('All imports OK')"`

Expected: `All imports OK`

**Step 2: Run integration test**

Run: `python tests/test_credential_provider.py`

Expected: All tests pass.

**Step 3: Run AP2 Phase 1 test to ensure no regression**

Run: `python tests/test_ap2_mandates.py`

Expected: All tests pass.

**Step 4: Commit summary (if needed)**

```bash
git status
```

If clean, no additional commit needed.

---

## Summary

**Files Created:**
- `src/linebot_ap2/services/credential_provider.py` - CredentialProviderService

**Files Modified:**
- `src/linebot_ap2/models/payment.py` - PaymentCredential, PaymentToken models
- `src/linebot_ap2/models/__init__.py` - Export new models
- `src/linebot_ap2/services/__init__.py` - Add CP singleton
- `src/linebot_ap2/tools/shopping_tools.py` - get_eligible_payment_methods, issue_payment_token_for_mandate
- `src/linebot_ap2/tools/payment_tools.py` - initiate_payment_with_token

**Tests Created:**
- `tests/test_credential_provider.py` - Integration test

**AP2 Compliance:**
- ✅ Credential Provider role (Section 3.1)
- ✅ Secure credential storage with encryption
- ✅ Payment method selection based on transaction context
- ✅ Token issuance bound to mandate
- ✅ Token consumption for payment processing
