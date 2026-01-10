"""Contribution rules and validation logic for Ateker Voices platform."""

import uuid
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from .models import Recording, RecordingSession, User
from . import db


# Configuration constants
MAX_RECORDINGS_PER_SENTENCE = 5  # Sentence saturation limit (changed from 20 to 5)
RECORDINGS_PER_SESSION = 5  # Target recordings per session
SESSION_TIMEOUT_MINUTES = 30  # Auto-end session after inactivity


class ContributionRules:
    """Handles contribution limits and validation rules."""
    
    @staticmethod
    def can_user_record_sentence(user_id: int, language: str, prompt_group: str, prompt_id: str) -> Tuple[bool, str]:
        """
        Check if user can record a specific sentence.
        
        Returns:
            Tuple of (can_record, reason_message)
        """
        # Rule 1: One recording per sentence per user
        existing_recording = Recording.query.filter_by(
            user_id=user_id,
            language=language,
            prompt_group=prompt_group,
            prompt_id=prompt_id
        ).first()
        
        if existing_recording:
            return False, "You have already recorded this sentence. Each sentence can only be recorded once per person."
        
        # Rule 2: Sentence saturation check (15-20 different people)
        total_recordings = Recording.query.filter_by(
            language=language,
            prompt_group=prompt_group,
            prompt_id=prompt_id
        ).count()
        
        if total_recordings >= MAX_RECORDINGS_PER_SENTENCE:
            return False, f"This sentence has reached its maximum recordings ({MAX_RECORDINGS_PER_SENTENCE}). Thank you for your contribution!"
        
        return True, "You can record this sentence."
    
    @staticmethod
    def get_or_create_session(user_id: int, language: str) -> RecordingSession:
        """
        Get active session or create a new one.
        """
        # Check for active session
        active_session = RecordingSession.query.filter_by(
            user_id=user_id,
            language=language,
            is_active=True
        ).first()
        
        if active_session:
            # Check if session has timed out
            timeout_threshold = datetime.utcnow() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            if active_session.started_at < timeout_threshold:
                # End the old session
                active_session.is_active = False
                active_session.ended_at = datetime.utcnow()
                db.session.commit()
            elif active_session.recordings_count >= RECORDINGS_PER_SESSION:
                # End completed session
                active_session.is_active = False
                active_session.ended_at = datetime.utcnow()
                db.session.commit()
            else:
                # Session is still valid
                return active_session
        
        # Create new session
        new_session = RecordingSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            language=language
        )
        db.session.add(new_session)
        db.session.commit()
        
        return new_session
    
    @staticmethod
    def update_session_progress(session_id: str) -> None:
        """
        Update session recording count and check if session should end.
        """
        session = RecordingSession.query.get(session_id)
        if not session:
            return
        
        # Count recordings in this session
        session.recordings_count = Recording.query.filter_by(
            session_id=session_id
        ).count()
        
        # End session if limit reached
        if session.recordings_count >= RECORDINGS_PER_SESSION:
            session.is_active = False
            session.ended_at = datetime.utcnow()
        
        db.session.commit()
    
    @staticmethod
    def get_available_prompts(user_id: int, language: str, all_prompts: List) -> List:
        """
        Filter prompts based on contribution rules.
        Optimized to reduce database queries.
        """
        # Get all user's existing recordings in one query
        user_recordings = db.session.query(
            Recording.language, Recording.prompt_group, Recording.prompt_id
        ).filter_by(user_id=user_id).all()
        user_recorded_set = {
            (rec.language, rec.prompt_group, rec.prompt_id) 
            for rec in user_recordings
        }
        
        # Get sentence counts in batch - use language parameter instead of prompt.language
        sentence_keys = [(language, prompt.group, prompt.id) for prompt in all_prompts]
        existing_recordings = db.session.query(
            Recording.language, Recording.prompt_group, Recording.prompt_id,
            db.func.count(Recording.id).label('count')
        ).filter(
            db.tuple_(Recording.language, Recording.prompt_group, Recording.prompt_id).in_(sentence_keys)
        ).group_by(
            Recording.language, Recording.prompt_group, Recording.prompt_id
        ).all()
        
        # Create lookup dictionary
        recording_counts = {
            (rec.language, rec.prompt_group, rec.prompt_id): rec.count
            for rec in existing_recordings
        }
        
        available_prompts = []
        
        for prompt in all_prompts:
            prompt_key = (language, prompt.group, prompt.id)
            
            # Skip if user already recorded this
            if prompt_key in user_recorded_set:
                continue
            
            # Get recording count for this sentence
            total_recordings = recording_counts.get(prompt_key, 0)
            
            # Check sentence saturation
            if total_recordings >= MAX_RECORDINGS_PER_SENTENCE:
                continue
            
            available_prompts.append({
                'prompt': prompt,
                'recordings_count': total_recordings,
                'saturation_percent': (total_recordings / MAX_RECORDINGS_PER_SENTENCE) * 100
            })
        
        # Sort by saturation (least saturated first)
        available_prompts.sort(key=lambda x: x['saturation_percent'])
        
        return available_prompts
    
    @staticmethod
    def get_user_progress(user_id: int, language: str) -> dict:
        """
        Get user's recording progress and session info.
        """
        # Total recordings by user in this language
        user_recordings = Recording.query.filter_by(
            user_id=user_id,
            language=language
        ).count()
        
        # Get active session
        active_session = RecordingSession.query.filter_by(
            user_id=user_id,
            language=language,
            is_active=True
        ).first()
        
        session_progress = None
        if active_session:
            session_progress = {
                'session_id': active_session.id,
                'recordings_in_session': active_session.recordings_count,
                'max_per_session': RECORDINGS_PER_SESSION,
                'session_percent': (active_session.recordings_count / RECORDINGS_PER_SESSION) * 100,
                'started_at': active_session.started_at.isoformat()
            }
        
        return {
            'total_recordings': user_recordings,
            'active_session': session_progress
        }
    
    @staticmethod
    def get_sentence_statistics(language: str, prompt_group: str, prompt_id: str) -> dict:
        """
        Get statistics for a specific sentence.
        """
        total_recordings = Recording.query.filter_by(
            language=language,
            prompt_group=prompt_group,
            prompt_id=prompt_id
        ).count()
        
        # Get unique users who recorded this
        unique_users = db.session.query(Recording.user_id).filter_by(
            language=language,
            prompt_group=prompt_group,
            prompt_id=prompt_id
        ).distinct().count()
        
        return {
            'total_recordings': total_recordings,
            'unique_contributors': unique_users,
            'saturation_percent': (total_recordings / MAX_RECORDINGS_PER_SENTENCE) * 100,
            'is_saturated': total_recordings >= MAX_RECORDINGS_PER_SENTENCE,
            'remaining_slots': max(0, MAX_RECORDINGS_PER_SENTENCE - total_recordings)
        }
