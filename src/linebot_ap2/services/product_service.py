"""Product Service with enhanced search and recommendation capabilities."""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models.product import (
    Product, ProductCategory, ProductSearchFilters, ProductSearchResult,
    ShoppingCart, ShoppingCartItem, ProductStatus
)
from ..common.logger import setup_logger


class ProductService:
    """Enhanced product service with search and recommendation features."""
    
    def __init__(self):
        self.logger = setup_logger("product_service")
        self.products: Dict[str, Product] = {}
        self.shopping_carts: Dict[str, ShoppingCart] = {}
        
        # Initialize demo products
        self._init_demo_products()
        
        self.logger.info("✓ Product service initialized with demo products")
    
    def _init_demo_products(self):
        """Initialize demo product catalog."""
        
        demo_products = [
            Product(
                id="prod_001",
                name="iPhone 15 Pro",
                price=999.00,
                currency="USD",
                description="Latest Apple iPhone with advanced camera system and A17 Pro chip",
                category=ProductCategory.PHONES,
                stock=10,
                brand="Apple",
                model="iPhone 15 Pro",
                specifications={
                    "display": "6.1-inch Super Retina XDR",
                    "storage": "128GB",
                    "camera": "48MP Main + 12MP Ultra Wide + 12MP Telephoto",
                    "chip": "A17 Pro",
                    "battery": "Up to 23 hours video playback"
                },
                tags=["5G", "Premium", "Camera", "iOS"]
            ),
            Product(
                id="prod_002",
                name="MacBook Air M3",
                price=1299.00,
                currency="USD",
                description="Lightweight laptop with M3 chip, perfect for work and creativity",
                category=ProductCategory.COMPUTERS,
                stock=5,
                brand="Apple",
                model="MacBook Air M3",
                specifications={
                    "display": "13.6-inch Liquid Retina",
                    "chip": "Apple M3",
                    "memory": "8GB unified memory",
                    "storage": "256GB SSD",
                    "battery": "Up to 18 hours"
                },
                tags=["Laptop", "M3", "Portable", "macOS"]
            ),
            Product(
                id="prod_003",
                name="AirPods Pro (2nd generation)",
                price=249.00,
                currency="USD",
                description="Wireless earbuds with Active Noise Cancellation and Spatial Audio",
                category=ProductCategory.AUDIO,
                stock=15,
                brand="Apple",
                model="AirPods Pro 2",
                specifications={
                    "chip": "H2 chip",
                    "battery": "Up to 6 hours listening time",
                    "features": "Active Noise Cancellation, Transparency mode",
                    "charging": "MagSafe charging case"
                },
                tags=["Wireless", "ANC", "Premium", "Audio"]
            ),
            Product(
                id="prod_004",
                name="Apple Watch Series 9",
                price=399.00,
                currency="USD",
                description="Advanced smartwatch with health monitoring and fitness tracking",
                category=ProductCategory.WEARABLES,
                stock=8,
                brand="Apple",
                model="Watch Series 9",
                specifications={
                    "display": "45mm Always-On Retina",
                    "chip": "S9 SiP",
                    "sensors": "Blood Oxygen, ECG, Temperature",
                    "battery": "Up to 18 hours",
                    "connectivity": "GPS + Cellular"
                },
                tags=["Health", "Fitness", "Smart", "Wearable"]
            ),
            Product(
                id="prod_005",
                name="iPad Pro 12.9-inch",
                price=1099.00,
                currency="USD",
                description="Professional tablet with M2 chip and Liquid Retina XDR display",
                category=ProductCategory.TABLETS,
                stock=6,
                brand="Apple",
                model="iPad Pro 12.9",
                specifications={
                    "display": "12.9-inch Liquid Retina XDR",
                    "chip": "Apple M2",
                    "storage": "128GB",
                    "camera": "12MP Wide + 10MP Ultra Wide",
                    "connectivity": "Wi-Fi 6E + 5G"
                },
                tags=["Professional", "M2", "Tablet", "Creative"]
            ),
            Product(
                id="prod_006",
                name="Magic Keyboard for iPad Pro",
                price=349.00,
                currency="USD",
                description="Backlit keyboard with trackpad for iPad Pro",
                category=ProductCategory.ACCESSORIES,
                stock=12,
                brand="Apple",
                model="Magic Keyboard",
                specifications={
                    "compatibility": "iPad Pro 12.9-inch",
                    "features": "Backlit keys, trackpad, USB-C pass-through",
                    "material": "Premium materials"
                },
                tags=["Keyboard", "Trackpad", "Productivity", "Accessory"]
            )
        ]
        
        for product in demo_products:
            self.products[product.id] = product
    
    def search_products(
        self,
        query: str = "",
        category: str = "",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        brand: str = "",
        in_stock_only: bool = True
    ) -> ProductSearchResult:
        """Enhanced product search with multiple filters."""
        
        # Create search filters
        filters = ProductSearchFilters(
            query=query.strip() if query else None,
            category=ProductCategory(category) if category else None,
            min_price=min_price,
            max_price=max_price,
            brand=brand.strip() if brand else None,
            in_stock_only=in_stock_only
        )
        
        # Apply filters
        results = []
        
        for product in self.products.values():
            if self._matches_filters(product, filters):
                results.append(product)
        
        # Sort by relevance (simplified scoring)
        if query:
            results.sort(key=lambda p: self._calculate_relevance_score(p, query), reverse=True)
        else:
            results.sort(key=lambda p: p.name)
        
        return ProductSearchResult(
            products=results,
            total=len(results),
            search_query=query,
            category=category,
            filters_applied=filters.to_dict()
        )
    
    def _matches_filters(self, product: Product, filters: ProductSearchFilters) -> bool:
        """Check if product matches search filters."""
        
        # Stock filter
        if filters.in_stock_only and not product.is_available:
            return False
        
        # Query filter (search in name, description, brand, tags)
        if filters.query:
            query_lower = filters.query.lower()
            searchable_text = " ".join([
                product.name.lower(),
                product.description.lower(),
                product.brand.lower() if product.brand else "",
                " ".join(product.tags).lower()
            ])
            if query_lower not in searchable_text:
                return False
        
        # Category filter
        if filters.category and product.category != filters.category:
            return False
        
        # Price filters
        if filters.min_price is not None and product.price < filters.min_price:
            return False
        
        if filters.max_price is not None and product.price > filters.max_price:
            return False
        
        # Brand filter
        if filters.brand and (not product.brand or 
                             filters.brand.lower() not in product.brand.lower()):
            return False
        
        return True
    
    def _calculate_relevance_score(self, product: Product, query: str) -> float:
        """Calculate relevance score for search results."""
        score = 0.0
        query_lower = query.lower()
        
        # Name match (highest weight)
        if query_lower in product.name.lower():
            score += 10.0
            if product.name.lower().startswith(query_lower):
                score += 5.0
        
        # Brand match
        if product.brand and query_lower in product.brand.lower():
            score += 5.0
        
        # Description match
        if query_lower in product.description.lower():
            score += 2.0
        
        # Tag matches
        for tag in product.tags:
            if query_lower in tag.lower():
                score += 1.0
        
        # Boost popular/available products
        if product.is_available:
            score += 1.0
        
        return score
    
    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed product information."""
        
        product = self.products.get(product_id)
        if not product:
            return None
        
        return {
            "product": product.dict(),
            "availability": {
                "status": product.status.value,
                "stock": product.stock,
                "estimated_delivery": "2-3 business days" if product.is_available else "Out of stock"
            },
            "recommendations": self._get_related_products(product_id, limit=3)
        }
    
    def _get_related_products(self, product_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get related products based on category and brand."""
        
        base_product = self.products.get(product_id)
        if not base_product:
            return []
        
        related = []
        
        for product in self.products.values():
            if (product.id != product_id and 
                product.is_available and 
                (product.category == base_product.category or 
                 product.brand == base_product.brand)):
                
                related.append({
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "currency": product.currency,
                    "category": product.category.value
                })
        
        return related[:limit]
    
    def get_recommendations(
        self,
        user_preferences: str = "",
        category: str = "",
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """Get personalized product recommendations."""
        
        recommendations = []
        
        if user_preferences:
            # Search-based recommendations
            search_result = self.search_products(query=user_preferences)
            recommendations.extend([p.dict() for p in search_result.products[:limit]])
        elif category:
            # Category-based recommendations
            search_result = self.search_products(category=category)
            recommendations.extend([p.dict() for p in search_result.products[:limit]])
        else:
            # Default recommendations (popular/featured products)
            featured_products = [
                self.products.get("prod_001"),  # iPhone
                self.products.get("prod_002"),  # MacBook
                self.products.get("prod_003"),  # AirPods
                self.products.get("prod_004"),  # Apple Watch
            ]
            
            recommendations = [
                p.dict() for p in featured_products 
                if p and p.is_available
            ][:limit]
        
        return recommendations
    
    def get_shopping_cart(self, user_id: str) -> ShoppingCart:
        """Get or create shopping cart for user."""
        
        if user_id not in self.shopping_carts:
            self.shopping_carts[user_id] = ShoppingCart(user_id=user_id)
        
        return self.shopping_carts[user_id]
    
    def add_to_cart(
        self,
        user_id: str,
        product_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """Add product to shopping cart."""
        
        product = self.products.get(product_id)
        if not product:
            return {"error": "Product not found"}
        
        if not product.is_available:
            return {"error": "Product out of stock"}
        
        if product.stock < quantity:
            return {"error": f"Insufficient stock. Available: {product.stock}"}
        
        cart = self.get_shopping_cart(user_id)
        success = cart.add_item(product, quantity)
        
        if success:
            return {
                "success": True,
                "cart": {
                    "user_id": cart.user_id,
                    "items": [item.dict() for item in cart.items],
                    "total_amount": cart.total_amount,
                    "item_count": cart.item_count
                }
            }
        else:
            return {"error": "Failed to add item to cart"}
    
    def create_cart_mandate_data(self, user_id: str) -> Dict[str, Any]:
        """Create cart mandate data for payment processing."""
        
        cart = self.get_shopping_cart(user_id)
        
        if cart.is_empty:
            return {"error": "Cart is empty"}
        
        # Prepare items for mandate
        mandate_items = []
        
        for item in cart.items:
            mandate_items.append({
                "product_id": item.product_id,
                "name": item.product_name,
                "price": item.price,
                "quantity": item.quantity,
                "subtotal": item.subtotal
            })
        
        return {
            "user_id": user_id,
            "items": mandate_items,
            "total_amount": cart.total_amount,
            "currency": "USD",
            "item_count": cart.item_count
        }
    
    def reduce_product_stock(self, product_id: str, quantity: int) -> bool:
        """Reduce product stock after successful payment."""
        
        product = self.products.get(product_id)
        if product:
            return product.reduce_stock(quantity)
        return False
    
    def get_product_categories(self) -> List[Dict[str, Any]]:
        """Get all available product categories."""
        
        categories = {}
        
        for product in self.products.values():
            category = product.category.value
            if category not in categories:
                categories[category] = {
                    "name": category,
                    "count": 0,
                    "products": []
                }
            
            categories[category]["count"] += 1
            if product.is_available:
                categories[category]["products"].append({
                    "id": product.id,
                    "name": product.name,
                    "price": product.price
                })
        
        return list(categories.values())