"""AP2 Credential Provider Service - Manages user payment credentials."""

import json
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
