"""Test Credential Provider - Phase 2 AP2 compliance."""

import sys
sys.path.insert(0, '/Users/al03034132/Documents/linebot-ap2')

from src.linebot_ap2.services import get_credential_provider, get_mandate_service


def test_credential_provider_flow():
    """Test complete Credential Provider flow."""

    cp = get_credential_provider()
    mandate_service = get_mandate_service()

    # Clean state
    mandate_service.active_mandates.clear()

    print("=" * 60)
    print("AP2 Phase 2: Credential Provider Test")
    print("=" * 60)

    # Step 1: Get user credentials
    print("\n1. Getting user credentials...")
    credentials = cp.get_user_credentials("demo_user")
    print(f"   Found {len(credentials)} credentials")
    for cred in credentials:
        print(f"   - {cred.brand} ****{cred.last_four} (default: {cred.is_default})")

    assert len(credentials) >= 2

    # Step 2: Get eligible methods for transaction
    print("\n2. Getting eligible methods for $150 USD...")
    eligible = cp.get_eligible_methods(
        user_id="demo_user",
        amount=150.0,
        currency="USD"
    )
    print(f"   Found {len(eligible)} eligible methods")

    assert len(eligible) >= 1

    # Step 3: Select optimal method
    print("\n3. Selecting optimal payment method...")
    optimal = cp.select_optimal_method(
        user_id="demo_user",
        amount=150.0,
        currency="USD"
    )
    print(f"   Selected: {optimal.brand} ****{optimal.last_four}")

    assert optimal is not None
    assert optimal.is_default == True

    # Step 4: Create a mandate
    print("\n4. Creating cart mandate...")
    mandate_result = mandate_service.create_signed_mandate(
        user_id="demo_user",
        items=[{"product_id": "prod_001", "name": "Test Item", "price": 150.0}]
    )
    mandate_id = mandate_result["mandate"]["id"]
    print(f"   Mandate ID: {mandate_id}")

    # Step 5: Issue payment token
    print("\n5. Issuing payment token...")
    token = cp.issue_payment_token(
        credential_id=optimal.credential_id,
        mandate_id=mandate_id,
        amount=150.0,
        currency="USD"
    )
    print(f"   Token ID: {token.token_id}")
    print(f"   Expires: {token.expires_at.isoformat()}")

    assert token is not None
    assert token.mandate_id == mandate_id

    # Step 6: Validate token
    print("\n6. Validating token...")
    is_valid = cp.validate_token(token.token_id)
    print(f"   Valid: {is_valid}")

    assert is_valid == True

    # Step 7: Consume token
    print("\n7. Consuming token for payment...")
    consumed = cp.consume_token(token.token_id)
    print(f"   Credential: {consumed['brand']} ****{consumed['last_four']}")
    print(f"   Amount: {consumed['amount']} {consumed['currency']}")

    assert consumed is not None
    assert "_credential_data" in consumed

    # Step 8: Verify token is now invalid
    print("\n8. Verifying token is consumed...")
    is_still_valid = cp.validate_token(token.token_id)
    print(f"   Still valid: {is_still_valid}")

    assert is_still_valid == False

    print("\n" + "=" * 60)
    print("All Credential Provider tests passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_credential_provider_flow()
