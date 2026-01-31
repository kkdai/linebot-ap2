"""Enhanced shopping tools using the new service architecture."""

import json
from typing import Optional

from ..services import get_product_service, get_mandate_service, get_credential_provider
from ..models.product import ProductCategory
from ..common.logger import setup_logger

# Use shared service instances to ensure data consistency across agents
_product_service = get_product_service()
_mandate_service = get_mandate_service()
_credential_provider = get_credential_provider()
_logger = setup_logger("shopping_tools")


def enhanced_search_products(
    query: str = "",
    category: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    brand: str = "",
    in_stock_only: bool = True
) -> str:
    """
    Enhanced product search with advanced filtering capabilities.
    
    Args:
        query: Search term for product name, description, or tags
        category: Product category filter (Electronics, Computers, Audio, etc.)
        min_price: Minimum price filter
        max_price: Maximum price filter  
        brand: Brand name filter
        in_stock_only: Show only products in stock
        
    Returns:
        JSON string with search results and metadata
    """
    try:
        _logger.info(f"Product search: query='{query}', category='{category}', price_range={min_price}-{max_price}")
        
        result = _product_service.search_products(
            query=query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            brand=brand,
            in_stock_only=in_stock_only
        )
        
        response = {
            "products": [product.dict() for product in result.products],
            "total": result.total,
            "search_query": result.search_query,
            "category": result.category,
            "filters_applied": result.filters_applied,
            "has_results": result.has_results,
            "search_metadata": {
                "timestamp": result.products[0].updated_at.isoformat() if result.products else None,
                "categories_available": [cat.value for cat in ProductCategory],
                "total_catalog_size": len(_product_service.products)
            }
        }
        
        _logger.info(f"Search returned {result.total} products")
        return json.dumps(response, default=str)
        
    except Exception as e:
        _logger.error(f"Product search error: {str(e)}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "products": [],
            "total": 0
        })


def enhanced_get_product_details(product_id: str) -> str:
    """
    Get comprehensive product details with recommendations.
    
    Args:
        product_id: Unique product identifier
        
    Returns:
        JSON string with detailed product information
    """
    try:
        _logger.info(f"Getting product details for: {product_id}")
        
        details = _product_service.get_product_details(product_id)
        
        if not details:
            return json.dumps({
                "error": "Product not found",
                "product_id": product_id
            })
        
        _logger.info(f"Product details retrieved for: {product_id}")
        return json.dumps(details, default=str)
        
    except Exception as e:
        _logger.error(f"Product details error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get product details: {str(e)}",
            "product_id": product_id
        })


def enhanced_get_recommendations(
    user_preferences: str = "",
    category: str = "",
    limit: int = 4
) -> str:
    """
    Get personalized product recommendations.
    
    Args:
        user_preferences: User's interests or search terms
        category: Specific category to focus on
        limit: Maximum number of recommendations
        
    Returns:
        JSON string with recommended products
    """
    try:
        _logger.info(f"Getting recommendations: preferences='{user_preferences}', category='{category}'")
        
        recommendations = _product_service.get_recommendations(
            user_preferences=user_preferences,
            category=category,
            limit=limit
        )
        
        response = {
            "recommendations": recommendations,
            "total": len(recommendations),
            "based_on": user_preferences or category or "popular_items",
            "recommendation_type": "personalized" if user_preferences else "category" if category else "featured",
            "categories_available": [cat["name"] for cat in _product_service.get_product_categories()]
        }
        
        _logger.info(f"Generated {len(recommendations)} recommendations")
        return json.dumps(response, default=str)
        
    except Exception as e:
        _logger.error(f"Recommendations error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get recommendations: {str(e)}",
            "recommendations": []
        })


def enhanced_add_to_cart(
    user_id: str,
    product_id: str, 
    quantity: int = 1
) -> str:
    """
    Add product to user's shopping cart.
    
    Args:
        user_id: User identifier
        product_id: Product to add
        quantity: Number of items
        
    Returns:
        JSON string with cart update result
    """
    try:
        _logger.info(f"Adding to cart: user={user_id}, product={product_id}, qty={quantity}")
        
        result = _product_service.add_to_cart(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        
        if "error" in result:
            _logger.warning(f"Add to cart failed: {result['error']}")
        else:
            _logger.info(f"Product added to cart successfully")
        
        return json.dumps(result, default=str)
        
    except Exception as e:
        _logger.error(f"Add to cart error: {str(e)}")
        return json.dumps({
            "error": f"Failed to add to cart: {str(e)}",
            "user_id": user_id,
            "product_id": product_id
        })


def enhanced_create_cart_mandate(
    user_id: str,
    expires_in_minutes: int = 30
) -> str:
    """
    Create AP2-compliant cart mandate for payment processing.
    
    Args:
        user_id: User identifier
        expires_in_minutes: Mandate expiration time
        
    Returns:
        JSON string with signed mandate details
    """
    try:
        _logger.info(f"Creating cart mandate for user: {user_id}")
        
        # Get cart data from product service
        cart_data = _product_service.create_cart_mandate_data(user_id)
        
        if "error" in cart_data:
            _logger.warning(f"Cart mandate creation failed: {cart_data['error']}")
            return json.dumps(cart_data)
        
        # Create signed mandate using mandate service
        signed_mandate = _mandate_service.create_signed_mandate(
            user_id=cart_data["user_id"],
            items=cart_data["items"],
            currency="USD",
            expires_in_minutes=expires_in_minutes
        )
        
        # Add shopping context
        signed_mandate["shopping_context"] = {
            "cart_total": cart_data["total_amount"],
            "item_count": cart_data["item_count"],
            "created_from": "shopping_cart"
        }
        
        _logger.info(f"Cart mandate created: {signed_mandate['mandate']['id']}")
        return json.dumps(signed_mandate, default=str)
        
    except Exception as e:
        _logger.error(f"Cart mandate creation error: {str(e)}")
        return json.dumps({
            "error": f"Failed to create cart mandate: {str(e)}",
            "user_id": user_id
        })


def get_product_categories() -> str:
    """
    Get all available product categories with counts.
    
    Returns:
        JSON string with category information
    """
    try:
        categories = _product_service.get_product_categories()
        
        response = {
            "categories": categories,
            "total_categories": len(categories),
            "catalog_stats": {
                "total_products": len(_product_service.products),
                "in_stock_products": sum(1 for p in _product_service.products.values() if p.is_available)
            }
        }
        
        return json.dumps(response, default=str)
        
    except Exception as e:
        _logger.error(f"Get categories error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get categories: {str(e)}",
            "categories": []
        })


def get_shopping_cart(user_id: str) -> str:
    """
    Get user's current shopping cart.

    Args:
        user_id: User identifier

    Returns:
        JSON string with cart contents
    """
    try:
        cart = _product_service.get_shopping_cart(user_id)

        response = {
            "cart": {
                "user_id": cart.user_id,
                "items": [item.dict() for item in cart.items],
                "total_amount": cart.total_amount,
                "item_count": cart.item_count,
                "is_empty": cart.is_empty,
                "created_at": cart.created_at.isoformat(),
                "updated_at": cart.updated_at.isoformat()
            }
        }

        return json.dumps(response, default=str)

    except Exception as e:
        _logger.error(f"Get cart error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get cart: {str(e)}",
            "user_id": user_id
        })


def get_user_mandates(user_id: str) -> str:
    """
    Get all active mandates for a user.

    This tool is essential for:
    - Verifying that mandates were actually created
    - Debugging "mandate not found" issues
    - Showing users their valid mandate IDs

    Args:
        user_id: User identifier

    Returns:
        JSON string with list of active mandates
    """
    try:
        _logger.info(f"Getting active mandates for user: {user_id}")

        mandates = _mandate_service.get_user_mandates(user_id)

        response = {
            "user_id": user_id,
            "active_mandates": mandates,
            "total_count": len(mandates),
            "has_mandates": len(mandates) > 0
        }

        if not mandates:
            response["message"] = (
                "No active mandates found. "
                "Create a new mandate by adding items to cart and using enhanced_create_cart_mandate."
            )

        _logger.info(f"Found {len(mandates)} active mandate(s) for user {user_id}")
        return json.dumps(response, default=str)

    except Exception as e:
        _logger.error(f"Get user mandates error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get user mandates: {str(e)}",
            "user_id": user_id,
            "active_mandates": []
        })


def get_eligible_payment_methods(
    user_id: str,
    amount: float,
    currency: str = "USD",
    merchant_accepted_types: str = ""
) -> str:
    """
    Get eligible payment methods for a transaction.
    Per AP2 spec: Credential Provider returns methods matching transaction context.

    Args:
        user_id: User identifier
        amount: Transaction amount
        currency: Transaction currency (default: USD)
        merchant_accepted_types: Comma-separated list of accepted types (e.g., "card,wallet")

    Returns:
        JSON string with eligible payment methods
    """
    try:
        _logger.info(f"Getting eligible payment methods for user {user_id}, amount={amount} {currency}")

        accepted_types = None
        if merchant_accepted_types:
            accepted_types = [t.strip() for t in merchant_accepted_types.split(",")]

        eligible = _credential_provider.get_eligible_methods(
            user_id=user_id,
            amount=amount,
            currency=currency,
            merchant_accepted_types=accepted_types
        )

        # Get display-safe info
        methods = []
        for cred in eligible:
            methods.append({
                "credential_id": cred.credential_id,
                "type": cred.type.value,
                "brand": cred.brand,
                "last_four": cred.last_four,
                "nickname": cred.nickname,
                "is_default": cred.is_default
            })

        response = {
            "user_id": user_id,
            "eligible_methods": methods,
            "total": len(methods),
            "transaction_context": {
                "amount": amount,
                "currency": currency
            }
        }

        if not methods:
            response["message"] = "No eligible payment methods found. Please add a payment method."

        _logger.info(f"Found {len(methods)} eligible methods")
        return json.dumps(response, default=str)

    except Exception as e:
        _logger.error(f"Get eligible methods error: {str(e)}")
        return json.dumps({
            "error": f"Failed to get eligible methods: {str(e)}",
            "user_id": user_id,
            "eligible_methods": []
        })