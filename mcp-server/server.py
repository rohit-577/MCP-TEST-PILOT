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

def get_http_client(tenant_id) -> httpx.AsyncClient:
    """Get or create HTTP client with authentication"""
    global http_client
    if http_client is None:
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoYXJpbmkuYkB5ZXRoaS5pbiIsImV4cCI6MTc1MzM5NTgzOX0.I8cvgG6XugcwRSRVrt35NTg-9q6m_WotywAlu1Gfdj4",
            "accept": "application/json",
            "Tenent-ID": tenant_id
        }
        http_client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers
        )
    return http_client

def get_base_url() -> str:
    """Get the FastAPI base URL"""
    return os.getenv("FASTAPI_BASE_URL", "http://192.168.16.65:8000").rstrip('/')

@mcp.tool()
async def get_users(tenant_id: str, project_id: Optional[int] = None) -> str:
    """
    Retrieve a list of all users for a given tenant from the FastAPI backend.
    Requires admin role and valid authentication.

    Args:
        tenant_id: The tenant ID to filter users by
        project_id: Optional project ID to exclude the project creator from results

    Returns:
        JSON string containing the list of users with their details
    """
    client = get_http_client(tenant_id)
    base_url = get_base_url()
    
    params = {"project_id": project_id} if project_id else {}

    response = await client.get(f"{base_url}/api/user", params=params)
    response.raise_for_status()
    return json.dumps(response.json(), indent=2)

@mcp.tool()
async def get_projects(tenant_id: str) -> str:
    """
    Retrieve all existing projects for a tenant.
    Projects are sorted on creation date (newest first).

    Args:
        tenant_id: The tenant ID to filter projects by

    Returns:
        JSON string containing the list of projects sorted by created_on date (newest first)
    """
    client = get_http_client(tenant_id)
    base_url = get_base_url()

    response = await client.get(f"{base_url}/api/project")
    response.raise_for_status()
    return json.dumps(response.json(), indent=2)

async def cleanup():
    """Clean up HTTP client on shutdown"""
    global http_client
    if http_client:
        await http_client.aclose()

if __name__ == "__main__":
    mcp.run()
