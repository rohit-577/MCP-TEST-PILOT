from typing import Optional
from contextlib import AsyncExitStack
import traceback
# from utils.logger import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime
import json
import os
import uuid

from openai import OpenAI
# from anthropic.types import Message


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = OpenAI()
        self.tools = []
        self.messages = []
        # self.logger = logger

        self.conversation_id = str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a tool with the given name and arguments"""
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            return result
        except Exception as e:
            # self.logger.error(f"Failed to call tool: {str(e)}")
            raise Exception(f"Failed to call tool: {str(e)}")

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        try:
            is_python = server_script_path.endswith(".py")
            is_js = server_script_path.endswith(".js")
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")

            # self.logger.info(
            #     f"Attempting to connect to server using script: {server_script_path}"
            # )
            # command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command="uv", 
                args=[
                "--directory",
                "PATH\\jira-mcp",
                "run",
                "server.py"
                ],
                type="stdio",
                env=None
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()
            mcp_tools = await self.get_mcp_tools()
            
            # Fix: Format tools correctly for OpenAI API
            self.tools = [
                {
                    "type": "function", 
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                }
                for tool in mcp_tools
            ]
            
            # self.logger.info(
            #     f"Successfully connected to server. Available tools: {[tool['function']['name'] for tool in self.tools]}"
            # )
            return True
        except Exception as e:
            # self.logger.error(f"Failed to connect to server: {str(e)}")
            # self.logger.debug(f"Connection error details: {traceback.format_exc()}")
            raise Exception(f"Failed to connect to server: {str(e)}")

    async def get_mcp_tools(self):
        try:
            # self.logger.info("Requesting MCP tools from the server.")
            response = await self.session.list_tools()
            tools = response.tools
            return tools
        except Exception as e:
            # self.logger.error(f"Failed to get MCP tools: {str(e)}")
            # self.logger.debug(f"Error details: {traceback.format_exc()}")
            raise Exception(f"Failed to get tools: {str(e)}")

    async def call_llm(self):
        """Call the LLM with the given query"""
        try:
            return self.llm.chat.completions.create(
                model="gpt-4o",
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto"
            )
        except Exception as e:
            # self.logger.error(f"Failed to call LLM: {str(e)}")
            raise Exception(f"Failed to call LLM: {str(e)}")

    async def process_query(self, query: str):
        system_prompt = """Process a query using OpenAI and available tools, returning all messages at the end "
        You are an expert AI assistant and QA engineer. Your primary goal is to assist the user "
                "by answering questions, providing information, and generating detailed test cases when requested. "
                "You have access to various tools to gather information from uploaded files, Jira, and GitLab. "
                "When the user asks for information that can be retrieved by a tool, call the appropriate tool. "
                "If you need more information to call a tool (e.g., a sprint ID or issue key), ask the user for it. "
                "All the keywords you get from a file or a link etc , check for those keywords in all the jira stories without asking for sprintid or key , just go through everything and try to find something related ,and summarize your answers after getting information from it ,if there is nothing related then give your own answer"
                "After retrieving information using tools, synthesize it to provide comprehensive and human-readable answers, "
                "especially when generating test cases. Maintain context throughout the conversation. "
                "If the user says 'quit' or 'end conversation', acknowledge it and end the session. "
                "When generating test cases, ensure they are clean, structured, and easy to understand, even for non-technical users. "
                "Do not assume the user has technical context. Always strive to be helpful and conversational."""
        try:
            # self.logger.info(
            #     f"Processing new query: {query[:100]}..."
            # )  # Log first 100 chars of query

            # Add the initial user message
            user_message = {"role": "user", "content": query}
            system_message = {"role": "system", "content": system_prompt}
            self.messages.append(user_message)
            await self.log_conversation(self.messages)
            messages = [system_message, user_message]

            while True:
                # self.logger.debug("Calling OPENAI API")
                response = await self.call_llm()
                
                # Get the assistant's message from the response
                assistant_message = response.choices[0].message
                
                # Check if there are tool calls
                if assistant_message.tool_calls:
                    # Add the assistant message with tool calls
                    assistant_msg = {
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                            for tool_call in assistant_message.tool_calls
                        ]
                    }
                    self.messages.append(assistant_msg)
                    await self.log_conversation(self.messages)
                    messages.append(assistant_msg)
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            # Parse the arguments (they come as a JSON string)
                            import json
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # self.logger.info(
                        #     f"Executing tool: {tool_name} with args: {tool_args}"
                        # )
                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                            # self.logger.info(f"Tool result: {result}")
                            
                            # Add tool result message
                            tool_result_message = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(result.content) if hasattr(result, 'content') else str(result)
                            }
                            self.messages.append(tool_result_message)
                            await self.log_conversation(self.messages)
                            messages.append(tool_result_message)
                            
                        except Exception as e:
                            error_msg = f"Tool execution failed: {str(e)}"
                            # self.logger.error(error_msg)
                            
                            # Add error message as tool result
                            tool_error_message = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": error_msg
                            }
                            self.messages.append(tool_error_message)
                            await self.log_conversation(self.messages)
                            messages.append(tool_error_message)
                else:
                    # Simple text response without tool calls
                    assistant_msg = {
                        "role": "assistant",
                        "content": assistant_message.content or ""
                    }
                    self.messages.append(assistant_msg)
                    await self.log_conversation(self.messages)
                    messages.append(assistant_msg)
                    break

            return messages

        except Exception as e:
            # self.logger.error(f"Error processing query: {str(e)}")
            # self.logger.debug(
            #     f"Query processing error details: {traceback.format_exc()}"
            # )
            raise
    def get_conversation_path(self):
        os.makedirs("conversations", exist_ok=True)
        return os.path.join("conversations", f"{self.conversation_id}.json")

    async def load_conversation(self, conversation_id: str):
        """Load a saved conversation by ID."""
        self.conversation_id = conversation_id
        path = self.get_conversation_path()

        if not os.path.exists(path):
            raise FileNotFoundError(f"Conversation {conversation_id} not found.")

        with open(path, "r") as f:
            data = json.load(f)
            self.messages = data.get("messages", [])
            self.created_at = data.get("created_at", datetime.now().isoformat())

    async def log_conversation(self, conversation: list):
        """Save entire conversation to a consistent file."""
        path = self.get_conversation_path()
        serializable_conversation = []

        for message in conversation:
            try:
                serializable_message = {
                    "role": message["role"],
                    "content": []
                }

                if isinstance(message["content"], str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message["content"], list):
                    for content_item in message["content"]:
                        if hasattr(content_item, 'to_dict'):
                            serializable_message["content"].append(content_item.to_dict())
                        elif hasattr(content_item, 'dict'):
                            serializable_message["content"].append(content_item.dict())
                        elif hasattr(content_item, 'model_dump'):
                            serializable_message["content"].append(content_item.model_dump())
                        else:
                            serializable_message["content"].append(content_item)

                serializable_conversation.append(serializable_message)
            except Exception as e:
                raise

        data_to_save = {
            "id": self.conversation_id,
            "created_at": self.created_at,
            "messages": serializable_conversation
        }

        try:
            with open(path, "w") as f:
                json.dump(data_to_save, f, indent=2, default=str)
        except Exception as e:
            raise

    async def cleanup(self):
        """Clean up resources"""
        try:
            # self.logger.info("Cleaning up resources")
            await self.exit_stack.aclose()
        except Exception as e:
            # self.logger.error(f"Error during cleanup: {str(e)}")
            pass
