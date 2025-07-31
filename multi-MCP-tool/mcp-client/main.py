

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager
from mcp_client import MCPClient
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import json
import base64
import uuid

load_dotenv()

# ------------------------
# Configuration
# ------------------------
class Settings(BaseSettings):
    server_script_path: str = "path\\jira-mcp\\server.py"

settings = Settings()

# ------------------------
# Lifespan (startup/shutdown)
# ------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MCPClient()
    try:
        connected = await client.connect_to_server(settings.server_script_path)
        if not connected:
            raise Exception("Failed to connect to server")
        app.state.client = client
        app.state.conversations = {}  # in-memory {conversation_id: messages}
        yield
    finally:
        await client.cleanup()

app = FastAPI(title="MCP Chatbot API", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Pydantic Models
# ------------------------
class QueryRequest(BaseModel):
    query: str
    conversation_id: str = ""

class FileUploadRequest(BaseModel):
    file: Dict[str, Any]
    conversation_id: str = ""

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]

# ------------------------
# Endpoints
# ------------------------

@app.get("/tools")
async def get_available_tools():
    try:
        tools = await app.state.client.get_mcp_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def process_query(request: QueryRequest):
    try:
        # Create or load conversation
        convo_id = request.conversation_id or str(uuid.uuid4())

        # Restore previous messages if available
        if convo_id in app.state.conversations:
            app.state.client.messages = app.state.conversations[convo_id]
        else:
            app.state.client.messages = []

        # Process query
        messages = await app.state.client.process_query(request.query)

        # Store updated messages
        app.state.conversations[convo_id] = app.state.client.messages

        return {
            "messages": messages,
            "conversation_id": convo_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/file")
async def handle_file_upload(payload: FileUploadRequest):
    try:
        file_data = payload.file
        convo_id = payload.conversation_id or str(uuid.uuid4())

        tool_name = "read_uploaded_file"
        args = {
            "filename": file_data["filename"],
            "content": file_data["content"],
            "type": file_data.get("type", "application/octet-stream")
        }

        result = await app.state.client.call_tool(tool_name, args)

        messages = [
            {"role": "user", "content": f"📎 Uploaded file: `{file_data['filename']}`"},
            {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "content": [{"text": json.dumps(result)}]
                }]
            }
        ]

        # Save to memory
        if convo_id not in app.state.conversations:
            app.state.conversations[convo_id] = []
        app.state.conversations[convo_id].extend(messages)

        return {
            "messages": app.state.conversations[convo_id],
            "conversation_id": convo_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations")
async def list_conversations():
    """Return a list of conversation IDs"""
    return {"conversations": list(app.state.conversations.keys())}

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Return messages for a specific conversation"""
    if conversation_id not in app.state.conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": conversation_id,
        "messages": app.state.conversations[conversation_id]
    }
class DeleteRequest(BaseModel):
    conversation_id: str

@app.post("/conversations/delete")
async def delete_conversation_post(request: DeleteRequest):
    convo_id = request.conversation_id
    if convo_id in app.state.conversations:
        del app.state.conversations[convo_id]
        return {"detail": f"Conversation {convo_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.post("/tool")
async def call_tool(tool_call: ToolCall):
    try:
        result = await app.state.client.call_tool(tool_call.name, tool_call.args)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------
# Uvicorn Run (CLI)
# ------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
