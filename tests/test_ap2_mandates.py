"""Test AP2 mandate flow - Phase 1 compliance."""

import sys
sys.path.insert(0, '/Users/al03034132/Documents/linebot-ap2')

from src.linebot_ap2.services import get_mandate_service, get_payment_service
from src.linebot_ap2.models.payment import TransactionModality


def test_full_ap2_mandate_flow():
    """Test complete AP2 mandate flow with merchant and user signatures."""

    mandate_service = get_mandate_service()
    payment_service = get_payment_service()

    # Clean state
    mandate_service.active_mandates.clear()
    mandate_service.payment_mandates.clear()

    print("=" * 60)
    print("AP2 Phase 1 Mandate Flow Test")
    print("=" * 60)

    # Step 1: Create cart mandate (merchant signs automatically)
    print("\n1. Creating cart mandate with merchant signature...")
    items = [
        {"product_id": "prod_001", "name": "Test Product", "price": 99.99, "quantity": 2}
    ]
    result = mandate_service.create_signed_mandate(
        user_id="test_user_001",
        items=items,
        merchant_id="merchant_001",
        merchant_name="Test Store"
    )

    mandate_id = result["mandate"]["id"]
    print(f"   Mandate ID: {mandate_id}")
    print(f"   Merchant signed: {result['ap2_signatures']['merchant_signed']}")
    print(f"   User signed: {result['ap2_signatures']['user_signed']}")
    print(f"   Awaiting: {result['ap2_signatures']['awaiting']}")

    assert result["ap2_signatures"]["merchant_signed"] == True
    assert result["ap2_signatures"]["user_signed"] == False
    assert result["ap2_signatures"]["awaiting"] == "user_signature"

    # Step 2: User signs mandate
    print("\n2. User signing mandate...")
    mandate = mandate_service.user_sign_mandate(mandate_id, "test_user_001")
    print(f"   User signature: {mandate.user_signature[:32]}...")
    print(f"   Fully signed: {mandate.is_fully_signed()}")

    assert mandate.is_fully_signed() == True

    # Step 3: Create PaymentMandate
    print("\n3. Creating PaymentMandate for network/issuer...")
    payment_mandate = mandate_service.create_payment_mandate(
        cart_mandate=mandate,
        payment_method_name="CARD",
        payment_token="tok_test_123"
    )

    print(f"   PaymentMandate ID: {payment_mandate.payment_mandate_id}")
    print(f"   Agent presence: {payment_mandate.agent_presence}")
    print(f"   Modality: {payment_mandate.transaction_modality.value}")
    print(f"   Cart mandate ID: {payment_mandate.cart_mandate_id}")

    assert payment_mandate.agent_presence == True
    assert payment_mandate.transaction_modality == TransactionModality.HUMAN_PRESENT
    assert payment_mandate.cart_mandate_id == mandate_id

    # Step 4: Generate network payload
    print("\n4. Generating network payload...")
    network_payload = payment_mandate.to_network_payload()
    print(f"   Payload keys: {list(network_payload.keys())}")

    assert "agent_presence" in network_payload
    assert "transaction_modality" in network_payload
    assert network_payload["transaction_modality"] == "human_present"

    print("\n" + "=" * 60)
    print("✅ All AP2 Phase 1 tests passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_full_ap2_mandate_flow()
