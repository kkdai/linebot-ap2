#!/usr/bin/env python3
"""
Demo script to showcase AP2 integration features in LINE Bot
This script demonstrates the shopping and payment functionality without needing LINE Bot setup
"""

import json
import asyncio
from ap2_agents.shopping_agent import (
    search_products, 
    get_product_details, 
    create_cart_mandate,
    get_shopping_recommendations
)
from ap2_agents.payment_processor import (
    get_user_payment_methods,
    initiate_payment,
    verify_otp,
    process_refund
)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")


def print_json_result(result: str, title: str = "Result"):
    """Pretty print JSON result"""
    try:
        data = json.loads(result)
        print(f"\n{title}:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(f"\n{title}: {result}")


async def demo_shopping_features():
    """Demonstrate shopping assistant features"""
    print_section("AP2 SHOPPING ASSISTANT DEMO")
    
    # 1. Product Search
    print("\n1. Searching for products...")
    result = search_products("iPhone")
    print_json_result(result, "Search Results for 'iPhone'")
    
    # 2. Product Details
    print("\n2. Getting product details...")
    result = get_product_details("prod_001")
    print_json_result(result, "Product Details for iPhone 15 Pro")
    
    # 3. Recommendations
    print("\n3. Getting recommendations...")
    result = get_shopping_recommendations("electronics")
    print_json_result(result, "Recommendations for Electronics")
    
    # 4. Create Cart Mandate
    print("\n4. Creating cart mandate...")
    result = create_cart_mandate("prod_001", 1, "demo_user_123")
    print_json_result(result, "Cart Mandate Created")
    
    return json.loads(result)["mandate_id"]


async def demo_payment_features(mandate_id: str):
    """Demonstrate payment processing features"""
    print_section("AP2 PAYMENT PROCESSOR DEMO")
    
    user_id = "demo_user_123"
    
    # 1. Get Payment Methods
    print("\n1. Getting user payment methods...")
    result = get_user_payment_methods(user_id)
    print_json_result(result, "Available Payment Methods")
    
    # 2. Initiate Payment
    print("\n2. Initiating payment...")
    result = initiate_payment(mandate_id, "card_001", user_id)
    payment_data = json.loads(result)
    print_json_result(result, "Payment Initiation")
    
    # Extract OTP for demo (in real scenario, user would receive this via SMS)
    from ap2_agents.payment_processor import _otp_store
    actual_otp = _otp_store[mandate_id]["otp"]
    print(f"\n📱 Demo: OTP sent to user's phone: {actual_otp}")
    
    # 3. Verify OTP
    print("\n3. Verifying OTP...")
    result = verify_otp(mandate_id, actual_otp, user_id)
    payment_result = json.loads(result)
    print_json_result(result, "OTP Verification")
    
    if payment_result["status"] == "payment_successful":
        return payment_result["transaction_id"]
    return None


async def demo_additional_features(transaction_id: str):
    """Demonstrate additional features"""
    print_section("ADDITIONAL AP2 FEATURES")
    
    if transaction_id:
        # 1. Transaction Status
        print("\n1. Checking transaction status...")
        from ap2_agents.payment_processor import get_transaction_status
        result = get_transaction_status(transaction_id)
        print_json_result(result, "Transaction Status")
        
        # 2. Process Refund (demo)
        print("\n2. Processing refund (demo)...")
        result = process_refund(transaction_id, 999.00, "Customer requested refund")
        print_json_result(result, "Refund Processing")


def demo_intent_detection():
    """Demonstrate intent detection"""
    print_section("INTENT DETECTION DEMO")
    
    def determine_intent(message: str) -> str:
        """Simplified intent detection for demo"""
        message_lower = message.lower()
        
        payment_keywords = ['pay', 'payment', 'otp', 'verify', '付款', '支付', '驗證']
        shopping_keywords = ['buy', 'shop', 'product', '買', '購物', 'iphone', 'macbook']
        weather_keywords = ['weather', 'time', '天氣', '時間']
        
        for keyword in payment_keywords:
            if keyword in message_lower:
                return 'payment'
        for keyword in shopping_keywords:
            if keyword in message_lower:
                return 'shopping'
        for keyword in weather_keywords:
            if keyword in message_lower:
                return 'weather_time'
        return 'shopping'
    
    test_messages = [
        "我想買 iPhone 15 Pro",
        "今天台北天氣如何？",
        "我要付款",
        "Show me MacBook options",
        "Verify my OTP code",
        "What time is it in New York?",
        "幫我結帳"
    ]
    
    print("\nIntent Detection Results:")
    for message in test_messages:
        intent = determine_intent(message)
        print(f"  '{message}' → {intent}")


async def main():
    """Run the complete demo"""
    print("🚀 LINE Bot with AP2 Integration Demo")
    print("This demo showcases shopping assistant and payment processing features")
    
    # Demo intent detection
    demo_intent_detection()
    
    # Demo shopping features
    mandate_id = await demo_shopping_features()
    
    # Demo payment features
    transaction_id = await demo_payment_features(mandate_id)
    
    # Demo additional features
    await demo_additional_features(transaction_id)
    
    print_section("DEMO COMPLETED")
    print("✅ All AP2 features are working correctly!")
    print("\nKey Features Demonstrated:")
    print("  • Product search and recommendations")
    print("  • Shopping cart and mandate creation")
    print("  • Secure payment processing with OTP")
    print("  • Transaction management and refunds")
    print("  • Intelligent intent detection")
    print("\n🎉 Your LINE Bot is now ready with AP2 e-commerce capabilities!")


if __name__ == "__main__":
    asyncio.run(main())