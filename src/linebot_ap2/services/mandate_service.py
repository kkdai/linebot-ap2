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


@dataclass
class MandateSignature:
    """AP2 mandate signature data."""
    mandate_id: str
    signature: str
    algorithm: str
    timestamp: str
    nonce: str


class MandateService:
    """Enhanced mandate service following AP2 standards."""

    def __init__(self, secret_key: str = "demo_secret_key"):
        self.secret_key = secret_key
        self.active_mandates: Dict[str, CartMandate] = {}
        self.mandate_signatures: Dict[str, MandateSignature] = {}
        self.logger = setup_logger("mandate_service")
    
    def create_cart_mandate(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        currency: str = "USD",
        expires_in_minutes: int = 30
    ) -> CartMandate:
        """Create a new cart mandate with AP2 compliance."""

        mandate_id = f"mandate_{uuid.uuid4().hex[:12]}"

        # Convert items to CartItem objects
        cart_items = []
        total_amount = 0.0

        for item_data in items:
            cart_item = CartItem(
                product_id=item_data["product_id"],
                name=item_data["name"],
                price=float(item_data["price"]),
                quantity=int(item_data.get("quantity", 1)),
                subtotal=float(item_data["price"]) * int(item_data.get("quantity", 1))
            )
            cart_items.append(cart_item)
            total_amount += cart_item.subtotal

        # Get current time
        now = datetime.now()
        expires_at = now + timedelta(minutes=expires_in_minutes)

        self.logger.info(
            f"Creating mandate {mandate_id}: "
            f"user={user_id}, items={len(cart_items)}, total=${total_amount:.2f}, "
            f"created_at={now.isoformat()}, expires_at={expires_at.isoformat()}, "
            f"expires_in_minutes={expires_in_minutes}"
        )

        # Create mandate
        mandate = CartMandate(
            mandate_id=mandate_id,
            user_id=user_id,
            items=cart_items,
            total_amount=total_amount,
            currency=currency,
            created_at=now,
            expires_at=expires_at,
            status=PaymentStatus.PENDING
        )

        # Store mandate
        self.active_mandates[mandate_id] = mandate

        self.logger.info(f"✓ Mandate {mandate_id} created and stored successfully")

        return mandate
    
    def sign_mandate(self, mandate: CartMandate) -> MandateSignature:
        """Create AP2-compliant mandate signature."""

        self.logger.info(f"Signing mandate: {mandate.mandate_id}")

        # Create signature payload
        nonce = uuid.uuid4().hex[:16]
        timestamp = datetime.now().isoformat()
        
        payload = {
            "mandate_id": mandate.mandate_id,
            "user_id": mandate.user_id,
            "total_amount": mandate.total_amount,
            "currency": mandate.currency,
            "items_count": len(mandate.items),
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Create signature
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Create signature object
        mandate_signature = MandateSignature(
            mandate_id=mandate.mandate_id,
            signature=signature,
            algorithm="HMAC-SHA256",
            timestamp=timestamp,
            nonce=nonce
        )
        
        # Store signature
        self.mandate_signatures[mandate.mandate_id] = mandate_signature

        self.logger.info(
            f"✓ Mandate {mandate.mandate_id} signed successfully with {mandate_signature.algorithm}"
        )

        return mandate_signature

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

    def verify_mandate_signature(
        self, 
        mandate_id: str, 
        provided_signature: str
    ) -> bool:
        """Verify mandate signature."""
        
        if mandate_id not in self.mandate_signatures:
            return False
        
        stored_signature = self.mandate_signatures[mandate_id]
        return hmac.compare_digest(stored_signature.signature, provided_signature)
    
    def get_mandate(self, mandate_id: str) -> Optional[CartMandate]:
        """Get mandate by ID."""
        return self.active_mandates.get(mandate_id)
    
    def update_mandate_status(
        self, 
        mandate_id: str, 
        status: PaymentStatus
    ) -> bool:
        """Update mandate status."""
        
        if mandate_id in self.active_mandates:
            self.active_mandates[mandate_id].status = status
            return True
        return False
    
    def is_mandate_valid(self, mandate_id: str) -> bool:
        """Check if mandate is valid and not expired."""

        self.logger.debug(f"Validating mandate: {mandate_id}")

        mandate = self.get_mandate(mandate_id)
        if not mandate:
            self.logger.warning(f"❌ Mandate {mandate_id} not found")
            return False

        # Log current time and expiration
        now = datetime.now()
        self.logger.info(
            f"Mandate {mandate_id} validation check: "
            f"current_time={now.isoformat()}, "
            f"expires_at={mandate.expires_at.isoformat() if mandate.expires_at else 'None'}, "
            f"status={mandate.status.value}"
        )

        # Check expiration
        if mandate.is_expired():
            time_diff = (now - mandate.expires_at).total_seconds() if mandate.expires_at else 0
            self.logger.warning(
                f"❌ Mandate {mandate_id} is EXPIRED! "
                f"Expired {time_diff:.2f} seconds ago. "
                f"expires_at={mandate.expires_at.isoformat() if mandate.expires_at else 'None'}"
            )
            self.update_mandate_status(mandate_id, PaymentStatus.EXPIRED)
            return False

        # Calculate remaining time
        if mandate.expires_at:
            remaining_seconds = (mandate.expires_at - now).total_seconds()
            self.logger.info(
                f"✓ Mandate {mandate_id} is valid. "
                f"Remaining time: {remaining_seconds:.2f} seconds ({remaining_seconds/60:.2f} minutes)"
            )

        # Check status
        is_valid = mandate.status in [PaymentStatus.PENDING, PaymentStatus.PENDING_OTP]
        if is_valid:
            self.logger.info(f"✓ Mandate {mandate_id} status is valid: {mandate.status.value}")
        else:
            self.logger.warning(f"❌ Mandate {mandate_id} status is invalid: {mandate.status.value}")

        return is_valid
    
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
                ]
            },
            "signature": {
                "signature": signature.signature if signature else None,
                "algorithm": signature.algorithm if signature else None,
                "timestamp": signature.timestamp if signature else None,
                "nonce": signature.nonce if signature else None
            } if signature else None,
            "ap2_compliance": {
                "version": "1.0",
                "signed": signature is not None,
                "valid": self.is_mandate_valid(mandate_id),
                "verification_method": "HMAC-SHA256"
            }
        }
    
    def create_signed_mandate(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        currency: str = "USD",
        expires_in_minutes: int = 30
    ) -> Dict[str, Any]:
        """Create and sign mandate in one operation."""
        
        # Create mandate
        mandate = self.create_cart_mandate(
            user_id=user_id,
            items=items,
            currency=currency,
            expires_in_minutes=expires_in_minutes
        )
        
        # Sign mandate
        signature = self.sign_mandate(mandate)
        
        # Return detailed mandate info
        return self.get_mandate_details(mandate.mandate_id)
    
    def cleanup_expired_mandates(self) -> int:
        """Clean up expired mandates. Returns count of cleaned mandates."""
        
        expired_mandates = []
        
        for mandate_id, mandate in self.active_mandates.items():
            if mandate.is_expired():
                expired_mandates.append(mandate_id)
        
        # Remove expired mandates
        for mandate_id in expired_mandates:
            del self.active_mandates[mandate_id]
            if mandate_id in self.mandate_signatures:
                del self.mandate_signatures[mandate_id]
        
        return len(expired_mandates)
    
    def get_user_mandates(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active mandates for a user."""
        
        user_mandates = []
        
        for mandate in self.active_mandates.values():
            if mandate.user_id == user_id and self.is_mandate_valid(mandate.mandate_id):
                user_mandates.append(self.get_mandate_details(mandate.mandate_id))
        
        return user_mandates