import asyncio
import json
import os
from typing import Optional
import httpx
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("FastAPI Tools")

# HTTP client for API calls
http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client with authentication"""
    global http_client
    if http_client is None:
        # api_key = os.getenv("FASTAPI_API_KEY")
        # headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoYXJpbmkuYkB5ZXRoaS5pbiIsImV4cCI6MTc1MzIyOTg4Mn0.GXBlDwwXuMRialob5SJKFAtaLQR7JoA5QW0W0kOn7YQ"} 
        http_client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers
        )
    return http_client

def get_base_url() -> str:
    """Get the FastAPI base URL"""
    return os.getenv("FASTAPI_BASE_URL", "http://192.168.17.153:8000").rstrip('/')

@mcp.tool()
async def get_users(tenant_id: str, project_id: Optional[int] = None) -> str:
    """
    Retrieve a list of all users from the FastAPI backend.
    Requires admin role and valid authentication.
    
    Args:
        tenant_id: The tenant ID to filter users by
        project_id: Optional project ID to exclude the project creator from results
    
    Returns:
        JSON string containing the list of users with their details (id, names, email, role, status)
    """
    client = get_http_client()
    base_url = get_base_url()
    
    # Set up headers with tenant ID
    headers = {"Tenent_ID": tenant_id}
    
    # Set up query parameters
    params = {}
    if project_id is not None:
        params["project_id"] = project_id
    
    response = await client.get(
        f"{base_url}/api/user", 
        params=params,
        headers=headers
    )
    response.raise_for_status()
    return json.dumps(response.json(), indent=2)

@mcp.tool()
async def get_projects(tenant_id: str) -> str:
    """
    Retrieve all existing projects for a tenant.
    Projects are returned sorted by creation date (newest first).
    
    Args:
        tenant_id: The tenant ID to filter projects by
    
    Returns:
        JSON string containing the list of projects sorted by created_on date (newest first)
    """
    client = get_http_client()
    base_url = get_base_url()
    
    # Set up headers with tenant ID
    headers = {"Tenent_ID": tenant_id}
    
    response = await client.get(
        f"{base_url}/api/projects",  # Adjust this path to match your actual route
        headers=headers
    )
    response.raise_for_status()
    return json.dumps(response.json(), indent=2)

# @mcp.tool()
# async def get_user_by_id(user_id: str) -> str:
#     """
#     Retrieve a specific user by their ID.
    
#     Args:
#         user_id: The unique identifier for the user
    
#     Returns:
#         JSON string containing the user details
#     """
#     client = get_http_client()
#     base_url = get_base_url()
    
#     response = await client.get(f"{base_url}/users/{user_id}")
#     response.raise_for_status()
#     return json.dumps(response.json(), indent=2)

# @mcp.tool()
# async def create_user(name: str, email: str, age: Optional[int] = None) -> str:
#     """
#     Create a new user in the FastAPI backend.
    
#     Args:
#         name: User's full name
#         email: User's email address
#         age: User's age (optional)
    
#     Returns:
#         JSON string containing the created user details
#     """
#     client = get_http_client()
#     base_url = get_base_url()
    
#     user_data = {"name": name, "email": email}
#     if age is not None:
#         user_data["age"] = age
    
#     response = await client.post(f"{base_url}/users", json=user_data)
#     response.raise_for_status()
#     return json.dumps(response.json(), indent=2)

# @mcp.tool()
# async def update_user(
#     user_id: str, 
#     name: Optional[str] = None, 
#     email: Optional[str] = None, 
#     age: Optional[int] = None
# ) -> str:
#     """
#     Update an existing user's information.
    
#     Args:
#         user_id: The unique identifier for the user
#         name: User's full name (optional)
#         email: User's email address (optional)  
#         age: User's age (optional)
    
#     Returns:
#         JSON string containing the updated user details
#     """
#     client = get_http_client()
#     base_url = get_base_url()
    
#     user_data = {}
#     if name is not None:
#         user_data["name"] = name
#     if email is not None:
#         user_data["email"] = email
#     if age is not None:
#         user_data["age"] = age
    
#     response = await client.put(f"{base_url}/users/{user_id}", json=user_data)
#     response.raise_for_status()
#     return json.dumps(response.json(), indent=2)

# @mcp.tool()
# async def delete_user(user_id: str) -> str:
#     """
#     Delete a user from the FastAPI backend.
    
#     Args:
#         user_id: The unique identifier for the user to delete
    
#     Returns:
#         Success message
#     """
#     client = get_http_client()
#     base_url = get_base_url()
    
#     response = await client.delete(f"{base_url}/users/{user_id}")
#     response.raise_for_status()
#     return f"User {user_id} deleted successfully"

# # Add more tools for your other FastAPI endpoints
# @mcp.tool()
# async def get_products(category: Optional[str] = None, limit: int = 20) -> str:
#     """
#     Retrieve products from the FastAPI backend.
    
#     Args:
#         category: Filter products by category (optional)
#         limit: Maximum number of products to return (default: 20)
    
#     Returns:
#         JSON string containing the list of products
#     """
#     client = get_http_client()
#     base_url = get_base_url()
    
#     params = {"limit": limit}
#     if category:
#         params["category"] = category
    
#     response = await client.get(f"{base_url}/products", params=params)
#     response.raise_for_status()
#     return json.dumps(response.json(), indent=2)

# @mcp.tool()
# async def create_order(user_id: str, product_ids: list[str], quantities: list[int]) -> str:
#     """
#     Create a new order in the FastAPI backend.
    
#     Args:
#         user_id: The ID of the user placing the order
#         product_ids: List of product IDs to order
#         quantities: List of quantities for each product (must match product_ids length)
    
#     Returns:
#         JSON string containing the created order details
#     """
#     client = get_http_client()
#     base_url = get_base_url()
    
#     if len(product_ids) != len(quantities):
#         raise ValueError("product_ids and quantities must have the same length")
    
#     order_data = {
#         "user_id": user_id,
#         "items": [
#             {"product_id": pid, "quantity": qty} 
#             for pid, qty in zip(product_ids, quantities)
#         ]
#     }
    
#     response = await client.post(f"{base_url}/orders", json=order_data)
#     response.raise_for_status()
#     return json.dumps(response.json(), indent=2)

async def cleanup():
    """Clean up HTTP client on shutdown"""
    global http_client
    if http_client:
        await http_client.aclose()

if __name__ == "__main__":
    # Set up cleanup on exit
    import atexit
    atexit.register(lambda: asyncio.run(cleanup()))
    
    # Run the MCP server
    mcp.run()