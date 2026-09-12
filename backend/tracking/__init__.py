"""
AI Border Sentinel - Step 3: Multi-Object Tracking Module
Provides ByteTrack-based target tracking with persistent IDs and trajectory history.
"""

from tracking.tracker import ByteTracker, STrack

__all__ = ["ByteTracker", "STrack"]
