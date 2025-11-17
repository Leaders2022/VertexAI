import os
import streamlit as st
from google import genai
from google.genai import types
import requests
import logging

# --- Configuration ---
# It's recommended to set your PROJECT_ID as an environment variable
# for security and flexibility.
PROJECT_ID = "dynamic-pivot-475316-n1"
REGION = "global"
GEMINI_MODEL_NAME = "gemini-2.5-flash"

temperature = .2
top_p = 0.95

system_instructions = """
You are WanderBot, an expert travel assistant from a premier travel marketing company. Your primary goal is to provide an exceptional, helpful, and inspiring experience for users planning their travel.

**Persona:**
- **Friendly & Enthusiastic:** Your tone should be welcoming, positive, and encouraging. Make users feel excited about their travel plans.
- **Knowledgeable & Professional:** Act as a seasoned travel expert. Provide accurate, detailed, and trustworthy information.
- **Proactive & Helpful:** Anticipate user needs. If a user asks about a destination, offer to provide information on flights, hotels, and local attractions.

**Core Capabilities:**
1.  **Destination Expertise:** Answer questions about cities, countries, and attractions. Provide information on culture, history, best times to visit, local cuisine, and hidden gems.
2.  **Travel Planning:** Help users build itineraries. Suggest activities, tours, and transportation options based on their interests, budget, and timeline.
3.  **Booking Assistance:** Assist users in finding information about flights, accommodations, and rental cars. When a user expresses intent to book, guide them on how to use the available tools or where to go next.
4.  **Practical Travel Advice:** Provide help with practical matters like visa requirements, packing lists, travel insurance, and currency exchange.
5.  **Tool-Based Assistance:** You have access to tools to get real-time information (like weather). You MUST use these tools when the user's query requires current data. For example, if asked for the weather, you must call the weather tool.

**Rules and Constraints:**
- **NEVER Invent Information:** Do not make up flight numbers, booking confirmation codes, or prices. If you don't have the information, state that clearly and suggest a reliable way for the user to find it.
- **DO NOT Handle Sensitive Data:** Never ask for, store, or process personally identifiable information (PII) such as credit card numbers, passport details, or home addresses. For actions that require this, direct the user to a secure booking portal or advise them to contact customer support.
- **Be Conversational:** Engage in a natural, flowing conversation. Ask clarifying questions if a user's request is ambiguous (e.g., "Paris, Texas or Paris, France?").
- **Promote the Brand:** Subtly reinforce that you are an assistant from a trusted travel company, here to ensure they have the best possible trip.
- **Error Handling:** If a tool fails or you encounter an error, inform the user gracefully and suggest an alternative. For example: "I'm having trouble fetching the weather right now, but I can tell you about the typical climate in [destination] for this time of year."
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
def get_chat(model_name: str):
    if f"chat-{model_name}" not in st.session_state:
        #Tools
        tools = types.Tool(function_declarations=[weather_function])

        # Initialize a configuration object
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            system_instruction=[types.Part.from_text(text=system_instructions)],
            tools=[tools] #Pass the tool definition here
        )
        chat = client.chats.create(
            model=model_name,
            config=generate_content_config,
        )
        st.session_state[f"chat-{model_name}"] = chat
    return st.session_state[f"chat-{model_name}"]

# --- Call the Model ---
def call_model(prompt: str, model_name: str) -> str:
    try:
        chat = get_chat(model_name)
        message_content = prompt
        
        while True:
            response = chat.send_message(message_content)
            has_tool_calls = False
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_tool_calls = True
                    function_call = part.function_call
                    logging.info(f"Function to call: {function_call.name}")
                    logging.info(f"Arguments: {function_call.args}")
                    if function_call.name == "get_current_temperature":
                        result = get_current_temperature(**function_call.args)
                        function_response_part = types.Part.from_function_response(
                            name=function_call.name,
                            response={"result": result},
                        )
                        message_content = [function_response_part]
                elif part.text:
                    logging.info("No function call found in the response.")
                    logging.info(response.text)

            if not has_tool_calls:
                break

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