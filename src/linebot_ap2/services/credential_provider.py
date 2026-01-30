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
        # TODO: Uncomment in Task 5 after register_credential is implemented
        # self._init_demo_credentials()

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
