#!/usr/bin/env python3
"""Test script to verify the mandate fix for the "mandate not found" issue."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.linebot_ap2.tools.shopping_tools import (
    enhanced_search_products,
    enhanced_add_to_cart,
    enhanced_create_cart_mandate,
    get_user_mandates as shopping_get_user_mandates
)
from src.linebot_ap2.tools.payment_tools import (
    enhanced_initiate_payment,
    get_user_mandates as payment_get_user_mandates
)


def test_mandate_not_found_scenario():
    """Test the scenario where payment agent receives an invalid mandate ID."""

    print("=" * 80)
    print("Testing Mandate Not Found Scenario (Simulating AI Hallucination)")
    print("=" * 80)

    user_id = "test_user_123"

    # Scenario 1: Try to use a fake mandate ID (simulating AI hallucination)
    print("\n[Scenario 1] User provides fake mandate ID (AI hallucination)")
    print("-" * 80)

    fake_mandate_id = "mandate_fake_abc123"
    print(f"User says: '支付代理 {fake_mandate_id}'")

    # Get valid payment method first
    from src.linebot_ap2.tools.payment_tools import enhanced_get_payment_methods
    payment_methods_result = enhanced_get_payment_methods(user_id)
    payment_methods_data = json.loads(payment_methods_result)
    valid_payment_method = payment_methods_data['payment_methods'][0]['id']

    # Payment agent tries to initiate payment
    print(f"\nPayment agent calling enhanced_initiate_payment with fake ID...")
    result = enhanced_initiate_payment(
        mandate_id=fake_mandate_id,
        payment_method_id=valid_payment_method,
        user_id=user_id
    )

    result_data = json.loads(result)
    print(f"\nResult: {result_data.get('error', 'success')}")

    if result_data.get("error") == "mandate_not_found":
        print("✓ Correctly detected fake mandate")
        print(f"  - Message: {result_data['message'][:100]}...")
        print(f"  - User has {result_data['user_active_mandates_count']} active mandates")
        print(f"  - Suggestion: {result_data['suggestion']}")

        # Now check user's actual mandates
        print(f"\nPayment agent calling get_user_mandates...")
        mandates_result = payment_get_user_mandates(user_id)
        mandates_data = json.loads(mandates_result)
        print(f"  - Found {mandates_data['total_count']} active mandates")
        if not mandates_data['has_mandates']:
            print(f"  - Message: {mandates_data['message']}")
    else:
        print("✗ FAILED: Should have detected fake mandate")
        return False

    # Scenario 2: Create a real mandate and use it
    print("\n[Scenario 2] Create real mandate through shopping agent")
    print("-" * 80)

    # Search and add to cart
    print("1. Searching for products...")
    search_result = enhanced_search_products(query="iPhone", in_stock_only=True)
    search_data = json.loads(search_result)

    if not search_data.get("products"):
        print("✗ No products found")
        return False

    product = search_data["products"][0]
    product_id = product["id"]
    print(f"   ✓ Found: {product['name']} (${product['price']})")

    print(f"\n2. Adding to cart...")
    add_result = enhanced_add_to_cart(user_id=user_id, product_id=product_id, quantity=1)
    add_data = json.loads(add_result)
    print(f"   ✓ Added: {add_data['cart']['item_count']} item(s), ${add_data['cart']['total_amount']}")

    print(f"\n3. Creating mandate...")
    mandate_result = enhanced_create_cart_mandate(user_id=user_id, expires_in_minutes=30)
    mandate_data = json.loads(mandate_result)

    if "error" in mandate_data:
        print(f"✗ Error: {mandate_data['error']}")
        return False

    real_mandate_id = mandate_data["mandate"]["id"]
    print(f"   ✓ Mandate created: {real_mandate_id}")
    print(f"   Total: ${mandate_data['mandate']['total_amount']}")

    # Scenario 3: Verify payment agent can now see the mandate
    print("\n[Scenario 3] Payment agent verifies real mandate")
    print("-" * 80)

    print(f"Payment agent calling get_user_mandates...")
    mandates_result = payment_get_user_mandates(user_id)
    mandates_data = json.loads(mandates_result)

    print(f"✓ Found {mandates_data['total_count']} active mandate(s)")

    if mandates_data['has_mandates']:
        print(f"  Message: {mandates_data['message']}")
        for mandate in mandates_data['active_mandates']:
            print(f"\n  Mandate: {mandate['mandate']['id']}")
            print(f"    Total: ${mandate['mandate']['total_amount']}")
            print(f"    Status: {mandate['mandate']['status']}")
            print(f"    Valid: {mandate['ap2_compliance']['valid']}")

    # Scenario 4: Initiate payment with real mandate
    print("\n[Scenario 4] Initiate payment with real mandate")
    print("-" * 80)

    print(f"Payment agent calling enhanced_initiate_payment with real ID...")
    result = enhanced_initiate_payment(
        mandate_id=real_mandate_id,
        payment_method_id=valid_payment_method,
        user_id=user_id
    )

    result_data = json.loads(result)

    if "error" not in result_data:
        print("✓ Payment initiated successfully!")
        print(f"  Transaction ID: {result_data.get('transaction_id')}")
        print(f"  OTP Code: {result_data.get('otp_code')}")
        print(f"  Status: {result_data.get('status')}")
    else:
        print(f"✗ Payment initiation failed: {result_data['error']}")
        return False

    print("\n" + "=" * 80)
    print("✓ ALL SCENARIOS PASSED!")
    print("=" * 80)
    print("\nFix Summary:")
    print("1. ✓ Payment agent correctly detects fake mandate IDs")
    print("2. ✓ get_user_mandates tool helps debug and guide users")
    print("3. ✓ Improved error messages explain the issue clearly")
    print("4. ✓ Real mandates work correctly across agents")
    print("5. ✓ Service sharing verified and working")

    return True


if __name__ == "__main__":
    success = test_mandate_not_found_scenario()
    sys.exit(0 if success else 1)
