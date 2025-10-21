import os
import sys
import asyncio
from io import BytesIO

import aiohttp
from fastapi import Request, FastAPI, HTTPException
from zoneinfo import ZoneInfo

from linebot.models import MessageEvent, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import AsyncLineBotApi, WebhookParser
from multi_tool_agent.agent import (
    get_weather,
    get_current_time,
)
from ap2_agents.shopping_agent import shopping_agent
from ap2_agents.payment_processor import (
    get_user_payment_methods,
    initiate_payment,
    verify_otp,
    process_refund,
    get_transaction_status
)
from google.adk.agents import Agent
import re

# Import necessary session components
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner
from google.genai import types

# OpenAI Agent configuration
USE_VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or "FALSE"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or ""

# LINE Bot configuration
channel_secret = os.getenv("ChannelSecret", None)
channel_access_token = os.getenv("ChannelAccessToken", None)

# Validate environment variables
if channel_secret is None:
    print("Specify ChannelSecret as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify ChannelAccessToken as environment variable.")
    sys.exit(1)
if USE_VERTEX == "True":  # Check if USE_VERTEX is true as a string
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
    if not GOOGLE_CLOUD_PROJECT:
        raise ValueError(
            "Please set GOOGLE_CLOUD_PROJECT via env var or code when USE_VERTEX is true."
        )
    if not GOOGLE_CLOUD_LOCATION:
        raise ValueError(
            "Please set GOOGLE_CLOUD_LOCATION via env var or code when USE_VERTEX is true."
        )
elif not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY via env var or code.")

# Initialize the FastAPI app for LINEBot
app = FastAPI()
session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(channel_access_token, async_http_client)
parser = WebhookParser(channel_secret)

# Initialize ADK agents
weather_time_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description=("Agent to answer questions about the time and weather in a city."),
    instruction=("I can answer your questions about the time and weather in a city."),
    tools=[get_weather, get_current_time],
)

# Payment agent for AP2 functionality
payment_agent = Agent(
    name="ap2_payment_agent", 
    model="gemini-2.0-flash",
    description=("Agent to handle secure payment processing with OTP verification for AP2 protocol."),
    instruction=("""You handle secure payment processing for purchases. When users want to pay:
    1. Show available payment methods
    2. Initiate payment with OTP challenge
    3. Guide through OTP verification - IMPORTANT: When showing OTP info, always display the demo_hint or otp_code from the response so users can complete the demo
    4. Confirm successful transactions
    Always explain security features to build user confidence. For demo purposes, make sure to show the OTP code clearly when it's provided in the response."""),
    tools=[
        get_user_payment_methods,
        initiate_payment, 
        verify_otp,
        process_refund,
        get_transaction_status
    ]
)

print(f"Agents created: '{weather_time_agent.name}', '{shopping_agent.name}', '{payment_agent.name}'")

# --- Session Management ---
# Key Concept: SessionService stores conversation history & state.
# InMemorySessionService is simple, non-persistent storage for this tutorial.
session_service = InMemorySessionService()

# Define constants for identifying the interaction context
APP_NAME = "linebot_adk_app"
# Instead of fixed user_id and session_id, we'll now manage them dynamically

# Dictionary to track active sessions
active_sessions = {}

# Create a function to get or create a session for a user


async def get_or_create_session(user_id):  # Make function async
    if user_id not in active_sessions:
        # Create a new session for this user
        session_id = f"session_{user_id}"
        # Add await for the async session creation
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        active_sessions[user_id] = session_id
        print(
            f"New session created: App='{APP_NAME}', User='{user_id}', Session='{session_id}'"
        )
    else:
        # Use existing session
        session_id = active_sessions[user_id]
        print(
            f"Using existing session: App='{APP_NAME}', User='{user_id}', Session='{session_id}'"
        )

    return session_id


# Key Concept: Runners orchestrate the agent execution loops.
weather_runner = Runner(
    agent=weather_time_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

shopping_runner = Runner(
    agent=shopping_agent,
    app_name=APP_NAME, 
    session_service=session_service,
)

payment_runner = Runner(
    agent=payment_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

print(f"Runners created for all agents")


def determine_intent(message: str) -> str:
    """
    Determine user intent from message content
    
    Args:
        message: User's message text
        
    Returns:
        Intent type: 'shopping', 'payment', or 'weather_time'
    """
    message_lower = message.lower()
    
    # Shopping keywords
    shopping_keywords = [
        'buy', 'purchase', 'shop', 'product', 'item', 'store',
        '買', '購買', '商品', '產品', '店', '購物', '買東西',
        'iphone', 'macbook', 'airpods', 'apple watch', 'phone', 'laptop'
    ]
    
    # Payment keywords  
    payment_keywords = [
        'pay', 'payment', 'card', 'checkout', 'otp', 'verify',
        '付款', '支付', '付錢', '結帳', '驗證碼', '驗證',
        'confirm purchase', 'complete order'
    ]
    
    # Weather/time keywords
    weather_time_keywords = [
        'weather', 'time', 'temperature', 'forecast', 'rain', 'sunny',
        '天氣', '時間', '溫度', '預報', '下雨', '晴天', '現在幾點'
    ]
    
    # Check for payment intent first (highest priority for ongoing transactions)
    for keyword in payment_keywords:
        if keyword in message_lower:
            return 'payment'
    
    # Check for shopping intent
    for keyword in shopping_keywords:
        if keyword in message_lower:
            return 'shopping'
            
    # Check for weather/time intent
    for keyword in weather_time_keywords:
        if keyword in message_lower:
            return 'weather_time'
    
    # Default to shopping for unknown intents (since it's the main new feature)
    return 'shopping'


@app.post("/")
async def handle_callback(request: Request):
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue

        if event.message.type == "text":
            # Process text message
            msg = event.message.text
            user_id = event.source.user_id
            print(f"Received message: {msg} from user: {user_id}")

            # Determine user intent and route to appropriate agent
            intent = determine_intent(msg)
            response = await call_agent_async(msg, user_id, intent)
            reply_msg = TextSendMessage(text=response)
            await line_bot_api.reply_message(event.reply_token, reply_msg)
        elif event.message.type == "image":
            return "OK"
        else:
            continue

    return "OK"


async def call_agent_async(query: str, user_id: str, intent: str = 'shopping') -> str:
    """Sends a query to the appropriate agent based on intent and returns the final response."""
    print(f"\n>>> User Query: {query} (Intent: {intent})")

    # Get or create a session for this user
    session_id = await get_or_create_session(user_id)

    # Select appropriate runner based on intent
    if intent == 'weather_time':
        selected_runner = weather_runner
        print(f"Using weather/time agent")
    elif intent == 'payment':
        selected_runner = payment_runner
        print(f"Using payment agent")
    else:  # default to shopping
        selected_runner = shopping_runner
        print(f"Using shopping agent")

    # Prepare the user's message in ADK format
    content = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."  # Default

    try:
        # Key Concept: run_async executes the agent logic and yields Events.
        # We iterate through events to find the final answer.
        async for event in selected_runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # You can uncomment the line below to see *all* events during execution
            # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

            # Key Concept: is_final_response() marks the concluding message for the turn.
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Assuming text response in the first part
                    final_response_text = event.content.parts[0].text
                elif (
                    event.actions and event.actions.escalate
                ):  # Handle potential errors/escalations
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                # Add more checks here if needed (e.g., specific error codes)
                break  # Stop processing events once the final response is found
    except ValueError as e:
        # Handle errors, especially session not found
        print(f"Error processing request: {str(e)}")
        # Recreate session if it was lost
        if "Session not found" in str(e):
            active_sessions.pop(user_id, None)  # Remove the invalid session
            session_id = await get_or_create_session(
                user_id
            )  # Create a new one # Add await
            # Try again with the new session
            try:
                async for event in selected_runner.run_async(
                    user_id=user_id, session_id=session_id, new_message=content
                ):
                    # Same event handling code as above
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            final_response_text = event.content.parts[0].text
                        elif event.actions and event.actions.escalate:
                            final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                        break
            except Exception as e2:
                final_response_text = f"Sorry, I encountered an error: {str(e2)}"
        else:
            final_response_text = f"Sorry, I encountered an error: {str(e)}"

    print(f"<<< Agent Response: {final_response_text}")
    return final_response_text
