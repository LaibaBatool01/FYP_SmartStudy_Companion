import streamlit as st
from chatbot_api import ask_chatbot

# Set page config
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
        border-radius: 10px;
        background-color: #f8f9fa;
    }
    .chat-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        border: 1px solid #ddd;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        margin: 10px 0;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        padding: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Main app
st.title("🤖 AI Chatbot")

# Initialize session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# User input
user_question = st.text_area("Ask a question:", height=100)

# Submit button
if st.button("Send", type="primary"):
    if user_question:
        with st.spinner("Getting response..."):
            # Add user question to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            
            # Get response from chatbot using the fixed URL in the API
            answer = ask_chatbot(user_question)
            
            # Add bot response to chat history
            st.session_state.chat_history.append({"role": "bot", "content": answer})

# Display chat history
if st.session_state.chat_history:
    st.markdown("### Conversation")
    
    with st.container():
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**Bot:** {message['content']}")
            st.markdown("---")

# Clear chat button
if st.session_state.chat_history and st.button("Clear Chat"):
    st.session_state.chat_history = []
    st.rerun()
