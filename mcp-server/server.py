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



# import os
# import dotenv
# import mimetypes
# import aiohttp
# import tempfile
# import base64
# import pandas as pd
# from pdfminer.high_level import extract_text as extract_pdf
# from docx import Document
# from markdown import markdown
# from bs4 import BeautifulSoup
# from fastmcp import FastMCP, tool
# from jira import JIRA, JIRAError
# from typing import Optional, Dict
# import requests
# import logging
 
# # Load environment variables
# dotenv.load_dotenv()
 
# mcp = FastMCP()
 
# @mcp.tool()
# async def read_file_or_url(path_or_url: str) -> str:
#     """
#     Reads content from a local file or URL and returns plain text.
#     Supports .pdf, .docx, .txt, .md, .html, .json, .csv, .xlsx, and web pages.
#     """
#     if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
#         return await read_from_url(path_or_url)
#     return await read_from_file(path_or_url)
 
# @mcp.tool()
# async def read_uploaded_file(filename: str, content: str) -> str:
#     """
#     Reads an uploaded file given its name and content (base64 or raw text).
#     Works with Claude, UIs, web apps, or any frontend uploading files.
#     """
#     logging.info(f"Processing uploaded file: {filename}")
#     ext = os.path.splitext(filename)[1].lower()
 
#     # Try decoding base64 first. If it fails, treat as UTF-8 text.
#     try:
#         if isinstance(content, str) and not content.strip().startswith(('{', '[', '<!DOCTYPE')) and len(content) % 4 == 0:
#             file_bytes = base64.b64decode(content, validate=True)
#             logging.info("Base64 decode successful.")
#         else:
#             raise ValueError("Not base64 — fallback to text")
#     except Exception as e:
#         logging.warning(f"Base64 decode failed, treating content as UTF-8 text: {e}")
#         file_bytes = content.encode("utf-8", errors="ignore")
 
#     tmp_path = None
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
#             tmp.write(file_bytes)
#             tmp_path = tmp.name
#         logging.info(f"Temporary file written to: {tmp_path}")
#         return await read_from_file(tmp_path)
#     except Exception as e:
#         logging.error(f"Failed to process uploaded file {filename}: {e}")
#         raise
#     finally:
#         if tmp_path and os.path.exists(tmp_path):
#             os.remove(tmp_path)
# async def read_from_url(url: str) -> str:
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url) as resp:
#             content_type = resp.headers.get("Content-Type", "")
#             if "text/html" in content_type:
#                 html = await resp.text()
#                 return BeautifulSoup(html, "html.parser").get_text()
#             data = await resp.read()
#             suffix = mimetypes.guess_extension(content_type) or ""
#             with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
#                 tmp.write(data)
#                 tmp_path = tmp.name
#             return await read_from_file(tmp_path)
 
 
# async def read_from_file(path: str) -> str:
#     ext = os.path.splitext(path)[1].lower()
#     if ext == ".pdf":
#         return extract_pdf(path)
#     elif ext == ".docx":
#         return "\n".join(p.text for p in Document(path).paragraphs)
#     elif ext in [".md", ".markdown"]:
#         with open(path, "r", encoding="utf-8") as f:
#             return BeautifulSoup(markdown(f.read()), "html.parser").get_text()
#     elif ext in [".txt", ".json", ".csv", ".py", ".html"]:
#         with open(path, "r", encoding="utf-8") as f:
#             return f.read()
#     elif ext in [".xlsx", ".xls"]:
#         df = pd.read_excel(path, sheet_name=None)
#         return "\n\n".join(
#             [f"Sheet: {name}\n{sheet.to_string(index=False)}" for name, sheet in df.items()]
#         )
#     else:
#         raise Exception(f"Unsupported file extension: {ext}")
# def get_jira_client():
#     """Initialize and return a JIRA client."""
#     jira_url = os.getenv("JIRA_URL")
#     jira_user = os.getenv("JIRA_USER")
#     jira_token = os.getenv("JIRA_API_TOKEN")
#     if not all([jira_url, jira_user, jira_token]):
#         raise EnvironmentError("Missing one or more required JIRA environment variables.")
#     try:
#         return JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
#     except JIRAError as e:
#         raise ConnectionError(f"Failed to connect to JIRA: {e}")
 
# @mcp.tool()
# def fetch_sprint_issues(sprint_id):
#     """Fetch all Story and Task issues for a given sprint ID."""
#     client = get_jira_client()
#     jql = f'"Sprint" = {sprint_id} AND type IN (Story, Task)'
#     try:
#         issues = client.search_issues(jql, maxResults=1000)
#         return [
#             {
#                 "key": issue.key,
#                 "summary": issue.fields.summary,
#                 "status": issue.fields.status.name,
#                 "assignee": getattr(issue.fields.assignee, "displayName", None)
#             }
#             for issue in issues
#         ]
#     except JIRAError as e:
#         return {"error": str(e)}
 
# @mcp.tool()
# def fetch_story(key):
#     """Return a single Jira issue by key."""
#     client = get_jira_client()
#     try:
#         issue = client.issue(key)
#         return {
#             "key": issue.key,
#             "summary": issue.fields.summary,
#             "status": issue.fields.status.name,
#             "assignee": getattr(issue.fields.assignee, "displayName", None)
#         }
#     except JIRAError as e:
#         return {"error": str(e)}
 
 
# API_BASE = "http://192.168.16.173:8000"
 
# API_LIST = [
#     {
#         "name": "generate_process",
#         "method": "POST",
#         "url": "/generate/process/{project_id}/{design_id}",
#         "description": "Generate a process"
#     },
#     {
#         "name": "get_design_summary",
#         "method": "GET",
#         "url": "/design_summary/{project_id}/{design_id}",
#         "description": "Fetch design summary"
#     },
#     {
#         "name": "get_design_code",
#         "method": "GET",
#         "url": "/design_code/{project_id}/{design_id}",
#         "description": "Fetch design code"
#     },
#     {
#         "name": "get_design_code_zip",
#         "method": "GET",
#         "url": "/design_code_zip/{project_id}/{design_id}",
#         "description": "Fetch zipped design code"
#     },
#     {
#         "name": "get_prompt_summary",
#         "method": "GET",
#         "url": "/prompt_summary/{project_id}/{design_id}",
#         "description": "Fetch prompt summary"
#     },
#     {
#         "name": "get_requirement_design_mapping",
#         "method": "GET",
#         "url": "/requirement_design_mapping/{project_id}/{design_id}",
#         "description": "Get requirement to design mapping"
#     },
#     {
#         "name": "get_requirement_summary",
#         "method": "GET",
#         "url": "/requirement_summary/{project_id}/{design_id}",
#         "description": "Get requirement summary"
#     },
#     {
#         "name": "get_design_insight",
#         "method": "GET",
#         "url": "/design_insight/{project_id}/{design_id}",
#         "description": "Get design insights"
#     },
#     {
#         "name": "get_quality_report",
#         "method": "GET",
#         "url": "/quality_report/{project_id}/{design_id}",
#         "description": "Get quality report"
#     }
# ]
 
# def make_api_tool(name, method, url, description):
#     @mcp.tool(name=name, description=description)
#     async def dynamic_tool(
#         project_id: str,
#         design_id: Optional[str] = None,
#         payload: Optional[Dict] = None,
#         params: Optional[Dict] = None
#     ):
#         full_url = API_BASE + url.format(project_id=project_id, design_id=design_id or "")
#         headers = {"Content-Type": "application/json"}
 
#         try:
#             response = requests.request(
#                 method=method,
#                 url=full_url,
#                 json=payload,
#                 params=params,
#                 headers=headers
#             )
#             response.raise_for_status()
#             return response.json()
#         except Exception as e:
#             return {"error": str(e), "url": full_url, "method": method}
 
#     return dynamic_tool
 
# # Register all API tools
# for api in API_LIST:
#     make_api_tool(
#         name=api["name"],
#         method=api["method"],
#         url=api["url"],
#         description=api["description"]
#     )
# if __name__ == "__main__":
#     mcp.run()