import os
import dotenv
from jira import JIRA, JIRAError
from fastmcp import FastMCP
import mimetypes
import aiohttp
import tempfile
import base64
import pandas as pd
from pdfminer.high_level import extract_text as extract_pdf
from docx import Document
from markdown import markdown
from bs4 import BeautifulSoup
import logging
 
mcp = FastMCP("JIRA-MCP")
 
dotenv.load_dotenv()
 
@mcp.tool()
async def read_file_or_url(path_or_url: str) -> str:
    """
    Reads content from a local file or URL and returns plain text.
    Supports .pdf, .docx, .txt, .md, .html, .json, .csv, .xlsx, and web pages.
    """
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return await read_from_url(path_or_url)
    return await read_from_file(path_or_url)
 
@mcp.tool()
async def read_uploaded_file(filename: str, content: str) -> str:
    """
    Reads an uploaded file given its name and content (base64 or raw text).
    Works with Claude, UIs, web apps, or any frontend uploading files.
    """
    logging.info(f"Processing uploaded file: {filename}")
    ext = os.path.splitext(filename)[1].lower()
 
    # Try decoding base64 first. If it fails, treat as UTF-8 text.
    try:
        if isinstance(content, str) and not content.strip().startswith(('{', '[', '<!DOCTYPE')) and len(content) % 4 == 0:
            file_bytes = base64.b64decode(content, validate=True)
            logging.info("Base64 decode successful.")
        else:
            raise ValueError("Not base64 — fallback to text")
    except Exception as e:
        logging.warning(f"Base64 decode failed, treating content as UTF-8 text: {e}")
        file_bytes = content.encode("utf-8", errors="ignore")
 
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        logging.info(f"Temporary file written to: {tmp_path}")
        return await read_from_file(tmp_path)
    except Exception as e:
        logging.error(f"Failed to process uploaded file {filename}: {e}")
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
async def read_from_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" in content_type:
                html = await resp.text()
                return BeautifulSoup(html, "html.parser").get_text()
            data = await resp.read()
            suffix = mimetypes.guess_extension(content_type) or ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            return await read_from_file(tmp_path)
 
 
async def read_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_pdf(path)
    elif ext == ".docx":
        return "\n".join(p.text for p in Document(path).paragraphs)
    elif ext in [".md", ".markdown"]:
        with open(path, "r", encoding="utf-8") as f:
            return BeautifulSoup(markdown(f.read()), "html.parser").get_text()
    elif ext in [".txt", ".json", ".csv", ".py", ".html"]:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path, sheet_name=None)
        return "\n\n".join(
            [f"Sheet: {name}\n{sheet.to_string(index=False)}" for name, sheet in df.items()]
        )
    else:
        raise Exception(f"Unsupported file extension: {ext}")
def get_jira_client():
    """Initialize and return a JIRA client."""
    jira_url = os.getenv("JIRA_URL")
    jira_user = os.getenv("JIRA_USER")
    jira_token = os.getenv("JIRA_API_TOKEN")
    if not all([jira_url, jira_user, jira_token]):
        raise EnvironmentError("Missing one or more required JIRA environment variables.")
    try:
        return JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
    except JIRAError as e:
        raise ConnectionError(f"Failed to connect to JIRA: {e}")
 
@mcp.tool()
def fetch_sprint_issues(sprint_id):
    """Fetch all Story and Task issues for a given sprint ID."""
    client = get_jira_client()
    jql = f'"Sprint" = {sprint_id} AND type IN (Story, Task)'
    try:
        issues = client.search_issues(jql, maxResults=1000)
        return [
            {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": getattr(issue.fields.assignee, "displayName", None)
            }
            for issue in issues
        ]
    except JIRAError as e:
        return {"error": str(e)}
 
@mcp.tool()
def fetch_story(key):
    """Return a single Jira issue by key."""
    client = get_jira_client()
    try:
        issue = client.issue(key)
        return {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "assignee": getattr(issue.fields.assignee, "displayName", None)
        }
    except JIRAError as e:
        return {"error": str(e)}
 
if __name__ == "__main__":
    mcp.run()
 