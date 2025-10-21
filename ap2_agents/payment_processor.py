"""
Payment Processor Agent for AP2 integration
Handles secure payment processing with OTP verification
"""

import json
import uuid
import random
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta


# Mock payment methods for demo
DEMO_PAYMENT_METHODS = [
    {
        "id": "card_001",
        "type": "card",
        "last_four": "1234",
        "brand": "Visa",
        "exp_month": 12,
        "exp_year": 2027,
        "is_default": True
    },
    {
        "id": "card_002", 
        "type": "card",
        "last_four": "5678",
        "brand": "Mastercard",
        "exp_month": 8,
        "exp_year": 2026,
        "is_default": False
    }
]

# Store for OTP verification (in production, use secure storage)
_otp_store = {}


def get_user_payment_methods(user_id: str) -> str:
    """
    Get available payment methods for a user
    
    Args:
        user_id: User identifier
        
    Returns:
        JSON string with payment methods
    """
    return json.dumps({
        "user_id": user_id,
        "payment_methods": DEMO_PAYMENT_METHODS,
        "total": len(DEMO_PAYMENT_METHODS)
    })


def initiate_payment(mandate_id: str, payment_method_id: str, user_id: str) -> str:
    """
    Initiate payment processing with OTP challenge
    
    Args:
        mandate_id: Cart mandate ID
        payment_method_id: Selected payment method
        user_id: User identifier
        
    Returns:
        JSON string with payment initiation details
    """
    # Generate OTP
    otp = f"{random.randint(100000, 999999)}"
    
    # Store OTP with expiration (5 minutes)
    _otp_store[mandate_id] = {
        "otp": otp,
        "user_id": user_id,
        "payment_method_id": payment_method_id,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "attempts": 0
    }
    
    # Find payment method details
    payment_method = None
    for pm in DEMO_PAYMENT_METHODS:
        if pm["id"] == payment_method_id:
            payment_method = pm
            break
    
    return json.dumps({
        "mandate_id": mandate_id,
        "payment_method": payment_method,
        "otp_required": True,
        "otp_sent_to": f"***-***-{random.randint(1000, 9999)}",  # Mock phone number
        "expires_in": 300,  # 5 minutes in seconds
        "status": "pending_otp"
    })


def verify_otp(mandate_id: str, otp_code: str, user_id: str) -> str:
    """
    Verify OTP code for payment authorization
    
    Args:
        mandate_id: Cart mandate ID
        otp_code: OTP code entered by user
        user_id: User identifier
        
    Returns:
        JSON string with verification result
    """
    if mandate_id not in _otp_store:
        return json.dumps({
            "error": "Invalid mandate or OTP expired",
            "status": "failed"
        })
    
    otp_data = _otp_store[mandate_id]
    
    # Check expiration
    if datetime.now() > otp_data["expires_at"]:
        del _otp_store[mandate_id]
        return json.dumps({
            "error": "OTP expired",
            "status": "expired"
        })
    
    # Check user
    if otp_data["user_id"] != user_id:
        return json.dumps({
            "error": "Invalid user",
            "status": "failed"
        })
    
    # Check attempts
    otp_data["attempts"] += 1
    if otp_data["attempts"] > 3:
        del _otp_store[mandate_id]
        return json.dumps({
            "error": "Too many attempts",
            "status": "blocked"
        })
    
    # Verify OTP
    if otp_data["otp"] == otp_code:
        # OTP verified, process payment
        del _otp_store[mandate_id]
        
        # Generate transaction ID
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        
        return json.dumps({
            "mandate_id": mandate_id,
            "transaction_id": transaction_id,
            "status": "payment_successful",
            "processed_at": datetime.now().isoformat()
        })
    else:
        return json.dumps({
            "error": f"Invalid OTP. {3 - otp_data['attempts']} attempts remaining",
            "status": "invalid_otp"
        })


def process_refund(transaction_id: str, amount: float, reason: str = "") -> str:
    """
    Process refund for a transaction
    
    Args:
        transaction_id: Original transaction ID
        amount: Refund amount
        reason: Reason for refund
        
    Returns:
        JSON string with refund details
    """
    refund_id = f"rfnd_{uuid.uuid4().hex[:12]}"
    
    return json.dumps({
        "refund_id": refund_id,
        "transaction_id": transaction_id,
        "amount": amount,
        "reason": reason,
        "status": "refund_processed",
        "processed_at": datetime.now().isoformat(),
        "estimated_arrival": "3-5 business days"
    })


def get_transaction_status(transaction_id: str) -> str:
    """
    Get status of a transaction
    
    Args:
        transaction_id: Transaction identifier
        
    Returns:
        JSON string with transaction status
    """
    # Mock transaction status
    return json.dumps({
        "transaction_id": transaction_id,
        "status": "completed",
        "amount": 999.00,
        "currency": "USD",
        "processed_at": datetime.now().isoformat(),
        "payment_method": "Visa ending in 1234"
    })


def create_payment_mandate(mandate_details: str) -> str:
    """
    Create a signed payment mandate for AP2 protocol
    
    Args:
        mandate_details: JSON string with mandate information
        
    Returns:
        JSON string with signed mandate
    """
    try:
        details = json.loads(mandate_details)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid mandate details"})
    
    # Create signed mandate (simplified for demo)
    signed_mandate = {
        "mandate_id": details.get("mandate_id", f"mandate_{uuid.uuid4().hex[:8]}"),
        "type": "payment_mandate",
        "amount": details.get("amount", 0),
        "currency": details.get("currency", "USD"),
        "merchant_id": details.get("merchant_id", "demo_merchant"),
        "user_signature_required": True,
        "created_at": datetime.now().isoformat(),
        "signature": f"sig_{uuid.uuid4().hex[:16]}",  # Mock signature
        "status": "pending_user_approval"
    }
    
    return json.dumps(signed_mandate)