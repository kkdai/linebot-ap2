"""
Shopping Agent for AP2 integration with LINE Bot
Handles product search, recommendations, and purchase orchestration
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from google.adk.agents import Agent
from google.genai import types


# Mock product database for demo
DEMO_PRODUCTS = [
    {
        "id": "prod_001",
        "name": "iPhone 15 Pro",
        "price": 999.00,
        "currency": "USD",
        "description": "Latest Apple iPhone with advanced camera system",
        "category": "Electronics",
        "stock": 10
    },
    {
        "id": "prod_002", 
        "name": "MacBook Air M3",
        "price": 1299.00,
        "currency": "USD",
        "description": "Lightweight laptop with M3 chip",
        "category": "Computers",
        "stock": 5
    },
    {
        "id": "prod_003",
        "name": "AirPods Pro",
        "price": 249.00,
        "currency": "USD", 
        "description": "Wireless earbuds with noise cancellation",
        "category": "Audio",
        "stock": 15
    },
    {
        "id": "prod_004",
        "name": "Apple Watch Series 9",
        "price": 399.00,
        "currency": "USD",
        "description": "Advanced smartwatch with health monitoring",
        "category": "Wearables",
        "stock": 8
    }
]


def search_products(query: str = "", category: str = "") -> str:
    """
    Search for products based on query or category
    
    Args:
        query: Search term for product name or description
        category: Product category filter
        
    Returns:
        JSON string of matching products
    """
    results = []
    
    for product in DEMO_PRODUCTS:
        match = True
        
        if query:
            query_lower = query.lower()
            if (query_lower not in product["name"].lower() and 
                query_lower not in product["description"].lower()):
                match = False
                
        if category:
            if category.lower() != product["category"].lower():
                match = False
                
        if match:
            results.append(product)
    
    return json.dumps({
        "products": results,
        "total": len(results),
        "search_query": query,
        "category": category
    })


def get_product_details(product_id: str) -> str:
    """
    Get detailed information about a specific product
    
    Args:
        product_id: Unique product identifier
        
    Returns:
        JSON string with product details
    """
    for product in DEMO_PRODUCTS:
        if product["id"] == product_id:
            return json.dumps({
                "product": product,
                "availability": "in_stock" if product["stock"] > 0 else "out_of_stock",
                "estimated_delivery": "2-3 business days"
            })
    
    return json.dumps({
        "error": "Product not found",
        "product_id": product_id
    })


def create_cart_mandate(product_id: str, quantity: int = 1, user_id: str = "") -> str:
    """
    Create a cart mandate for AP2 payment processing
    
    Args:
        product_id: Product to add to cart
        quantity: Number of items
        user_id: User identifier
        
    Returns:
        JSON string with cart mandate details
    """
    product = None
    for p in DEMO_PRODUCTS:
        if p["id"] == product_id:
            product = p
            break
            
    if not product:
        return json.dumps({"error": "Product not found"})
        
    if product["stock"] < quantity:
        return json.dumps({"error": "Insufficient stock"})
    
    total_amount = product["price"] * quantity
    mandate_id = f"mandate_{uuid.uuid4().hex[:8]}"
    
    cart_mandate = {
        "mandate_id": mandate_id,
        "type": "cart_mandate",
        "user_id": user_id,
        "items": [{
            "product_id": product_id,
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity,
            "subtotal": total_amount
        }],
        "total_amount": total_amount,
        "currency": product["currency"],
        "created_at": datetime.now().isoformat(),
        "status": "pending_payment"
    }
    
    return json.dumps(cart_mandate)


def get_shopping_recommendations(user_preferences: str = "") -> str:
    """
    Get personalized product recommendations
    
    Args:
        user_preferences: User's preferences or interests
        
    Returns:
        JSON string with recommended products
    """
    # Simple recommendation logic based on preferences
    recommendations = []
    
    if not user_preferences:
        # Default recommendations - popular items
        recommendations = DEMO_PRODUCTS[:2]
    else:
        prefs_lower = user_preferences.lower()
        
        # Match based on preferences
        for product in DEMO_PRODUCTS:
            if (prefs_lower in product["name"].lower() or 
                prefs_lower in product["description"].lower() or
                prefs_lower in product["category"].lower()):
                recommendations.append(product)
                
        # If no matches, suggest popular items
        if not recommendations:
            recommendations = DEMO_PRODUCTS[:2]
    
    return json.dumps({
        "recommendations": recommendations,
        "total": len(recommendations),
        "based_on": user_preferences or "popular_items"
    })


# Create shopping agent with tools
shopping_agent = Agent(
    name="ap2_shopping_assistant",  
    model="gemini-2.5-flash",
    description="Shopping assistant that helps users find products, create carts, and process payments using AP2 protocol",
    instruction="""You are a helpful shopping assistant that can:
    
    1. Search for products based on user queries
    2. Provide detailed product information  
    3. Create shopping carts and payment mandates
    4. Give personalized recommendations
    5. Help users complete purchases securely
    
    Always be friendly and helpful. When users show interest in purchasing, guide them through the AP2 payment process step by step.
    Provide clear product information including prices, descriptions, and availability.
    
    After creating a cart mandate, tell users they can proceed to payment by saying phrases like "我要付款" or "proceed to payment".
    For payments, explain the security features like OTP verification and signed mandates to build user confidence.""",
    tools=[
        search_products,
        get_product_details, 
        create_cart_mandate,
        get_shopping_recommendations
    ]
)