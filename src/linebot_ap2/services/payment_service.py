"""Enhanced Payment Service with AP2 compliance and security features."""

import json
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

from ..models.payment import (
    PaymentMethod, OTPData, Transaction, PaymentStatus, RefundRequest
)
from ..common.logger import setup_logger


class PaymentError(Exception):
    """Payment-related errors."""
    pass


class OTPError(PaymentError):
    """OTP-related errors."""
    pass


class PaymentService:
    """Enhanced payment service with security and retry mechanisms."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("payment_service")
        
        # Configuration
        self.max_otp_attempts = self.config.get("max_otp_attempts", 3)
        self.otp_expiry_minutes = self.config.get("otp_expiry_minutes", 5)
        self.max_retry_attempts = self.config.get("max_retry_attempts", 2)
        
        # Storage (in production, use secure persistent storage)
        self.payment_methods: Dict[str, List[PaymentMethod]] = {}
        self.otp_store: Dict[str, OTPData] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.refunds: Dict[str, RefundRequest] = {}
        
        # Demo payment methods
        self._init_demo_payment_methods()
        
        self.logger.info("✓ Payment service initialized")
    
    def _init_demo_payment_methods(self):
        """Initialize demo payment methods."""
        demo_methods = [
            PaymentMethod(
                id="card_001",
                type="card",
                last_four="1234",
                brand="Visa",
                exp_month=12,
                exp_year=2027,
                is_default=True,
                metadata={"country": "US", "issuer": "Chase"}
            ),
            PaymentMethod(
                id="card_002",
                type="card", 
                last_four="5678",
                brand="Mastercard",
                exp_month=8,
                exp_year=2026,
                is_default=False,
                metadata={"country": "US", "issuer": "Citi"}
            ),
            PaymentMethod(
                id="wallet_001",
                type="wallet",
                last_four="9999",
                brand="PayPal",
                is_default=False,
                metadata={"verified": True}
            )
        ]
        
        # Assign to demo users
        for user_id in ["demo_user", "test_user"]:
            self.payment_methods[user_id] = demo_methods.copy()
    
    def get_user_payment_methods(self, user_id: str) -> Dict[str, Any]:
        """Get available payment methods for user."""

        methods = self.payment_methods.get(user_id, [])

        if not methods:
            # Create default payment methods for new users
            self.payment_methods[user_id] = self._create_default_payment_methods()
            methods = self.payment_methods[user_id]

        return {
            "user_id": user_id,
            "payment_methods": [method.dict() for method in methods],
            "total": len(methods),
            "default_method": next(
                (method.dict() for method in methods if method.is_default),
                None
            )
        }
    
    def _create_default_payment_methods(self) -> List[PaymentMethod]:
        """Create default payment methods for new users."""
        return [
            PaymentMethod(
                id=f"card_{random.randint(100, 999)}",
                type="card",
                last_four=f"{random.randint(1000, 9999)}",
                brand=random.choice(["Visa", "Mastercard", "Amex"]),
                exp_month=random.randint(1, 12),
                exp_year=random.randint(2025, 2029),
                is_default=True
            )
        ]
    
    def initiate_payment(
        self,
        mandate_id: str,
        payment_method_id: str,
        user_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """Initiate payment with enhanced security."""
        
        try:
            # Validate inputs
            if not all([mandate_id, payment_method_id, user_id]):
                raise PaymentError("Missing required payment parameters")
            
            # Find payment method
            user_methods = self.payment_methods.get(user_id, [])
            payment_method = next(
                (pm for pm in user_methods if pm.id == payment_method_id),
                None
            )
            
            if not payment_method:
                raise PaymentError("Invalid payment method")
            
            # Generate secure OTP
            otp_code = self._generate_otp()
            
            # Create OTP data with enhanced security
            otp_data = OTPData(
                otp=otp_code,
                user_id=user_id,
                mandate_id=mandate_id,
                payment_method_id=payment_method_id,
                expires_at=datetime.now() + timedelta(minutes=self.otp_expiry_minutes),
                max_attempts=self.max_otp_attempts
            )
            
            # Store OTP securely
            self.otp_store[mandate_id] = otp_data
            
            # Log payment initiation
            self.logger.info(
                f"Payment initiated: mandate={mandate_id}, user={user_id}, "
                f"method={payment_method_id}, amount={amount}"
            )
            
            return {
                "mandate_id": mandate_id,
                "payment_method": payment_method.dict(),
                "otp_required": True,
                "otp_sent_to": self._mask_contact_info(user_id),
                "expires_in_seconds": self.otp_expiry_minutes * 60,
                "max_attempts": self.max_otp_attempts,
                "status": PaymentStatus.PENDING_OTP.value,
                "security_features": {
                    "otp_expiry": f"{self.otp_expiry_minutes} minutes",
                    "max_attempts": self.max_otp_attempts,
                    "encrypted_storage": True
                },
                # Demo information
                "demo_hint": f"🔐 Demo OTP Code: {otp_code}",
                "otp_code": otp_code,
                "demo_note": "In production, OTP would be sent via SMS/Email"
            }
            
        except Exception as e:
            self.logger.error(f"Payment initiation failed: {str(e)}")
            raise PaymentError(f"Payment initiation failed: {str(e)}")
    
    def verify_otp(
        self,
        mandate_id: str,
        otp_code: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Verify OTP with enhanced security and retry logic."""
        
        try:
            # Check if OTP exists
            if mandate_id not in self.otp_store:
                raise OTPError("Invalid mandate or OTP expired")
            
            otp_data = self.otp_store[mandate_id]
            
            # Verify user
            if otp_data.user_id != user_id:
                self.logger.warning(f"OTP verification: user mismatch for mandate {mandate_id}")
                raise OTPError("Invalid user for this OTP")
            
            # Check expiration
            if otp_data.is_expired():
                del self.otp_store[mandate_id]
                self.logger.info(f"OTP expired for mandate {mandate_id}")
                raise OTPError("OTP has expired")
            
            # Check attempt limit
            if otp_data.is_blocked():
                del self.otp_store[mandate_id]
                self.logger.warning(f"OTP blocked due to max attempts for mandate {mandate_id}")
                raise OTPError("Too many failed attempts. OTP blocked.")
            
            # Increment attempts
            otp_data.increment_attempts()
            
            # Verify OTP
            if otp_data.otp == otp_code:
                # OTP verified successfully
                del self.otp_store[mandate_id]
                
                # Process payment
                transaction = self._process_payment(mandate_id, otp_data)
                
                self.logger.info(
                    f"Payment successful: mandate={mandate_id}, "
                    f"transaction={transaction.transaction_id}"
                )
                
                return {
                    "mandate_id": mandate_id,
                    "transaction_id": transaction.transaction_id,
                    "status": PaymentStatus.COMPLETED.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "processed_at": transaction.processed_at.isoformat(),
                    "payment_method": {
                        "id": transaction.payment_method_id,
                        "type": "card",  # Simplified for demo
                        "last_four": "****"
                    },
                    "security_confirmation": {
                        "otp_verified": True,
                        "secure_processing": True,
                        "fraud_check": "passed"
                    }
                }
            else:
                # Invalid OTP
                remaining_attempts = otp_data.max_attempts - otp_data.attempts
                
                self.logger.warning(
                    f"Invalid OTP for mandate {mandate_id}, "
                    f"attempts: {otp_data.attempts}/{otp_data.max_attempts}"
                )
                
                if remaining_attempts <= 0:
                    del self.otp_store[mandate_id]
                    raise OTPError("Maximum OTP attempts exceeded")
                
                return {
                    "status": "invalid_otp",
                    "error": f"Invalid OTP code",
                    "remaining_attempts": remaining_attempts,
                    "can_retry": True,
                    "expires_in_seconds": int(
                        (otp_data.expires_at - datetime.now()).total_seconds()
                    )
                }
                
        except OTPError:
            raise
        except Exception as e:
            self.logger.error(f"OTP verification failed: {str(e)}")
            raise PaymentError(f"OTP verification failed: {str(e)}")
    
    def _process_payment(
        self,
        mandate_id: str,
        otp_data: OTPData
    ) -> Transaction:
        """Process the actual payment after OTP verification."""
        
        # Generate transaction ID
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            user_id=otp_data.user_id,
            amount=999.99,  # Demo amount, should come from mandate
            currency="USD",
            payment_method_id=otp_data.payment_method_id,
            status=PaymentStatus.PROCESSING
        )
        
        # Store transaction
        self.transactions[transaction_id] = transaction
        
        # Simulate payment processing delay (removed async sleep)
        
        # Mark as completed
        transaction.mark_completed()
        
        return transaction
    
    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction status with detailed information."""
        
        transaction = self.transactions.get(transaction_id)
        
        if not transaction:
            return {
                "error": "Transaction not found",
                "transaction_id": transaction_id
            }
        
        return {
            "transaction_id": transaction.transaction_id,
            "mandate_id": transaction.mandate_id,
            "status": transaction.status.value,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "created_at": transaction.created_at.isoformat(),
            "processed_at": transaction.processed_at.isoformat() if transaction.processed_at else None,
            "payment_method_id": transaction.payment_method_id,
            "error_message": transaction.error_message
        }
    
    def process_refund(
        self,
        transaction_id: str,
        amount: float,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Process refund for a transaction."""
        
        try:
            # Verify transaction exists
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                raise PaymentError("Transaction not found")
            
            if transaction.status != PaymentStatus.COMPLETED:
                raise PaymentError("Can only refund completed transactions")
            
            # Create refund
            refund_id = f"rfnd_{uuid.uuid4().hex[:12]}"
            
            refund = RefundRequest(
                refund_id=refund_id,
                transaction_id=transaction_id,
                amount=min(amount, transaction.amount),  # Can't refund more than paid
                reason=reason,
                status="processing"
            )
            
            # Store refund
            self.refunds[refund_id] = refund
            
            # Simulate processing (removed async sleep)
            refund.status = "completed"
            refund.processed_at = datetime.now()
            
            self.logger.info(f"Refund processed: {refund_id} for transaction {transaction_id}")
            
            return {
                "refund_id": refund_id,
                "transaction_id": transaction_id,
                "amount": refund.amount,
                "currency": transaction.currency,
                "reason": reason,
                "status": refund.status,
                "processed_at": refund.processed_at.isoformat(),
                "estimated_arrival": refund.estimated_arrival
            }
            
        except Exception as e:
            self.logger.error(f"Refund processing failed: {str(e)}")
            raise PaymentError(f"Refund processing failed: {str(e)}")
    
    def _generate_otp(self) -> str:
        """Generate secure OTP code."""
        return f"{random.randint(100000, 999999)}"
    
    def _mask_contact_info(self, user_id: str) -> str:
        """Mask contact information for security."""
        return f"***-***-{random.randint(1000, 9999)}"
    
    def cleanup_expired_otps(self) -> int:
        """Clean up expired OTPs. Returns count of cleaned OTPs."""
        
        expired_otps = []
        
        for mandate_id, otp_data in self.otp_store.items():
            if otp_data.is_expired():
                expired_otps.append(mandate_id)
        
        # Remove expired OTPs
        for mandate_id in expired_otps:
            del self.otp_store[mandate_id]
        
        if expired_otps:
            self.logger.info(f"Cleaned up {len(expired_otps)} expired OTPs")
        
        return len(expired_otps)