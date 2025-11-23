import streamlit as st
from google import genai
from google.genai import types
import requests
import logging

# --- Defining variables and parameters  ---
REGION = "global"
PROJECT_ID = "dynamic-pivot-475316-n1" # TO DO: Insert Project ID
GEMINI_MODEL_NAME = "gemini-2.5-flash"

temperature = .2
top_p = 0.95

system_instructions = """
You are Agricare Assistant, an expert AI chatbot from Agricare. Your purpose is to help farmers and agricultural professionals with their questions about crop health and productivity.

Your Persona:
- You are knowledgeable, professional, and supportive.
- Your tone should be clear, encouraging, and easy to understand. Avoid overly technical jargon. If you must use a technical term, explain it simply.
- You are an assistant from Agricare, a trusted agrovet company.

Your Primary Functions:
1.  **Pest and Disease Management**: Help users identify, prevent, and manage common crop pests and diseases. Provide information on symptoms, causes, and control methods (including cultural, biological, and chemical options).
2.  **Crop Yield Improvement**: Provide advice and best practices for increasing crop yields. This includes topics like soil health, proper fertilization, irrigation techniques, crop rotation, and selecting appropriate seed varieties.

Guidelines for Your Responses:
- **Be Specific and Actionable**: When possible, provide clear, step-by-step guidance. If a user's question is vague, ask clarifying questions to better understand their situation (e.g., "To help you better, could you tell me which crop you're growing and what the weather has been like?").
- **Promote Agricare Solutions**: Where relevant and genuinely helpful, you can recommend Agricare products or services. Frame these as helpful suggestions, not aggressive sales pitches. For example, "For treating fungal infections like powdery mildew, a fungicide is often needed. Agricare offers a suitable product called 'AgriFungicide X' that could help."
- **Safety First**: Always include a disclaimer to read and follow the manufacturer's label instructions when recommending chemical treatments like pesticides or herbicides. Emphasize user and environmental safety.

Important Boundaries:
- **No Definitive Diagnoses**: You cannot see the crop, so you cannot make a definitive diagnosis. Use phrases like "It sounds like it could be..." or "Common causes for these symptoms include...".
- **Refer to Human Experts**: For complex or critical issues, or when in doubt, advise the user to consult a local agronomist or an Agricare field representative.
- **Stay On-Topic**: If the user asks questions outside the scope of agriculture, crop management, pests, and diseases, politely decline to answer and steer the conversation back to your purpose. Do not answer questions about unrelated topics.
"""


# --- Tooling ---
# TODO: Define the weather tool function declaration
weather_function = {
    "name": "get_current_temperature",
    "description": "Gets the current temperature for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g. San Francisco",
            },
        },
        "required": ["location"],
    },
}

# TODO: Define the get_current_temperature function
def get_current_temperature(location: str) -> str:
    """Gets the current temperature for a given location."""

    try:
        # --- Get Latitude and Longitude for the location ---
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geocode_response = requests.get(geocode_url)
        geocode_data = geocode_response.json()

        if not geocode_data.get("results"):
            return f"Could not find coordinates for {location}."

        lat = geocode_data["results"][0]["latitude"]
        lon = geocode_data["results"][0]["longitude"]

        # --- Get Weather for the coordinates ---
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        temperature = weather_data["current_weather"]["temperature"]
        unit = "°C"

        return f"{temperature}{unit}"

    except Exception as e:
        return f"Error fetching weather: {e}"


# --- Initialize the Vertex AI Client ---
if "client" not in st.session_state:
    try:
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=REGION,
        )
        st.session_state["client"] = client
        print(f"VertexAI Client initialized successfully with model {GEMINI_MODEL_NAME}")
    except Exception as e:
        st.error(f"Error initializing VertexAI client: {e}")
        st.stop()

# TODO: Add the get_chat function here in Task 15.
def get_chat(model_name: str):
    if f"chat-{model_name}" not in st.session_state:

        # TODO: Define the tools configuration for the model
        tools = types.Tool(function_declarations=[weather_function])

        # TODO: Define the generate_content configuration, including tools
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            system_instruction=[types.Part.from_text(text=system_instructions)],
            tools=[tools] # Pass the tool definition here
        )

        # TODO: Create a new chat session
        chat = st.session_state.client.chats.create(
            model=model_name,
            config=generate_content_config,
        )

        st.session_state[f"chat-{model_name}"] = chat
    return st.session_state[f"chat-{model_name}"]

# --- Call the Model ---
def call_model(prompt: str, model_name: str) -> str:
    """
    This function interacts with a large language model (LLM) to generate text based on a given prompt.
    It maintains a chat session and handles function calls from the model to external tools.
    """
    try:
        # TODO: Get the existing chat session or create a new one.
        chat = get_chat(model_name)

        message_content = prompt

        # Start the tool-calling loop
        while True:
            # TODO: Send the message to the model.
            response = chat.send_message(message_content)
            
            # Check if the model wants to call a tool
            has_tool_calls = False
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_tool_calls = True
                    function_call = part.function_call
                    logging.info(f"Function to call: {function_call.name}")
                    logging.info(f"Arguments: {function_call.args}")

                    # TODO: Call the appropriate function if the model requests it.
                    if function_call.name == "get_current_temperature":
                      result = get_current_temperature(**function_call.args)
                    function_response_part = types.Part.from_function_response(
                        name=function_call.name,
                        response={"result": result},
                    )
                    message_content = [function_response_part]

            # If no tool call was made, break the loop
            if not has_tool_calls:
                break

        # TODO: Return the model's final text response.
        return response.text

    except Exception as e:
        return f"Error: {e}"


# --- Presentation Tier (Streamlit) ---
# Set the title of the Streamlit application
st.title("Agricare Chat Bot")

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