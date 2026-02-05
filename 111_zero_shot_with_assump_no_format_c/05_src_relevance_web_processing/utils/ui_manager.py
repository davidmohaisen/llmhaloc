"""
UI Manager for the LLM Vulnerability Function Localization Web Processing System.

"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple


class ProgressTracker:
    """
    Class to track and report processing progress.
    """

    def __init__(self):
        self.file_progress = 0.0
        self.total_progress = 0.0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def update(self, file_progress: float, total_progress: float) -> None:
        """
        Update the progress values.

        Args:
            file_progress: Progress percentage for the current file (0-100)
            total_progress: Overall progress percentage (0-100)
        """
        with self.lock:
            self.file_progress = file_progress
            self.total_progress = total_progress
            self.logger.debug(
                f"Progress updated - File: {file_progress:.2f}%, Total: {total_progress:.2f}%"
            )

    def get(self) -> Tuple[float, float]:
        """
        Get the current progress values.

        Returns:
            Tuple of (file_progress, total_progress)
        """
        with self.lock:
            return self.file_progress, self.total_progress


class NotificationManager:
    """
    Class to manage UI notifications.
    """

    def __init__(self):
        self.notifications = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def add_notification(self, message: str, level: str = "info") -> None:
        """
        Add a new notification.

        Args:
            message: The notification message
            level: Notification level (info, warning, error)
        """
        with self.lock:
            self.notifications.append(
                {"message": message, "level": level, "read": False}
            )
            self.logger.debug(f"Added {level} notification: {message}")

    def get_unread_notifications(self) -> List[Dict[str, Any]]:
        """
        Get all unread notifications.

        Returns:
            List of unread notification objects
        """
        with self.lock:
            unread = [n for n in self.notifications if not n["read"]]
            for n in unread:
                n["read"] = True
            return unread


class UIManager:
    """
    Class to manage UI-related functionality.
    """

    def __init__(self):
        self.progress_tracker = ProgressTracker()
        self.notification_manager = NotificationManager()
        self.logger = logging.getLogger(__name__)

    def update_progress(
        self, file_index: int, total_files: int, obj_index: int, total_objects: int
    ) -> None:
        """
        Update progress based on current processing state.

        Args:
            file_index: Current file index
            total_files: Total number of files
            obj_index: Current object index
            total_objects: Total number of objects in the current file
        """
        file_progress = (obj_index / total_objects) * 100
        total_progress = (
            (file_index - 1 + (obj_index / total_objects)) / total_files
        ) * 100
        self.progress_tracker.update(file_progress, total_progress)

    def get_progress(self) -> Tuple[float, float]:
        """
        Get the current progress values.

        Returns:
            Tuple of (file_progress, total_progress)
        """
        return self.progress_tracker.get()

    def add_notification(self, message: str, level: str = "info") -> None:
        """
        Add a new notification.

        Args:
            message: The notification message
            level: Notification level (info, warning, error)
        """
        self.notification_manager.add_notification(message, level)

    def get_unread_notifications(self) -> List[Dict[str, Any]]:
        """
        Get all unread notifications.

        Returns:
            List of unread notification objects
        """
        return self.notification_manager.get_unread_notifications()


# Create a singleton instance
ui_manager = UIManager()
