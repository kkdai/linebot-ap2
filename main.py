"""
Enhanced LINE Bot AP2 Application

Modern FastAPI application with improved architecture, error handling, 
and configuration management following AP2 best practices.
"""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

import aiohttp
from fastapi import FastAPI, Request, HTTPException
from linebot.models import MessageEvent, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import AsyncLineBotApi, WebhookParser

# Import new modularized components
from src.linebot_ap2.config import get_settings, validate_environment
from src.linebot_ap2.common import SessionManager, IntentDetector, setup_logger
from src.linebot_ap2.common.logger import log_agent_interaction, log_error_with_context
from src.linebot_ap2.agents import (
    create_enhanced_shopping_agent,
    create_enhanced_payment_agent
)

from google.adk.runners import Runner
from google.genai import types


class LineBot:
    """Enhanced LINE Bot with improved architecture."""
    
    def __init__(self):
        # Load and validate configuration
        self.settings = validate_environment()
        self.logger = setup_logger(level=self.settings.log_level)
        
        # Initialize components
        self.session_manager = SessionManager(self.settings.app_name)
        self.intent_detector = IntentDetector()
        
        # Initialize LINE Bot components
        self._init_line_bot()
        
        # Initialize agents
        self._init_agents()
        
        self.logger.info("✓ LINE Bot AP2 application initialized successfully")
    
    def _init_line_bot(self):
        """Initialize LINE Bot API components."""
        self.session = aiohttp.ClientSession()
        self.async_http_client = AiohttpAsyncHttpClient(self.session)
        self.line_bot_api = AsyncLineBotApi(
            self.settings.line_channel_access_token, 
            self.async_http_client
        )
        self.parser = WebhookParser(self.settings.line_channel_secret)
        
        self.logger.info("✓ LINE Bot API components initialized")
    
    def _init_agents(self):
        """Initialize ADK agents with enhanced configuration."""
        # Create enhanced agents using factory functions
        self.shopping_agent = create_enhanced_shopping_agent(
            model=self.settings.default_model
        )

        self.payment_agent = create_enhanced_payment_agent(
            model=self.settings.default_model,
            max_otp_attempts=self.settings.max_otp_attempts,
            otp_expiry_minutes=self.settings.otp_expiry_minutes
        )

        # Initialize runners with enhanced agents
        self.shopping_runner = Runner(
            agent=self.shopping_agent,
            app_name=self.settings.app_name,
            session_service=self.session_manager.session_service,
        )

        self.payment_runner = Runner(
            agent=self.payment_agent,
            app_name=self.settings.app_name,
            session_service=self.session_manager.session_service,
        )

        self.logger.info("✓ Enhanced agents and runners initialized successfully")
    
    async def process_message(self, event: MessageEvent) -> str:
        """Process incoming message with enhanced error handling."""
        start_time = time.time()
        user_id = event.source.user_id
        message = event.message.text
        
        try:
            # Detect intent with enhanced detection
            intent_result = self.intent_detector.detect_intent(message)
            intent = intent_result["intent"].value
            confidence = intent_result["confidence"]
            
            self.logger.info(
                f"Intent detected: {intent} (confidence: {confidence:.2f}) for user: {user_id}"
            )
            
            # Get or create session
            session_id = await self.session_manager.get_or_create_session(user_id)
            
            # Route to appropriate agent
            response = await self._call_agent(message, user_id, session_id, intent)
            
            # Log interaction
            processing_time = time.time() - start_time
            log_agent_interaction(
                self.logger, user_id, intent, message, response, processing_time
            )
            
            return response
            
        except Exception as e:
            log_error_with_context(
                self.logger, e, "message_processing", user_id
            )
            return "抱歉，處理您的訊息時發生錯誤。請稍後再試。"
    
    async def _call_agent(self, message: str, user_id: str, session_id: str, intent: str) -> str:
        """Call appropriate agent based on intent."""
        # Select runner based on intent
        if intent == 'payment':
            selected_runner = self.payment_runner
            agent_name = "Payment"
        else:  # default to shopping
            selected_runner = self.shopping_runner
            agent_name = "Shopping"
        
        self.logger.debug(f"Using {agent_name} agent for user {user_id}")
        
        # Prepare message
        content = types.Content(role="user", parts=[types.Part(text=message)])
        
        try:
            # Execute agent
            async for event in selected_runner.run_async(
                user_id=user_id, session_id=session_id, new_message=content
            ):
                # Log all events for debugging
                if hasattr(event, 'content') and event.content:
                    self.logger.debug(f"Agent event: final={event.is_final_response()}, parts={len(event.content.parts) if event.content.parts else 0}")

                # Only process final response
                if event.is_final_response():
                    if event.content and event.content.parts:
                        # Extract text from all text parts
                        text_parts = [
                            part.text for part in event.content.parts
                            if hasattr(part, 'text') and part.text
                        ]
                        if text_parts:
                            return "\n".join(text_parts)

                    if event.actions and event.actions.escalate:
                        return f"Agent escalated: {event.error_message or 'No specific message.'}"
                    
        except ValueError as e:
            if "Session not found" in str(e):
                # Handle session error by recreating
                self.logger.warning(f"Session error for user {user_id}, recreating...")
                session_id = await self.session_manager.handle_session_error(user_id)
                
                # Retry with new session
                async for event in selected_runner.run_async(
                    user_id=user_id, session_id=session_id, new_message=content
                ):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            # Extract text from all text parts
                            text_parts = [
                                part.text for part in event.content.parts
                                if hasattr(part, 'text') and part.text
                            ]
                            if text_parts:
                                return "\n".join(text_parts)

                        if event.actions and event.actions.escalate:
                            return f"Agent escalated: {event.error_message or 'No specific message.'}"
            else:
                raise
        
        return "抱歉，無法處理您的請求。"
    
    async def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'session'):
            await self.session.close()
        self.logger.info("✓ Application cleanup completed")


# Global app instance
bot_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global bot_instance
    
    # Startup
    bot_instance = LineBot()
    yield
    
    # Shutdown
    if bot_instance:
        await bot_instance.cleanup()


# Create FastAPI app with lifespan management
app = FastAPI(
    title="LINE Bot AP2",
    description="LINE Bot with Google AP2 integration",
    version="0.1.0",
    lifespan=lifespan
)


@app.post("/")
async def handle_callback(request: Request):
    """Handle LINE webhook callbacks."""
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Get request body
    body = await request.body()
    body_text = body.decode()
    
    try:
        events = bot_instance.parser.parse(body_text, signature)
    except InvalidSignatureError:
        bot_instance.logger.error("Invalid signature received")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Process events
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
            
        if event.message.type == "text":
            try:
                response = await bot_instance.process_message(event)
                reply_msg = TextSendMessage(text=response)
                await bot_instance.line_bot_api.reply_message(
                    event.reply_token, reply_msg
                )
            except Exception as e:
                bot_instance.logger.error(f"Error processing message: {e}")
                # Send error message to user
                error_msg = TextSendMessage(text="抱歉，處理您的訊息時發生錯誤。")
                await bot_instance.line_bot_api.reply_message(
                    event.reply_token, error_msg
                )
        elif event.message.type == "image":
            # Handle image messages (placeholder)
            continue
    
    return "OK"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": bot_instance.session_manager.get_active_session_count() if bot_instance else 0,
        "timestamp": time.time()
    }


@app.get("/metrics")
async def get_metrics():
    """Get application metrics."""
    if not bot_instance:
        return {"error": "Application not initialized"}
    
    return {
        "active_sessions": bot_instance.session_manager.get_active_session_count(),
        "active_users": bot_instance.session_manager.list_active_users(),
        "app_name": bot_instance.settings.app_name,
        "model": bot_instance.settings.default_model
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )