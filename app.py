import os
import streamlit as st
from google import genai
from google.genai import types
import requests
import logging

# --- Configuration ---
# It's recommended to set your PROJECT_ID as an environment variable
# for security and flexibility.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = "global"
GEMINI_MODEL_NAME = "gemini-2.5-flash"

temperature = .2
top_p = 0.95

system_instructions = None

# --- Tooling ---
# TODO: Define the weather tool function declaration

# TODO: Define the get_current_temperature function


# --- Initialize the Vertex AI Client ---
if not PROJECT_ID:
    st.error(
        "GOOGLE_CLOUD_PROJECT environment variable not set. "
        "Please set it to your Google Cloud Project ID."
    )
    st.stop()

try:
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=REGION,
    )
    print(f"VertexAI Client initialized successfully with model {GEMINI_MODEL_NAME}")
except Exception as e:
    st.error(f"Error initializing VertexAI client: {e}")
    st.stop()

# TODO: Add the get_chat function here in Task 15.


# --- Call the Model ---
def call_model(prompt: str, model_name: str) -> str:
    """
    This function interacts with a large language model (LLM) to generate text based on a given prompt and system instructions. 
    It will be replaced in a later step with a more advanced version that handles tooling.
    """
    try:

        # TODO: Prepare the content for the model
        contents = [prompt]

        # TODO: Define generate_content configuration (needed for system instructions and parameters)

        # TODO: Define response
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
        )

        logging.info(f"[call_model_response] LLM Response: \"{response.text}\"")
        # TODO: Uncomment the below "return response.text" line
        return response.text

    except Exception as e:
        return f"Error: {e}"


# --- Presentation Tier (Streamlit) ---
# Set the title of the Streamlit application
st.title("Travel Chat Bot")

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    # Initialize the chat history with a welcome message
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you today?"}
    ]

# Display the chat history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Get user input
if prompt := st.chat_input():
    # Add the user's message to the chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display the user's message
    st.chat_message("user").write(prompt)

    # Show a spinner while waiting for the model's response
    with st.spinner("Thinking..."):
        # Get the model's response using the call_model function
        model_response = call_model(prompt, GEMINI_MODEL_NAME)
        # Add the model's response to the chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": model_response}
        )
        # Display the model's response
        st.chat_message("assistant").write(model_response)