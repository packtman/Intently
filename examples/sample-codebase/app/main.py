"""Sample FastAPI application for testing security review."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Sample API")
security = HTTPBearer()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user - NO AUTH REQUIRED."""
    # TODO: Add validation
    return {"id": "123", "email": user.email, "name": user.name}


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID - NO AUTH CHECK ON OWNERSHIP."""
    # Potential IDOR vulnerability
    return {"id": user_id, "email": "test@example.com", "name": "Test User"}


@app.get("/api/admin/users")
async def list_all_users(token: str = Depends(security)):
    """List all users - requires auth."""
    return [{"id": "1", "email": "admin@example.com"}]


@app.post("/api/data/export")
async def export_data(query: str):
    """Export data - potential SQL injection."""
    # Dangerous: using raw query
    result = f"SELECT * FROM users WHERE {query}"
    return {"query": result}

