import asyncio
import streamlit as st
import httpx
from typing import Dict, Any
import json
import base64
from datetime import datetime


class Chatbot:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.current_tool_call = {"name": None, "args": None}
        self.messages = st.session_state.get("messages", [])

    def display_message(self, message: Dict[str, Any]):
        timestamp = datetime.now().strftime("%H:%M:%S")

        if message["role"] == "user" and isinstance(message["content"], str):
            with st.chat_message("user"):
                st.markdown(message["content"])
                st.caption(f"🕒 {timestamp}")

        if message["role"] == "user" and isinstance(message["content"], list):
            for content in message["content"]:
                if content["type"] == "tool_result":
                    with st.chat_message("assistant"):
                        st.write(f"Called tool: {self.current_tool_call['name']}:")
                        st.json(
                            {
                                "name": self.current_tool_call["name"],
                                "args": self.current_tool_call["args"],
                                "content": json.loads(content["content"][0]["text"]),
                            },
                            expanded=False,
                        )
                        st.caption(f"🕒 {timestamp}")

        if message["role"] == "assistant" and isinstance(message["content"], str):
            with st.chat_message("assistant"):
                st.markdown(message["content"])
                st.caption(f"🕒 {timestamp}")

        if message["role"] == "assistant" and isinstance(message["content"], list):
            for content in message["content"]:
                if content["type"] == "tool_use":
                    self.current_tool_call = {
                        "name": content["name"],
                        "args": content["input"],
                    }

    async def get_tools(self):
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(f"{self.api_url}/tools")
            return response.json()

    async def list_conversations(self):
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(f"{self.api_url}/conversations")
            return response.json()

    async def load_conversation(self, convo_id):
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(f"{self.api_url}/conversations/{convo_id}")
            if response.status_code == 200:
                data = response.json()
                st.session_state["messages"] = data["messages"]
                st.session_state["conversation_id"] = data["id"]
                self.messages = data["messages"]

    async def delete_conversation(self, convo_id):
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.delete(f"{self.api_url}/conversations/{convo_id}")
            print(f"DELETE response: {response.status_code} | {response.text}")
            return response

    async def render(self):
        st.set_page_config(page_title="Tenjin Bot", page_icon=":shark:")
        st.title("Tenjin Bot")

        # --- Sidebar ---
        with st.sidebar:
            st.subheader("Settings")
            st.write("API URL: ", self.api_url)

            tools_result = await self.get_tools()
            st.subheader("Tools")
            st.write([tool["name"] for tool in tools_result["tools"]])

            st.subheader("Chats")
            conversations_data = await self.list_conversations()
            conversation_list = conversations_data.get("conversations", [])

            if "selected_convo" not in st.session_state:
                st.session_state.selected_convo = None

            selected_convo = st.selectbox(
                "Load Conversation",
                conversation_list,
                index=0 if conversation_list else -1,
                key="selected_convo"
            )

            col1, col2 = st.columns([3, 3])

            with col1:
                if st.button("Load Chat"):
                    if selected_convo:
                        await self.load_conversation(selected_convo)
                        st.rerun()

            with col2:
                if st.button("delete chat🗑️", help="Delete Chat"):
                    if selected_convo:
                        try:
                            convo_id = str(selected_convo)  # Make sure it's a string
                            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                                response = await client.post(
                                    f"{self.api_url}/conversations/delete",
                                    json={"conversation_id": convo_id}
                                )


                            if response.status_code == 200:
                                if st.session_state.get("conversation_id") == convo_id:
                                    st.session_state["messages"] = []
                                    st.session_state["conversation_id"] = ""
                                st.success(f"Deleted conversation: {convo_id}")
                                st.session_state.selected_convo = None
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Exception during delete: {str(e)}")


            if st.button("🆕 New Chat"):
                st.session_state["messages"] = []
                st.session_state["conversation_id"] = ""
                self.messages = []
                st.rerun()

        for message in self.messages:
            self.display_message(message)

        # --- Chat input and upload ---
        cols = st.columns([0.85, 0.15])
        with cols[0]:
            with st.form(key="chat_form", clear_on_submit=True):
                query = st.text_input("Enter your query here", key="text_query")
                submitted = st.form_submit_button("Send")

        with cols[1]:
            uploaded_file = st.file_uploader("📎", label_visibility="collapsed", key="upload")

        conversation_id = st.session_state.get("conversation_id", "")

        if uploaded_file:
            file_bytes = uploaded_file.read()
            file_content_base64 = base64.b64encode(file_bytes).decode("utf-8")
            file_info = {
                "filename": uploaded_file.name,
                "content": file_content_base64,
                "type": uploaded_file.type,
            }
            st.chat_message("user").markdown(f"📎 Uploaded file: `{uploaded_file.name}`")

            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                try:
                    response = await client.post(
                        f"{self.api_url}/file",
                        json={"file": file_info, "conversation_id": conversation_id},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state["messages"] = data["messages"]
                        st.session_state["conversation_id"] = data["conversation_id"]
                        self.messages = data["messages"]
                        for message in self.messages:
                            self.display_message(message)
                except Exception as e:
                    st.error(f"Frontend: Error uploading file: {str(e)}")

        if submitted and query:
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                try:
                    response = await client.post(
                        f"{self.api_url}/query",
                        json={"query": query, "conversation_id": conversation_id},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state["messages"] = data["messages"]
                        st.session_state["conversation_id"] = data["conversation_id"]
                        self.messages = data["messages"]
                        for message in self.messages:
                            self.display_message(message)
                except Exception as e:
                    st.error(f"Frontend: Error processing query: {str(e)}")


async def main():
    st.session_state.setdefault("server_connected", False)
    st.session_state.setdefault("tools", [])
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("conversation_id", "")

    API_URL = "http://localhost:8000"
    chatbot = Chatbot(API_URL)
    await chatbot.render()


if __name__ == "__main__":
    asyncio.run(main())
