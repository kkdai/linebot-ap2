"""Session management for LINE Bot AP2."""

import asyncio
from typing import Dict, Optional
from google.adk.sessions import InMemorySessionService, Session


class SessionManager:
    """Enhanced session manager with better error handling and cleanup."""
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self.active_sessions: Dict[str, str] = {}
    
    async def get_or_create_session(self, user_id: str) -> str:
        """Get existing session or create new one for user."""
        if user_id not in self.active_sessions:
            session_id = f"session_{user_id}"
            try:
                await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                self.active_sessions[user_id] = session_id
                print(f"✓ New session created: {session_id} for user: {user_id}")
            except Exception as e:
                print(f"✗ Failed to create session for user {user_id}: {e}")
                raise
        else:
            session_id = self.active_sessions[user_id]
            print(f"✓ Using existing session: {session_id} for user: {user_id}")
        
        return session_id
    
    async def cleanup_session(self, user_id: str) -> bool:
        """Clean up session for user."""
        if user_id in self.active_sessions:
            session_id = self.active_sessions.pop(user_id)
            try:
                # Note: InMemorySessionService doesn't have explicit cleanup method
                # This is a placeholder for future implementation
                print(f"✓ Session cleaned up: {session_id} for user: {user_id}")
                return True
            except Exception as e:
                print(f"✗ Failed to cleanup session for user {user_id}: {e}")
                return False
        return False
    
    async def handle_session_error(self, user_id: str) -> str:
        """Handle session errors by recreating session."""
        print(f"⚠ Handling session error for user: {user_id}")
        
        # Remove invalid session
        self.active_sessions.pop(user_id, None)
        
        # Create new session
        return await self.get_or_create_session(user_id)
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)
    
    def list_active_users(self) -> list:
        """Get list of users with active sessions."""
        return list(self.active_sessions.keys())