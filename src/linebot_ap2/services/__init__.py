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
