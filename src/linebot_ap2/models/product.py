"""Product-related data models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ProductCategory(str, Enum):
    """Product categories."""
    ELECTRONICS = "Electronics"
    COMPUTERS = "Computers" 
    AUDIO = "Audio"
    WEARABLES = "Wearables"
    PHONES = "Phones"
    TABLETS = "Tablets"
    ACCESSORIES = "Accessories"


class ProductStatus(str, Enum):
    """Product availability status."""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


class Product(BaseModel):
    """Product model."""
    id: str
    name: str
    price: float = Field(ge=0, description="Price must be non-negative")
    currency: str = "USD"
    description: str
    category: ProductCategory
    stock: int = Field(ge=0, description="Stock must be non-negative")
    image_url: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def status(self) -> ProductStatus:
        """Get product availability status."""
        return ProductStatus.IN_STOCK if self.stock > 0 else ProductStatus.OUT_OF_STOCK
    
    @property
    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return self.stock > 0
    
    def reduce_stock(self, quantity: int) -> bool:
        """Reduce stock by quantity. Returns True if successful."""
        if self.stock >= quantity:
            self.stock -= quantity
            self.updated_at = datetime.now()
            return True
        return False
    
    def increase_stock(self, quantity: int) -> None:
        """Increase stock by quantity."""
        self.stock += quantity
        self.updated_at = datetime.now()


class ProductSearchFilters(BaseModel):
    """Product search filters."""
    query: Optional[str] = None
    category: Optional[ProductCategory] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    brand: Optional[str] = None
    in_stock_only: bool = True
    tags: List[str] = Field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filters to dictionary."""
        return {k: v for k, v in self.dict().items() if v is not None}


class ProductSearchResult(BaseModel):
    """Product search result."""
    products: List[Product]
    total: int
    search_query: Optional[str] = None
    category: Optional[str] = None
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return self.total > 0


class ShoppingCartItem(BaseModel):
    """Shopping cart item."""
    product_id: str
    product_name: str
    price: float
    quantity: int = Field(ge=1)
    subtotal: float
    added_at: datetime = Field(default_factory=datetime.now)
    
    def update_quantity(self, new_quantity: int) -> None:
        """Update item quantity and recalculate subtotal."""
        self.quantity = max(1, new_quantity)
        self.subtotal = self.price * self.quantity


class ShoppingCart(BaseModel):
    """Shopping cart model."""
    user_id: str
    items: List[ShoppingCartItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def total_amount(self) -> float:
        """Calculate total cart amount."""
        return sum(item.subtotal for item in self.items)
    
    @property
    def item_count(self) -> int:
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items)
    
    @property
    def is_empty(self) -> bool:
        """Check if cart is empty."""
        return len(self.items) == 0
    
    def add_item(self, product: Product, quantity: int = 1) -> bool:
        """Add item to cart or update quantity if exists."""
        # Check if item already exists
        for item in self.items:
            if item.product_id == product.id:
                item.update_quantity(item.quantity + quantity)
                self.updated_at = datetime.now()
                return True
        
        # Add new item
        cart_item = ShoppingCartItem(
            product_id=product.id,
            product_name=product.name,
            price=product.price,
            quantity=quantity,
            subtotal=product.price * quantity
        )
        self.items.append(cart_item)
        self.updated_at = datetime.now()
        return True
    
    def remove_item(self, product_id: str) -> bool:
        """Remove item from cart."""
        for i, item in enumerate(self.items):
            if item.product_id == product_id:
                del self.items[i]
                self.updated_at = datetime.now()
                return True
        return False
    
    def update_item_quantity(self, product_id: str, quantity: int) -> bool:
        """Update quantity of specific item."""
        for item in self.items:
            if item.product_id == product_id:
                if quantity <= 0:
                    return self.remove_item(product_id)
                item.update_quantity(quantity)
                self.updated_at = datetime.now()
                return True
        return False
    
    def clear(self) -> None:
        """Clear all items from cart."""
        self.items.clear()
        self.updated_at = datetime.now()