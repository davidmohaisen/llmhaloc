"""
UI manager for the LLM Vulnerability Function Localization Web Processing.
"""

import threading
import time
from typing import Dict, Any, List

from .logging_manager import logger


class Progress:
    """
    Class to track and manage progress information for the UI.
    """

    def __init__(self):
        """
        Initialize the progress tracker.
        """
        self.file_progress = 0
        self.total_progress = 0
        self.current_file_index = 0
        self.total_files = 0
        self.current_object_index = 0
        self.total_objects = 0
        self.total_objects_processed = 0
        self.total_objects_all_files = 0
        self.lock = threading.Lock()

    def update(self, file_progress: float, total_progress: float, 
               current_file_index: int, total_files: int,
               current_object_index: int, total_objects: int, 
               total_objects_processed: int = None,
               total_objects_all_files: int = None):
        """
        Update the progress information.

        Args:
            file_progress: Progress percentage for the current file.
            total_progress: Overall progress percentage.
            current_file_index: Index of the current file being processed.
            total_files: Total number of files to process.
            current_object_index: Index of the current object being processed.
            total_objects: Total number of objects in the current file.
            total_objects_processed: Total number of objects processed across all files.
            total_objects_all_files: Total number of objects across all files.
        """
        with self.lock:
            self.file_progress = file_progress
            self.total_progress = total_progress
            self.current_file_index = current_file_index
            self.total_files = total_files
            self.current_object_index = current_object_index
            self.total_objects = total_objects
            if total_objects_processed is not None:
                self.total_objects_processed = total_objects_processed
            if total_objects_all_files is not None:
                self.total_objects_all_files = total_objects_all_files
                
        # Log progress updates
        logger.debug(f"Progress updated: {self.get()}")

    def get(self) -> Dict[str, Any]:
        """
        Get the current progress information.

        Returns:
            Dictionary containing the progress information.
        """
        with self.lock:
            return {
                "file_progress": self.file_progress,
                "total_progress": self.total_progress,
                "current_file_index": self.current_file_index,
                "total_files": self.total_files,
                "current_object_index": self.current_object_index,
                "total_objects": self.total_objects,
                "total_objects_processed": self.total_objects_processed,
                "total_objects_all_files": self.total_objects_all_files
            }


class UIManager:
    """
    Manager for UI-related functionality.
    """

    def __init__(self):
        """
        Initialize the UI manager.
        """
        self.progress = Progress()
        self.cache_buster = str(int(time.time()))
        
    def reset_progress(self):
        """
        Reset all progress values to initial state.
        """
        self.progress.update(0, 0, 0, 0, 0, 0, 0, 0)
        logger.info("Progress reset")
        
    def update_progress(self, file_index: int, total_files: int, 
                        obj_index: int, total_objects: int,
                        total_objects_processed: int = None, 
                        total_objects_all_files: int = None):
        """
        Update the progress information.

        Args:
            file_index: Index of the current file being processed.
            total_files: Total number of files to process.
            obj_index: Index of the current object being processed.
            total_objects: Total number of objects in the current file.
            total_objects_processed: Total number of objects processed across all files.
            total_objects_all_files: Total number of objects across all files.
        """
        file_progress = (obj_index / total_objects) * 100 if total_objects > 0 else 0

        # Calculate total progress based on total objects processed if available
        if total_objects_processed is not None and total_objects_all_files is not None and total_objects_all_files > 0:
            total_progress = (total_objects_processed / total_objects_all_files) * 100
        else:
            # Fallback to old calculation method
            total_progress = ((file_index - 1 + (obj_index / total_objects)) / total_files) * 100 if total_files > 0 and total_objects > 0 else 0

        self.progress.update(
            file_progress,
            total_progress,
            file_index,
            total_files,
            obj_index,
            total_objects,
            total_objects_processed,
            total_objects_all_files
        )
        
    def update_cache_buster(self):
        """
        Update the cache buster timestamp.
        """
        self.cache_buster = str(int(time.time()))
        logger.debug(f"Cache buster updated: {self.cache_buster}")
        
    def get_cache_buster(self) -> str:
        """
        Get the current cache buster timestamp.

        Returns:
            The cache buster timestamp.
        """
        return self.cache_buster


# Create a singleton instance
ui_manager = UIManager()

# Create aliases for commonly used methods
progress = ui_manager.progress
reset_progress = ui_manager.reset_progress
update_progress = ui_manager.update_progress
