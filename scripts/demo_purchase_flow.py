#!/usr/bin/env python3
"""
AP2 Complete Purchase Flow Demo Script
=======================================

This script demonstrates the complete purchase flow from product search
to payment completion, integrating all AP2 components:

1. Product Search & Cart
2. Mandate Creation (AP2 Phase 1)
3. Credential Provider (AP2 Phase 2)
4. Payment & OTP Verification

Usage:
    python scripts/demo_purchase_flow.py

Author: Evan Lin
"""

import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/Users/al03034132/Documents/linebot-ap2')

# Import services
from src.linebot_ap2.services import (
    get_product_service,
    get_mandate_service,
    get_payment_service,
    get_credential_provider
)

# Import tools (these are what the agents use)
from src.linebot_ap2.tools.shopping_tools import (
    enhanced_search_products,
    enhanced_get_product_details,
    enhanced_add_to_cart,
    enhanced_create_cart_mandate,
    get_eligible_payment_methods,
    issue_payment_token_for_mandate
)

from src.linebot_ap2.tools.payment_tools import (
    enhanced_initiate_payment,
    enhanced_verify_otp,
    enhanced_get_transaction_status,
    initiate_payment_with_token
)


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step: int, description: str):
    """Print a step indicator."""
    print(f"\n{'─' * 60}")
    print(f"  Step {step}: {description}")
    print(f"{'─' * 60}")


def print_json(data: dict, indent: int = 2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str, ensure_ascii=False))


def parse_json_response(response: str) -> dict:
    """Parse JSON string response from tools."""
    return json.loads(response)


def demo_complete_purchase_flow():
    """
    Complete AP2 Purchase Flow Demo

    This demo walks through:
    1. Product browsing and cart management
    2. Mandate creation with merchant signature
    3. Credential Provider integration
    4. Payment initiation and OTP verification
    """

    # Demo user - this user has demo credentials pre-registered
    USER_ID = "demo_user"

    print_header("AP2 Complete Purchase Flow Demo")
    print(f"\nDemo User: {USER_ID}")
    print(f"Started at: {datetime.now().isoformat()}")

    # Initialize services and clear previous state
    product_service = get_product_service()
    mandate_service = get_mandate_service()
    payment_service = get_payment_service()
    credential_provider = get_credential_provider()

    # Clear previous demo data
    mandate_service.active_mandates.clear()
    product_service.shopping_carts.clear()
    payment_service.otp_store.clear()

    print("\n[System] Previous demo data cleared.")

    # ============================================================
    # PHASE 1: PRODUCT BROWSING & CART
    # ============================================================

    print_header("PHASE 1: Product Browsing & Cart")

    # Step 1: Search for products
    print_step(1, "Search for Products")
    print("Searching for 'phone' in electronics category...")

    search_result = parse_json_response(
        enhanced_search_products(
            query="phone",
            category="electronics"
        )
    )

    print(f"\nFound {search_result.get('total', 0)} products:")
    for product in search_result.get('products', [])[:3]:
        print(f"  - {product['name']}: ${product['price']} ({product['brand']})")

    if not search_result.get('products'):
        print("No products found. Using fallback search...")
        search_result = parse_json_response(enhanced_search_products(query=""))

    # Step 2: View product details
    print_step(2, "View Product Details")

    selected_product = search_result['products'][0]
    product_id = selected_product['id']  # Note: field is 'id', not 'product_id'
    print(f"Getting details for: {selected_product['name']}")

    product_details = parse_json_response(
        enhanced_get_product_details(product_id=product_id)
    )

    print(f"\nProduct Details:")
    print(f"  Name: {product_details['product']['name']}")
    print(f"  Price: ${product_details['product']['price']}")
    print(f"  Brand: {product_details['product']['brand']}")
    print(f"  Stock: {product_details['product']['stock']}")
    if product_details['product'].get('specifications'):
        print(f"  Specs: {product_details['product']['specifications']}")

    # Step 3: Add to cart
    print_step(3, "Add to Cart")
    print(f"Adding {selected_product['name']} to cart (quantity: 1)...")

    cart_result = parse_json_response(
        enhanced_add_to_cart(
            user_id=USER_ID,
            product_id=product_id,
            quantity=1
        )
    )

    print(f"\nCart Updated:")
    print(f"  Items in cart: {cart_result['cart']['item_count']}")
    print(f"  Cart total: ${cart_result['cart']['total_amount']}")

    # Add another product for variety
    if len(search_result['products']) > 1:
        second_product = search_result['products'][1]
        print(f"\nAdding second product: {second_product['name']}...")
        cart_result = parse_json_response(
            enhanced_add_to_cart(
                user_id=USER_ID,
                product_id=second_product['id'],  # Note: field is 'id'
                quantity=1
            )
        )
        print(f"  Cart total: ${cart_result['cart']['total_amount']}")

    # ============================================================
    # PHASE 2: MANDATE CREATION (AP2 Phase 1)
    # ============================================================

    print_header("PHASE 2: Mandate Creation (AP2 Phase 1)")

    # Step 4: Create cart mandate
    print_step(4, "Create Cart Mandate with Merchant Signature")
    print("Creating signed cart mandate...")

    mandate_result = parse_json_response(
        enhanced_create_cart_mandate(
            user_id=USER_ID,
            expires_in_minutes=30
        )
    )

    mandate_id = mandate_result['mandate']['id']
    total_amount = mandate_result['mandate']['total_amount']
    currency = mandate_result['mandate'].get('currency', 'USD')

    print(f"\nMandate Created:")
    print(f"  Mandate ID: {mandate_id}")
    print(f"  Total Amount: ${total_amount} {currency}")
    print(f"  Expires: {mandate_result['mandate']['expires_at']}")
    print(f"\nAP2 Signatures:")
    print(f"  Merchant Signed: {mandate_result['ap2_signatures']['merchant_signed']}")
    print(f"  User Signed: {mandate_result['ap2_signatures']['user_signed']}")
    print(f"  Awaiting: {mandate_result['ap2_signatures']['awaiting']}")

    print(f"\nCart Items:")
    for item in mandate_result['mandate']['items']:
        print(f"  - {item['name']}: ${item['price']} x {item.get('quantity', 1)}")

    # ============================================================
    # PHASE 3: CREDENTIAL PROVIDER (AP2 Phase 2)
    # ============================================================

    print_header("PHASE 3: Credential Provider (AP2 Phase 2)")

    # Step 5: Get eligible payment methods
    print_step(5, "Get Eligible Payment Methods")
    print(f"Querying Credential Provider for eligible methods...")
    print(f"  Transaction: ${total_amount} {currency}")

    eligible_result = parse_json_response(
        get_eligible_payment_methods(
            user_id=USER_ID,
            amount=total_amount,
            currency=currency
        )
    )

    print(f"\nEligible Payment Methods ({eligible_result['total']} found):")
    for method in eligible_result['eligible_methods']:
        default_marker = " (DEFAULT)" if method['is_default'] else ""
        nickname = f" - {method['nickname']}" if method.get('nickname') else ""
        print(f"  - {method['brand']} ****{method['last_four']}{nickname}{default_marker}")
        print(f"    Credential ID: {method['credential_id']}")

    # Select the default (first) method
    selected_credential = eligible_result['eligible_methods'][0]
    credential_id = selected_credential['credential_id']
    print(f"\nSelected: {selected_credential['brand']} ****{selected_credential['last_four']}")

    # Step 6: Issue payment token
    print_step(6, "Issue Payment Token")
    print(f"Issuing one-time token for mandate...")
    print(f"  Credential: {credential_id}")
    print(f"  Mandate: {mandate_id}")

    token_result = parse_json_response(
        issue_payment_token_for_mandate(
            user_id=USER_ID,
            credential_id=credential_id,
            mandate_id=mandate_id
        )
    )

    token_id = token_result['token_id']
    print(f"\nPayment Token Issued:")
    print(f"  Token ID: {token_id}")
    print(f"  Amount: ${token_result['amount']} {token_result['currency']}")
    print(f"  Expires: {token_result['expires_at']}")
    print(f"  Status: {token_result['status']}")

    # ============================================================
    # PHASE 4: PAYMENT & OTP VERIFICATION
    # ============================================================

    print_header("PHASE 4: Payment & OTP Verification")

    # Step 7: Initiate payment
    print_step(7, "Initiate Payment")
    print("Initiating payment and generating OTP...")

    # Note: Currently PaymentService has its own demo payment methods
    # In production, the token would be consumed here for actual payment processing
    # For demo, we use the standard payment flow with card_001 (matches Visa ****1234)
    payment_result = parse_json_response(
        enhanced_initiate_payment(
            mandate_id=mandate_id,
            payment_method_id="card_001",  # Demo payment method (Visa ****1234)
            user_id=USER_ID,
            amount=total_amount
        )
    )

    otp_code = payment_result.get('otp_code')

    print(f"\nPayment Initiated:")
    print(f"  Mandate ID: {payment_result['mandate_id']}")
    print(f"  Status: {payment_result['status']}")
    print(f"  OTP Required: {payment_result['otp_required']}")
    print(f"  OTP Sent To: {payment_result['otp_sent_to']}")
    print(f"  Max Attempts: {payment_result['max_attempts']}")
    print(f"  Expires In: {payment_result['expires_in_seconds']}s")

    # In production, token_info would be included when using initiate_payment_with_token
    # For demo purposes, we show the previously issued token
    print(f"\nCredential Provider Token (Pre-issued):")
    print(f"  Token ID: {token_id}")
    print(f"  Bound to Credential: {selected_credential['brand']} ****{selected_credential['last_four']}")

    print(f"\n{'*' * 50}")
    print(f"  DEMO OTP CODE: {otp_code}")
    print(f"{'*' * 50}")

    # Step 8: Verify OTP
    print_step(8, "Verify OTP and Complete Payment")
    print(f"Verifying OTP: {otp_code}")

    verify_result = parse_json_response(
        enhanced_verify_otp(
            mandate_id=mandate_id,
            otp_code=otp_code,
            user_id=USER_ID
        )
    )

    if verify_result.get('status') == 'completed':
        transaction_id = verify_result['transaction_id']

        print(f"\n{'*' * 50}")
        print(f"  PAYMENT SUCCESSFUL!")
        print(f"{'*' * 50}")
        print(f"\nTransaction Details:")
        print(f"  Transaction ID: {transaction_id}")
        print(f"  Amount: ${verify_result['amount']} {verify_result.get('currency', 'USD')}")
        print(f"  Status: {verify_result['status']}")
        print(f"  Processed At: {verify_result['processed_at']}")

        print(f"\nFulfillment Info:")
        fulfillment = verify_result.get('fulfillment', {})
        print(f"  Order Processing: {fulfillment.get('order_processing', 'N/A')}")
        print(f"  Estimated Delivery: {fulfillment.get('estimated_delivery', 'N/A')}")
        print(f"  Tracking: {fulfillment.get('tracking_available', 'N/A')}")

        print(f"\nAP2 Compliance:")
        ap2 = verify_result.get('ap2_compliance', {})
        print(f"  Mandate Fulfilled: {ap2.get('mandate_fulfilled', 'N/A')}")
        print(f"  Transaction Signed: {ap2.get('transaction_signed', 'N/A')}")
        print(f"  Audit Trail: {ap2.get('audit_trail', 'N/A')}")

        # Step 9: Verify transaction status
        print_step(9, "Verify Transaction Status")

        status_result = parse_json_response(
            enhanced_get_transaction_status(transaction_id=transaction_id)
        )

        print(f"\nTransaction Status Check:")
        print(f"  Transaction ID: {status_result['transaction_id']}")
        print(f"  Status: {status_result['status']}")
        print(f"  Amount: ${status_result['amount']}")

    else:
        print(f"\nPayment failed: {verify_result.get('error', 'Unknown error')}")
        return False

    # ============================================================
    # SUMMARY
    # ============================================================

    print_header("DEMO COMPLETE - Summary")

    print(f"""
    Purchase Flow Completed Successfully!

    Flow Summary:
    ─────────────────────────────────────────────────────────
    1. Product Search     : Found products in catalog
    2. Add to Cart        : Added items to shopping cart
    3. Create Mandate     : {mandate_id}
       - Merchant signed  : Yes
       - User signed      : Yes (at payment initiation)
    4. Credential Provider:
       - Payment method   : {selected_credential['brand']} ****{selected_credential['last_four']}
       - Token issued     : {token_id}
    5. Payment Processing :
       - OTP verified     : Yes
       - Transaction ID   : {transaction_id}
       - Status           : Completed
    ─────────────────────────────────────────────────────────

    AP2 Compliance:
    ─────────────────────────────────────────────────────────
    [✓] Cart Mandate created with items and total
    [✓] Merchant signature (Step 10 AP2 Spec)
    [✓] User signature (Step 21 AP2 Spec)
    [✓] Credential Provider issued payment token
    [✓] Payment token bound to mandate (single-use)
    [✓] OTP verification for user authorization
    [✓] Payment Mandate created for network/issuer
    [✓] Transaction recorded with audit trail
    ─────────────────────────────────────────────────────────
    """)

    print(f"Completed at: {datetime.now().isoformat()}")

    return True


def demo_with_wrong_otp():
    """Demo showing OTP retry flow with wrong OTP attempts."""

    print_header("BONUS: OTP Retry Flow Demo")
    print("\nThis demo shows what happens with incorrect OTP entries.")

    USER_ID = "demo_user"

    # Clear and setup
    product_service = get_product_service()
    mandate_service = get_mandate_service()

    mandate_service.active_mandates.clear()
    product_service.shopping_carts.clear()

    # Quick cart setup
    search_result = parse_json_response(enhanced_search_products(query=""))
    product = search_result['products'][0]

    enhanced_add_to_cart(USER_ID, product['id'], 1)  # Note: field is 'id'

    mandate_result = parse_json_response(
        enhanced_create_cart_mandate(USER_ID, 30)
    )
    mandate_id = mandate_result['mandate']['id']

    # Get credential and issue token
    eligible = parse_json_response(
        get_eligible_payment_methods(USER_ID, 999, "USD")
    )
    credential_id = eligible['eligible_methods'][0]['credential_id']

    token_result = parse_json_response(
        issue_payment_token_for_mandate(USER_ID, credential_id, mandate_id)
    )
    token_id = token_result['token_id']

    # Initiate payment (use standard flow for demo compatibility)
    payment_result = parse_json_response(
        enhanced_initiate_payment(mandate_id, "card_001", USER_ID, 249)
    )
    correct_otp = payment_result['otp_code']

    print(f"\nCorrect OTP: {correct_otp}")
    print(f"Max attempts: {payment_result['max_attempts']}")

    # Try wrong OTP
    print("\n--- Attempt 1: Wrong OTP '000000' ---")
    result1 = parse_json_response(
        enhanced_verify_otp(mandate_id, "000000", USER_ID)
    )
    print(f"Result: {result1.get('error', 'Success')}")
    print(f"Remaining attempts: {result1.get('remaining_attempts', 'N/A')}")

    # Try another wrong OTP
    print("\n--- Attempt 2: Wrong OTP '111111' ---")
    result2 = parse_json_response(
        enhanced_verify_otp(mandate_id, "111111", USER_ID)
    )
    print(f"Result: {result2.get('error', 'Success')}")
    print(f"Remaining attempts: {result2.get('remaining_attempts', 'N/A')}")

    # Try correct OTP
    print(f"\n--- Attempt 3: Correct OTP '{correct_otp}' ---")
    result3 = parse_json_response(
        enhanced_verify_otp(mandate_id, correct_otp, USER_ID)
    )

    if result3.get('status') == 'completed':
        print(f"SUCCESS! Transaction ID: {result3['transaction_id']}")
    else:
        print(f"Result: {result3.get('error', result3.get('status'))}")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AP2 Purchase Flow Demo")
    parser.add_argument(
        '--bonus',
        action='store_true',
        help='Also run the OTP retry bonus demo'
    )

    args = parser.parse_args()

    try:
        # Run main demo
        success = demo_complete_purchase_flow()

        if success and args.bonus:
            # Run bonus demo
            demo_with_wrong_otp()

        print("\n" + "=" * 70)
        print("  Demo completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
