
import os
import dotenv
import mimetypes
import aiohttp
import tempfile
import base64
import pandas as pd
from pdfminer.high_level import extract_text as extract_pdf
from docx import Document
from markdown import markdown
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from jira import JIRA, JIRAError
from typing import Optional, Dict, Any
import requests
import logging
import asyncio

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize FastMCP server
mcp = FastMCP("File and API Tools Server")

@mcp.tool()
async def read_file_or_url(path_or_url: str) -> str:
    """
    Reads content from a local file or URL and returns plain text.
    Supports .pdf, .docx, .txt, .md, .html, .json, .csv, .xlsx, and web pages.
    """
    try:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return await read_from_url(path_or_url)
        return await read_from_file(path_or_url)
    except Exception as e:
        logging.error(f"Error reading file/URL {path_or_url}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
async def read_uploaded_file(filename: str, content: str) -> str:
    """
    Reads an uploaded file given its name and content (base64 or raw text).
    Works with Claude, UIs, web apps, or any frontend uploading files.
    """
    logging.info(f"Processing uploaded file: {filename}")
    ext = os.path.splitext(filename)[1].lower()

    try:
        # Try to decode as base64 first
        if isinstance(content, str) and len(content) % 4 == 0:
            try:
                file_bytes = base64.b64decode(content, validate=True)
                logging.info("Base64 decode successful.")
            except Exception:
                # If base64 fails, treat as UTF-8 text
                file_bytes = content.encode("utf-8", errors="ignore")
        else:
            file_bytes = content.encode("utf-8", errors="ignore")
    except Exception as e:
        logging.warning(f"Content processing failed: {e}")
        return f"Error processing file content: {str(e)}"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        return await read_from_file(tmp_path)
    except Exception as e:
        return f"Error processing uploaded file: {str(e)}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

async def read_from_url(url: str) -> str:
    """Read content from a URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return f"Error: HTTP {resp.status} - {resp.reason}"
                
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    html = await resp.text()
                    return BeautifulSoup(html, "html.parser").get_text()
                
                data = await resp.read()
                suffix = mimetypes.guess_extension(content_type) or ".bin"
                
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(data)
                        tmp_path = tmp.name
                    return await read_from_file(tmp_path)
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except:
                            pass
    except Exception as e:
        return f"Error reading URL: {str(e)}"

async def read_from_file(path: str) -> str:
    """Read content from a local file."""
    try:
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
            
        ext = os.path.splitext(path)[1].lower()
        
        if ext == ".pdf":
            return extract_pdf(path)
        elif ext == ".docx":
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        elif ext in [".md", ".markdown"]:
            with open(path, "r", encoding="utf-8") as f:
                html = markdown(f.read())
                return BeautifulSoup(html, "html.parser").get_text()
        elif ext in [".txt", ".json", ".csv", ".py", ".html"]:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext in [".xlsx", ".xls"]:
            df_dict = pd.read_excel(path, sheet_name=None)
            return "\n\n".join(
                [f"Sheet: {name}\n{sheet.to_string(index=False)}" for name, sheet in df_dict.items()]
            )
        else:
            return f"Error: Unsupported file extension: {ext}"
    except Exception as e:
        return f"Error reading file: {str(e)}"
    
        
@mcp.tool()
async def save_response_to_file(content: str, filename: str) -> str:
    """
    Saves the given content to a file with the specified filename.
    """
    try:
        filepath = os.path.join("D:\OneDrive - Yethi consulting Pvt Ltd\Desktop\Designs", filename) 
        with open(filepath, "w") as f:
            f.write(content)
        return f"Response successfully saved to {filename}"
    except Exception as e:
        return f"Error saving file: {e}"

    
# -------JIRA TOOLS-------

def get_jira_client():
    """Initialize and return a JIRA client."""
    jira_url = os.getenv("JIRA_URL")
    jira_user = os.getenv("JIRA_USER")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_url, jira_user, jira_token]):
        raise EnvironmentError("Missing one or more required JIRA environment variables: JIRA_URL, JIRA_USER, JIRA_API_TOKEN")

    try:
        return JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
    except JIRAError as e:
        raise ConnectionError(f"Failed to connect to JIRA: {e}")

@mcp.tool()
def fetch_sprint_issues(sprint_id: str) -> Dict[str, Any]:
    """Fetch all Story and Task issues for a given sprint ID."""
    try:
        client = get_jira_client()
        jql = f'"Sprint" = {sprint_id} AND type IN (Story, Task)'
        issues = client.search_issues(jql, maxResults=1000)
        
        return {
            "success": True,
            "issues": [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": getattr(issue.fields.assignee, "displayName", None) if issue.fields.assignee else None
                }
                for issue in issues
            ]
        }
    except Exception as e:
        logging.error(f"Error fetching sprint issues: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def fetch_story(key: str) -> Dict[str, Any]:
    """Return a single Jira issue by key."""
    try:
        client = get_jira_client()
        issue = client.issue(key)
        
        return {
            "success": True,
            "issue": {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": getattr(issue.fields.assignee, "displayName", None) if issue.fields.assignee else None
            }
        }
    except Exception as e:
        logging.error(f"Error fetching story {key}: {e}")
        return {"success": False, "error": str(e)}

# --------- website's-AI API TOOLS ---------
API_BASE = "WEBSITE'S URL"

def make_request(method: str, endpoint: str, payload: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request with proper error handling."""
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.request(
            method=method,
            url=endpoint,
            json=payload,
            params=params,
            headers=headers,
            timeout=30  # Add timeout
        )
        response.raise_for_status()
        
        # Try to parse JSON, fallback to text if it fails
        try:
            return {"success": True, "data": response.json()}
        except:
            return {"success": True, "data": response.text}
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {method} {endpoint} - {e}")
        return {
            "success": False,
            "error": str(e),
            "url": endpoint,
            "method": method
        }
@mcp.tool()
async def create_design(project_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Create Design."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design"
    return make_request("POST", endpoint, payload)
 
@mcp.tool()
async def get_all_designs(project_id: str) -> Dict[str, Any]:
    """Get All Designs."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def update_design(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Update Design."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}"
    return make_request("PUT", endpoint, payload)
 
@mcp.tool()
async def delete_design(project_id: str, design_id: str) -> Dict[str, Any]:
    """Delete Design."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}"
    return make_request("DELETE", endpoint)
 
@mcp.tool()
async def filter_cm(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Filter Cm."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}"
    return make_request("POST", endpoint, payload)
 
@mcp.tool()
async def get_coverage_matrix(project_id: str, design_id: str) -> Dict[str, Any]:
    """Process List."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/coveragematrix"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def get_design_summary(project_id: str, design_id: str) -> Dict[str, Any]:
    """Design Summary."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/summary"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def get_process(project_id: str, design_id: str) -> Dict[str, Any]:
    """Get Process."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/process"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def generate_process(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate Process."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/process"
    return make_request("POST", endpoint, payload)
 
@mcp.tool()
async def update_process(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Update Process."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/process"
    return make_request("PUT", endpoint, payload)
 
@mcp.tool()
async def delete_process(project_id: str, design_id: str) -> Dict[str, Any]:
    """Delete Process."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/process"
    return make_request("DELETE", endpoint)
 
@mcp.tool()
async def get_scenarios(project_id: str, design_id: str) -> Dict[str, Any]:
    """Fetch Scenario Data."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/scenarios"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def generate_scenarios(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate Scenario."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/scenarios"
    return make_request("POST", endpoint, payload)
 
@mcp.tool()
async def update_scenarios(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Update Scenario."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/scenarios"
    return make_request("PUT", endpoint, payload)
 
@mcp.tool()
async def delete_scenarios(project_id: str, design_id: str) -> Dict[str, Any]:
    """Delete Scenario."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/scenarios"
    return make_request("DELETE", endpoint)
 
@mcp.tool()
async def get_testcases(project_id: str, design_id: str) -> Dict[str, Any]:
    """Fetch Test Cases."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/testcases"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def generate_testcases(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate Test Cases."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/testcases"
    return make_request("POST", endpoint, payload)
 
@mcp.tool()
async def update_testcases(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Update Test Cases."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/testcases"
    return make_request("PUT", endpoint, payload)
 
@mcp.tool()
async def delete_testcases(project_id: str, design_id: str) -> Dict[str, Any]:
    """Delete Test Case."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/testcases"
    return make_request("DELETE", endpoint)
 
@mcp.tool()
async def register_testcases(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Register Application Test Cases."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/testcases/register"
    return make_request("PUT", endpoint, payload)
 
@mcp.tool()
async def get_teststeps(project_id: str, design_id: str) -> Dict[str, Any]:
    """Fetch Test Steps."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/teststeps"
    return make_request("GET", endpoint)
 
@mcp.tool()
async def post_teststeps(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Create Test Steps."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/teststeps"
    return make_request("POST", endpoint, payload)
 
@mcp.tool()
async def update_teststeps(project_id: str, design_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Update Test Steps."""
    endpoint = f"{API_BASE}/api/project/{project_id}/design/{design_id}/teststeps"
    return make_request("PUT", endpoint, payload)
@mcp.tool()
async def generate_process(project_id: str, design_id: Optional[str] = None, payload: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate a process."""
    endpoint = f"{API_BASE}/generate/process/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("POST", endpoint, payload)

@mcp.tool()
async def get_design_summary(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch design summary."""
    endpoint = f"{API_BASE}/design_summary/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_design_code(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch design code."""
    endpoint = f"{API_BASE}/design_code/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_design_code_zip(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch zipped design code."""
    endpoint = f"{API_BASE}/design_code_zip/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_prompt_summary(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch prompt summary."""
    endpoint = f"{API_BASE}/prompt_summary/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_requirement_design_mapping(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Get requirement to design mapping."""
    endpoint = f"{API_BASE}/requirement_design_mapping/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_requirement_summary(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Get requirement summary."""
    endpoint = f"{API_BASE}/requirement_summary/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_design_insight(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Get design insights."""
    endpoint = f"{API_BASE}/design_insight/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

@mcp.tool()
async def get_quality_report(project_id: str, design_id: Optional[str] = None) -> Dict[str, Any]:
    """Get quality report."""
    endpoint = f"{API_BASE}/quality_report/{project_id}"
    if design_id:
        endpoint += f"/{design_id}"
    return make_request("GET", endpoint)

# Health check tool
@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check if the API server is accessible."""
    endpoint = f"{API_BASE}/health"
    try:
        response = requests.get(endpoint, timeout=10)
        return {
            "success": True,
            "status": response.status_code,
            "message": "API server is accessible"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "API server is not accessible"
        }

if __name__ == "__main__":
    # Run the server
    mcp.run()

    
