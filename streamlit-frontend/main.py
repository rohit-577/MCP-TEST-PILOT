import asyncio
import streamlit as st
from chatbot import Chatbot


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
