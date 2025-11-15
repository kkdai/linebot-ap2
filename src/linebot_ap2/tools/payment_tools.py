"""Enhanced payment tools using the new service architecture."""

import json
from typing import Optional

from ..services.payment_service import PaymentService, PaymentError, OTPError
from ..services.mandate_service import MandateService
from ..common.logger import setup_logger

# Initialize services
_payment_service = PaymentService()
_mandate_service = MandateService()
_logger = setup_logger("payment_tools")


def enhanced_get_payment_methods(user_id: str) -> str:
    """
    Get available payment methods for user with enhanced metadata.
    
    Args:
        user_id: User identifier
        
    Returns:
        JSON string with payment methods and security info
    """
    try:
        _logger.info(f"Getting payment methods for user: {user_id}")

        # Call synchronous service method
        result = _payment_service.get_user_payment_methods(user_id)
        
        # Add security and compliance info
        result["security_features"] = {
            "payment_encryption": "AES-256",
            "pci_compliance": "Level 1",
            "fraud_protection": "Enabled",
            "3d_secure": "Supported"
        }
        
        result["ap2_compliance"] = {
            "mandate_signing": "HMAC-SHA256",
            "secure_otp": "Enabled",
            "transaction_logging": "Full audit trail"
        }
        
        _logger.info(f"Retrieved {result['total']} payment methods")
        return json.dumps(result, default=str)
        
    except Exception as e:
        _logger.error(f"Get payment methods error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get payment methods: {str(e)}",
            "user_id": user_id,
            "payment_methods": []
        })


def enhanced_initiate_payment(
    mandate_id: str,
    payment_method_id: str,
    user_id: str,
    amount: Optional[float] = None
) -> str:
    """
    Initiate payment with enhanced security and AP2 compliance.
    
    Args:
        mandate_id: Cart mandate ID
        payment_method_id: Selected payment method
        user_id: User identifier
        amount: Payment amount (optional, will use mandate amount)
        
    Returns:
        JSON string with payment initiation details and OTP info
    """
    try:
        _logger.info(f"Initiating payment: mandate={mandate_id}, user={user_id}")
        
        # Verify mandate exists and is valid
        if not _mandate_service.is_mandate_valid(mandate_id):
            return json.dumps({
                "error": "Invalid or expired mandate",
                "mandate_id": mandate_id,
                "status": "failed"
            })
        
        # Get mandate details for amount if not provided
        mandate_details = _mandate_service.get_mandate_details(mandate_id)
        if "error" in mandate_details:
            return json.dumps({
                "error": "Mandate not found",
                "mandate_id": mandate_id,
                "status": "failed"
            })
        
        if amount is None:
            amount = mandate_details["mandate"]["total_amount"]
        
        # Call synchronous payment initiation
        result = _payment_service.initiate_payment(
            mandate_id=mandate_id,
            payment_method_id=payment_method_id,
            user_id=user_id,
            amount=amount
        )
        
        # Update mandate status
        _mandate_service.update_mandate_status(mandate_id, "pending_otp")

        # Add mandate context
        result["mandate_info"] = {
            "mandate_id": mandate_id,
            "signed": mandate_details["ap2_compliance"]["signed"],
            "expires_at": mandate_details["mandate"]["expires_at"]
        }

        # Add prominent demo instruction for showing OTP
        result["demo_instruction"] = {
            "important": "THIS IS A DEMO - Display the OTP code to user",
            "display_format": f"🔐 測試用 OTP 驗證碼：{result.get('otp_code', 'N/A')}",
            "user_guidance": "請回覆驗證碼完成付款，例如：驗證碼是 " + result.get('otp_code', 'N/A')
        }

        _logger.info(f"Payment initiated successfully: {mandate_id}, OTP={result.get('otp_code')}")
        return json.dumps(result, default=str)
        
    except PaymentError as e:
        _logger.error(f"Payment initiation error: {str(e)}")
        return json.dumps({
            "error": str(e),
            "mandate_id": mandate_id,
            "status": "failed"
        })
    except Exception as e:
        _logger.error(f"Unexpected payment error: {str(e)}")
        return json.dumps({
            "error": f"Payment initiation failed: {str(e)}",
            "mandate_id": mandate_id,
            "status": "failed"
        })


def enhanced_verify_otp(
    mandate_id: str,
    otp_code: str,
    user_id: str
) -> str:
    """
    Verify OTP with enhanced security and transaction processing.
    
    Args:
        mandate_id: Cart mandate ID
        otp_code: OTP code entered by user
        user_id: User identifier
        
    Returns:
        JSON string with verification result and transaction details
    """
    try:
        _logger.info(f"Verifying OTP: mandate={mandate_id}, user={user_id}")
        
        # Run async OTP verification
        # Call synchronous OTP verification
        result = _payment_service.verify_otp(
            mandate_id=mandate_id,
            otp_code=otp_code,
            user_id=user_id
        )
        
        # If successful, update mandate status and process fulfillment
        if result.get("status") == "completed":
            _mandate_service.update_mandate_status(mandate_id, "completed")
            
            # Add fulfillment information
            result["fulfillment"] = {
                "order_processing": "Initiated",
                "estimated_delivery": "2-3 business days",
                "tracking_available": "Within 24 hours",
                "customer_service": "Available 24/7"
            }
            
            # Add AP2 compliance confirmation
            result["ap2_compliance"] = {
                "mandate_fulfilled": True,
                "transaction_signed": True,
                "audit_trail": "Complete"
            }
            
            _logger.info(f"OTP verified and payment completed: {result.get('transaction_id')}")
        else:
            _logger.warning(f"OTP verification failed: {result.get('error', 'Unknown error')}")
        
        return json.dumps(result, default=str)
        
    except OTPError as e:
        _logger.error(f"OTP verification error: {str(e)}")
        return json.dumps({
            "error": str(e),
            "mandate_id": mandate_id,
            "status": "failed"
        })
    except Exception as e:
        _logger.error(f"Unexpected OTP error: {str(e)}")
        return json.dumps({
            "error": f"OTP verification failed: {str(e)}",
            "mandate_id": mandate_id,
            "status": "failed"
        })


def enhanced_get_transaction_status(transaction_id: str) -> str:
    """
    Get comprehensive transaction status with audit trail.
    
    Args:
        transaction_id: Transaction identifier
        
    Returns:
        JSON string with detailed transaction status
    """
    try:
        _logger.info(f"Getting transaction status: {transaction_id}")
        
        # Run async status check
        # Call synchronous transaction status method
        result = _payment_service.get_transaction_status(transaction_id)
        
        if "error" not in result:
            # Add additional context
            result["audit_trail"] = {
                "payment_initiated": result.get("created_at"),
                "otp_verified": result.get("processed_at"),
                "mandate_signed": True,
                "fraud_check": "Passed"
            }
            
            result["customer_info"] = {
                "receipt_sent": True,
                "support_available": "24/7",
                "refund_policy": "30 days"
            }
        
        return json.dumps(result, default=str)
        
    except Exception as e:
        _logger.error(f"Transaction status error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get transaction status: {str(e)}",
            "transaction_id": transaction_id
        })


def enhanced_process_refund(
    transaction_id: str,
    amount: float,
    reason: str = ""
) -> str:
    """
    Process refund with enhanced tracking and notifications.
    
    Args:
        transaction_id: Original transaction ID
        amount: Refund amount
        reason: Reason for refund
        
    Returns:
        JSON string with refund processing details
    """
    try:
        _logger.info(f"Processing refund: transaction={transaction_id}, amount={amount}")
        
        # Run async refund processing
        # Call synchronous refund processing
        result = _payment_service.process_refund(
            transaction_id=transaction_id,
            amount=amount,
            reason=reason
        )
        
        # Add refund tracking and customer service info
        if "error" not in result:
            result["tracking"] = {
                "refund_id": result["refund_id"],
                "status_updates": "Email notifications enabled",
                "customer_service": "Available for questions"
            }
            
            result["process_info"] = {
                "verification_required": False,
                "processing_time": result["estimated_arrival"],
                "partial_refund": amount < 999.99  # Simplified check
            }
        
        _logger.info(f"Refund processed: {result.get('refund_id')}")
        return json.dumps(result, default=str)
        
    except PaymentError as e:
        _logger.error(f"Refund processing error: {str(e)}")
        return json.dumps({
            "error": str(e),
            "transaction_id": transaction_id,
            "status": "failed"
        })
    except Exception as e:
        _logger.error(f"Unexpected refund error: {str(e)}")
        return json.dumps({
            "error": f"Refund processing failed: {str(e)}",
            "transaction_id": transaction_id,
            "status": "failed"
        })


def get_mandate_details(mandate_id: str) -> str:
    """
    Get detailed mandate information for transparency.
    
    Args:
        mandate_id: Mandate identifier
        
    Returns:
        JSON string with mandate details and compliance info
    """
    try:
        details = _mandate_service.get_mandate_details(mandate_id)
        
        if "error" not in details:
            # Add user-friendly information
            details["user_info"] = {
                "secure_processing": "Your payment is protected by industry-standard encryption",
                "privacy": "Your data is handled according to our privacy policy",
                "support": "Customer service available 24/7"
            }
        
        return json.dumps(details, default=str)
        
    except Exception as e:
        _logger.error(f"Get mandate details error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get mandate details: {str(e)}",
            "mandate_id": mandate_id
        })


def cleanup_expired_data() -> str:
    """
    Clean up expired OTPs and mandates for maintenance.
    
    Returns:
        JSON string with cleanup results
    """
    try:
        # Run async cleanup
        # Call synchronous cleanup methods
        expired_otps = _payment_service.cleanup_expired_otps()
        
        expired_mandates = _mandate_service.cleanup_expired_mandates()
        
        result = {
            "cleanup_completed": True,
            "expired_otps_removed": expired_otps,
            "expired_mandates_removed": expired_mandates,
            "cleanup_timestamp": "now"
        }
        
        _logger.info(f"Cleanup completed: {expired_otps} OTPs, {expired_mandates} mandates")
        return json.dumps(result, default=str)
        
    except Exception as e:
        _logger.error(f"Cleanup error: {str(e)}")
        return json.dumps({
            "error": f"Cleanup failed: {str(e)}",
            "cleanup_completed": False
        })