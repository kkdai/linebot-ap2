#!/usr/bin/env python3
"""Test script to verify service sharing between shopping and payment tools."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.linebot_ap2.tools.shopping_tools import (
    enhanced_search_products,
    enhanced_add_to_cart,
    enhanced_create_cart_mandate
)
from src.linebot_ap2.tools.payment_tools import get_mandate_details
from src.linebot_ap2.services import get_mandate_service, get_product_service

def test_service_sharing():
    """Test that mandate created by shopping tools is accessible by payment tools."""

    print("=" * 80)
    print("Testing Service Sharing Between Shopping and Payment Agents")
    print("=" * 80)

    user_id = "test_user"

    # Step 0: Search for a product
    print("\n0. Searching for products...")
    search_result = enhanced_search_products(query="iPhone", in_stock_only=True)
    search_data = json.loads(search_result)

    if not search_data.get("products"):
        print("   ✗ No products found")
        return False

    product = search_data["products"][0]
    product_id = product["id"]
    print(f"   ✓ Found: {product['name']} (${product['price']})")

    # Step 0.5: Add product to cart
    print(f"\n0.5. Adding product to cart...")
    add_result = enhanced_add_to_cart(user_id=user_id, product_id=product_id, quantity=1)
    add_data = json.loads(add_result)

    if "error" in add_data:
        print(f"   ✗ Error: {add_data['error']}")
        return False

    print(f"   ✓ Added to cart: {add_data['cart']['item_count']} item(s), ${add_data['cart']['total_amount']}")

    # Step 1: Create mandate using shopping tools
    print("\n1. Creating mandate using Shopping Tools...")
    result = enhanced_create_cart_mandate(user_id=user_id, expires_in_minutes=30)

    result_data = json.loads(result)
    print(f"   ✓ Mandate created: {result_data.get('mandate', {}).get('id', 'N/A')}")

    if "error" in result_data:
        print(f"   ✗ Error: {result_data['error']}")
        return False

    mandate_id = result_data["mandate"]["id"]
    print(f"   Total: ${result_data['mandate']['total_amount']}")
    print(f"   Status: {result_data['mandate']['status']}")
    print(f"   Expires: {result_data['mandate']['expires_at']}")

    # Step 2: Verify mandate using payment tools
    print(f"\n2. Retrieving mandate using Payment Tools...")
    mandate_details = get_mandate_details(mandate_id)
    details_data = json.loads(mandate_details)

    if "error" in details_data:
        print(f"   ✗ FAILED: Mandate not found by Payment Tools!")
        print(f"   Error: {details_data['error']}")
        return False

    print(f"   ✓ SUCCESS: Mandate found by Payment Tools!")
    print(f"   Mandate ID: {details_data['mandate']['id']}")
    print(f"   Total: ${details_data['mandate']['total_amount']}")
    print(f"   Items: {len(details_data['mandate']['items'])}")

    # Step 3: Verify service instances are the same
    print(f"\n3. Verifying service instances...")
    from src.linebot_ap2.tools import shopping_tools, payment_tools

    shopping_mandate_service = shopping_tools._mandate_service
    payment_mandate_service = payment_tools._mandate_service
    shared_mandate_service = get_mandate_service()

    if shopping_mandate_service is payment_mandate_service:
        print(f"   ✓ Shopping and Payment tools use the SAME MandateService instance")
    else:
        print(f"   ✗ Shopping and Payment tools use DIFFERENT MandateService instances")
        return False

    if shopping_mandate_service is shared_mandate_service:
        print(f"   ✓ Tools use the shared singleton instance")
    else:
        print(f"   ✗ Tools do NOT use the shared singleton instance")
        return False

    # Step 4: Verify mandate storage
    print(f"\n4. Verifying mandate storage...")
    mandate_obj = shared_mandate_service.get_mandate(mandate_id)
    if mandate_obj:
        print(f"   ✓ Mandate exists in shared service")
        print(f"   User: {mandate_obj.user_id}")
        print(f"   Items: {len(mandate_obj.items)}")
        print(f"   Status: {mandate_obj.status.value}")
    else:
        print(f"   ✗ Mandate NOT found in shared service")
        return False

    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED - Services are properly shared!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_service_sharing()
    sys.exit(0 if success else 1)
