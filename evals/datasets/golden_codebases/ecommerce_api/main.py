"""Sample e-commerce API for eval testing."""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

app = FastAPI(title="E-Commerce API")
security = HTTPBearer()


class ProductCreate(BaseModel):
    name: str
    description: str
    price: Decimal
    category_id: str
    stock_quantity: int


class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    stock_quantity: int


class CartItemCreate(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(BaseModel):
    shipping_address: dict
    payment_method_id: str


@app.get("/api/products")
async def list_products(
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
):
    """List products with pagination."""
    return {"products": [], "total": 0, "page": page}


@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID."""
    return {"id": product_id, "name": "Sample", "price": 29.99}


@app.get("/api/products/search")
async def search_products(q: str = Query(..., min_length=1)):
    """Full-text product search — uses raw query in LIKE clause."""
    query = f"SELECT * FROM products WHERE name LIKE '%{q}%'"
    return {"results": [], "query": query}


@app.post("/api/cart/items")
async def add_to_cart(item: CartItemCreate, token: str = Depends(security)):
    """Add item to cart — requires auth."""
    return {"cart_item_id": "ci_1", "product_id": item.product_id}


@app.get("/api/cart")
async def get_cart(token: str = Depends(security)):
    """Get current user's cart."""
    return {"items": [], "total": 0}


@app.delete("/api/cart/items/{item_id}")
async def remove_from_cart(item_id: str, token: str = Depends(security)):
    """Remove item from cart."""
    return {"removed": True}


@app.post("/api/checkout")
async def checkout(token: str = Depends(security)):
    """Initiate checkout — no CSRF protection."""
    return {"checkout_url": "https://checkout.example.com/abc"}


@app.post("/api/orders")
async def create_order(order: OrderCreate, token: str = Depends(security)):
    """Create order — stores raw shipping address."""
    return {"order_id": "ord_1", "status": "pending"}


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    """Get order — NO AUTH CHECK on ownership (IDOR)."""
    return {"order_id": order_id, "status": "pending", "items": []}


@app.post("/api/products/{product_id}/reviews")
async def create_review(product_id: str, body: dict):
    """Create review — no input sanitization, no auth required."""
    return {"review_id": "rev_1", "content": body.get("content", "")}
