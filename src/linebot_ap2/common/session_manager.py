"""Enhanced session management for LINE Bot AP2."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

from google.adk.sessions import InMemorySessionService, Session
from .logger import setup_logger
from .retry_handler import RetryHandler, RetryableError
from ..models.agent import UserSession, AgentMetrics


@dataclass
class SessionStats:
    """Session statistics and health metrics."""
    total_sessions: int
    active_sessions: int
    expired_sessions: int
    average_session_duration: float
    last_cleanup: datetime


class EnhancedSessionManager:
    """Enhanced session manager with comprehensive monitoring and error handling."""
    
    def __init__(self, app_name: str, config: Dict[str, Any] = None):
        self.app_name = app_name
        self.config = config or {}
        
        # Configuration
        self.session_timeout_minutes = self.config.get("session_timeout_minutes", 30)
        self.cleanup_interval_seconds = self.config.get("cleanup_interval_seconds", 300)  # 5 minutes
        self.max_sessions_per_user = self.config.get("max_sessions_per_user", 3)
        
        # Core components
        self.session_service = InMemorySessionService()
        self.retry_handler = RetryHandler()
        self.logger = setup_logger("session_manager")
        
        # Session tracking
        self.active_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.user_sessions: Dict[str, UserSession] = {}  # user_id -> UserSession
        self.session_metadata: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata
        
        # Metrics
        self.total_sessions_created = 0
        self.total_sessions_cleaned = 0
        self.last_cleanup_time = datetime.now()
        
        # Start background cleanup task
        self._start_cleanup_task()
        
        self.logger.info(f"✓ Enhanced session manager initialized for app: {app_name}")


class SessionManager(EnhancedSessionManager):
    """Backward compatible session manager."""
    
    def __init__(self, app_name: str):
        super().__init__(app_name)
    
    async def get_or_create_session(self, user_id: str) -> str:
        """Get existing session or create new one with enhanced error handling."""
        
        try:
            # Check if user has existing session
            if user_id in self.active_sessions:
                session_id = self.active_sessions[user_id]
                
                # Verify session is still valid
                if await self._is_session_valid(session_id, user_id):
                    self._update_user_session(user_id, session_id)
                    self.logger.debug(f"Using existing session: {session_id} for user: {user_id}")
                    return session_id
                else:
                    # Clean up invalid session
                    await self._cleanup_invalid_session(user_id, session_id)
            
            # Create new session
            return await self._create_new_session(user_id)
            
        except Exception as e:
            self.logger.error(f"Session management error for user {user_id}: {str(e)}")
            raise RetryableError(f"Session creation failed: {str(e)}")
    
    async def _create_new_session(self, user_id: str) -> str:
        """Create a new session with comprehensive tracking."""
        
        # Check session limits
        if await self._check_session_limits(user_id):
            await self._cleanup_old_sessions(user_id)
        
        # Generate unique session ID
        timestamp = int(time.time())
        session_id = f"session_{user_id}_{timestamp}"
        
        try:
            # Create session in ADK
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )
            
            # Track session
            self.active_sessions[user_id] = session_id
            self._create_user_session(user_id, session_id)
            self._add_session_metadata(session_id, user_id)
            
            self.total_sessions_created += 1
            
            self.logger.info(f"✓ New session created: {session_id} for user: {user_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create session for user {user_id}: {str(e)}")
            raise
    
    async def _is_session_valid(self, session_id: str, user_id: str) -> bool:
        """Check if session is still valid."""
        
        # Check if user session exists and is active
        if user_id in self.user_sessions:
            user_session = self.user_sessions[user_id]
            if user_session.is_active:
                return True
        
        return False
    
    def _create_user_session(self, user_id: str, session_id: str):
        """Create user session tracking object."""
        
        user_session = UserSession(
            user_id=user_id,
            session_id=session_id,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.user_sessions[user_id] = user_session
    
    def _update_user_session(self, user_id: str, session_id: str):
        """Update user session activity."""
        
        if user_id in self.user_sessions:
            self.user_sessions[user_id].update_activity()
    
    def _add_session_metadata(self, session_id: str, user_id: str):
        """Add session metadata for tracking."""
        
        self.session_metadata[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
            "errors": 0
        }
    
    async def _check_session_limits(self, user_id: str) -> bool:
        """Check if user has too many sessions."""
        
        user_session_count = sum(
            1 for uid, session in self.user_sessions.items()
            if uid == user_id and session.is_active
        )
        
        return user_session_count >= self.max_sessions_per_user
    
    async def _cleanup_old_sessions(self, user_id: str):
        """Clean up oldest sessions for user."""
        
        user_sessions = [
            (uid, session) for uid, session in self.user_sessions.items()
            if uid == user_id and session.is_active
        ]
        
        # Sort by creation time and remove oldest
        user_sessions.sort(key=lambda x: x[1].created_at)
        
        for uid, session in user_sessions[:-self.max_sessions_per_user + 1]:
            await self.cleanup_session(uid)
    
    async def _cleanup_invalid_session(self, user_id: str, session_id: str):
        """Clean up invalid session."""
        
        self.active_sessions.pop(user_id, None)
        self.user_sessions.pop(user_id, None)
        self.session_metadata.pop(session_id, None)
        
        self.logger.warning(f"Cleaned up invalid session: {session_id} for user: {user_id}")
    
    async def cleanup_session(self, user_id: str) -> bool:
        """Clean up session for user with enhanced tracking."""
        
        if user_id not in self.active_sessions:
            return False
        
        session_id = self.active_sessions[user_id]
        
        try:
            # Clean up tracking data
            self.active_sessions.pop(user_id, None)
            self.user_sessions.pop(user_id, None)
            self.session_metadata.pop(session_id, None)
            
            self.total_sessions_cleaned += 1
            
            self.logger.info(f"✓ Session cleaned up: {session_id} for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup session for user {user_id}: {str(e)}")
            return False
    
    async def handle_session_error(self, user_id: str) -> str:
        """Handle session errors with enhanced recovery."""
        
        self.logger.warning(f"Handling session error for user: {user_id}")
        
        # Track error
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id].session_id
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["errors"] += 1
        
        # Clean up invalid session
        await self.cleanup_session(user_id)
        
        # Create new session
        return await self.get_or_create_session(user_id)
    
    def record_message(self, user_id: str):
        """Record message activity for user."""
        
        if user_id in self.user_sessions:
            self.user_sessions[user_id].update_activity()
            
            session_id = self.user_sessions[user_id].session_id
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["message_count"] += 1
                self.session_metadata[session_id]["last_activity"] = datetime.now()
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)
    
    def list_active_users(self) -> List[str]:
        """Get list of users with active sessions."""
        return list(self.active_sessions.keys())
    
    def get_session_stats(self) -> SessionStats:
        """Get comprehensive session statistics."""
        
        active_sessions = len(self.active_sessions)
        
        # Calculate average session duration
        total_duration = 0
        session_count = 0
        
        for user_session in self.user_sessions.values():
            if user_session.is_active:
                duration = (datetime.now() - user_session.created_at).total_seconds()
                total_duration += duration
                session_count += 1
        
        avg_duration = total_duration / session_count if session_count > 0 else 0
        
        return SessionStats(
            total_sessions=self.total_sessions_created,
            active_sessions=active_sessions,
            expired_sessions=self.total_sessions_cleaned,
            average_session_duration=avg_duration,
            last_cleanup=self.last_cleanup_time
        )
    
    def get_user_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session information for user."""
        
        if user_id not in self.user_sessions:
            return None
        
        user_session = self.user_sessions[user_id]
        session_id = user_session.session_id
        metadata = self.session_metadata.get(session_id, {})
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": user_session.created_at.isoformat(),
            "last_activity": user_session.last_activity.isoformat(),
            "message_count": user_session.message_count,
            "is_active": user_session.is_active,
            "session_metadata": metadata
        }
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        
        async def cleanup_expired_sessions():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval_seconds)
                    await self._cleanup_expired_sessions()
                except Exception as e:
                    self.logger.error(f"Background cleanup error: {str(e)}")
        
        # Start task in background (non-blocking)
        try:
            asyncio.create_task(cleanup_expired_sessions())
        except RuntimeError:
            # No event loop running, skip background task
            pass
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        
        cutoff_time = datetime.now() - timedelta(minutes=self.session_timeout_minutes)
        expired_users = []
        
        for user_id, user_session in self.user_sessions.items():
            if user_session.last_activity < cutoff_time:
                expired_users.append(user_id)
        
        # Clean up expired sessions
        for user_id in expired_users:
            await self.cleanup_session(user_id)
        
        if expired_users:
            self.logger.info(f"Cleaned up {len(expired_users)} expired sessions")
        
        self.last_cleanup_time = datetime.now()