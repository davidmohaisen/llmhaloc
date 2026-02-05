"""
Global time tracking utilities for LLM vulnerability function localization.

This module provides a class for tracking and estimating global processing times
across multiple models, continuously refining estimates as models are completed.

"""

import os
import json
import time
from datetime import datetime, timedelta
from statistics import mean, median, stdev
import math

class GlobalTimeTracker:
    """
    A class for tracking and estimating global processing times across multiple models.

    This class maintains a history of model processing times and continuously refines
    the global time estimate as more models are completed.
    """

    def __init__(self, models, log_dir):
        """
        Initialize the global time tracker.

        Args:
            models (dict): Dictionary of models to process
            log_dir (str): Directory for log files
        """
        self.models = models
        self.log_dir = log_dir
        self.start_time = time.time()

        # Track completed models and their processing times
        self.completed_models = {}
        self.model_estimates = {}

        # Track the order of models for better estimation
        self.model_order = list(models.keys())

        # Load previous processing times if available
        self.load_processing_times()

        # Check for already completed models and load their processing times
        self._load_completed_models_times()

    def load_processing_times(self):
        """
        Load global processing times from a previous run if available.
        """
        times_file = self._get_times_file_path()
        if os.path.exists(times_file) and os.path.getsize(times_file) > 0:
            try:
                with open(times_file, 'r') as file:
                    data = json.load(file)
                    self.completed_models = data.get('completed_models', {})
                    print(f"Loaded processing times for {len(self.completed_models)} previously completed models")
            except Exception as e:
                print(f"Error loading global processing times: {e}")

    def _get_times_file_path(self):
        """
        Get the path to the global processing times file.

        Returns:
            str: Path to the global processing times file
        """
        times_dir = os.path.join(self.log_dir, "processing_times")
        if not os.path.exists(times_dir):
            os.makedirs(times_dir)

        return os.path.join(times_dir, "global_processing_times.json")

    def record_model_completion(self, model_name, processing_time):
        """
        Record the completion of a model and its processing time.

        Args:
            model_name (str): Name of the completed model
            processing_time (float): Time taken to process the model in seconds

        Returns:
            dict: Updated time estimates
        """
        # Record the model completion
        self.completed_models[model_name] = {
            'processing_time': processing_time,
            'completed_at': datetime.now().isoformat(),
            'elapsed_since_start': time.time() - self.start_time
        }

        # Remove this model from estimates since it's now completed
        if model_name in self.model_estimates:
            del self.model_estimates[model_name]

        # Save the updated processing times
        self._save_processing_times()

        # Return updated time estimates
        return self.get_time_estimates()

    def _save_processing_times(self):
        """
        Save global processing times to a file.
        """
        times_file = self._get_times_file_path()
        try:
            data = {
                'completed_models': self.completed_models,
                'last_updated': datetime.now().isoformat()
            }
            with open(times_file, 'w') as file:
                json.dump(data, file, indent=2)
        except Exception as e:
            print(f"Error saving global processing times: {e}")

    def get_time_estimates(self):
        """
        Calculate time estimates for the entire process based on completed models.

        Returns:
            dict: Dictionary with time statistics and estimates
        """
        # Calculate elapsed time
        elapsed_time = time.time() - self.start_time

        # Get total number of models
        total_models = len(self.models)
        completed_count = len(self.completed_models)
        remaining_count = total_models - completed_count

        # Initialize estimates
        time_estimates = {
            'elapsed_time': elapsed_time,
            'estimated_remaining_time': 0,
            'estimated_total_time': 0,
            'estimated_completion_time': None,
            'completed_models_count': completed_count,
            'total_models': total_models,
            'remaining_models': remaining_count,
            'model_estimates': {}
        }

        # If no models completed yet, return initial estimates
        if completed_count == 0:
            return self._get_initial_estimates(time_estimates)

        # Calculate average time per model based on completed models
        completed_times = [data['processing_time'] for data in self.completed_models.values()]

        # Calculate total time spent on completed models
        total_completed_time = sum(completed_times)

        # Use weighted average giving more importance to recent completions
        if len(completed_times) > 1:
            avg_time = self._calculate_weighted_average(completed_times)
        else:
            avg_time = completed_times[0]

        # Get remaining models
        remaining_models = [m for m in self.model_order if m not in self.completed_models]

        # Estimate time for each remaining model
        model_estimates = {}
        total_remaining_time = 0

        for model_name in remaining_models:
            # If we have a specific estimate for this model, use it
            if model_name in self.model_estimates:
                model_time = self.model_estimates[model_name]
            else:
                # Otherwise use the average time
                model_time = avg_time

            model_estimates[model_name] = model_time
            total_remaining_time += model_time

        # Calculate estimated completion time
        completion_time = datetime.now() + timedelta(seconds=total_remaining_time)

        # Update time estimates
        time_estimates['estimated_remaining_time'] = total_remaining_time
        time_estimates['estimated_total_time'] = elapsed_time + total_remaining_time
        time_estimates['estimated_completion_time'] = completion_time.isoformat()
        time_estimates['model_estimates'] = model_estimates
        time_estimates['avg_model_time'] = avg_time
        time_estimates['total_completed_time'] = total_completed_time

        # Include completed models in the output (full details)
        time_estimates['completed_models'] = self.completed_models

        return time_estimates

    def _get_initial_estimates(self, time_estimates):
        """
        Get initial time estimates when no models have been completed yet.

        Args:
            time_estimates (dict): Base time estimates dictionary

        Returns:
            dict: Updated time estimates
        """
        # Use a conservative estimate of 1 hour per model if we have no data
        avg_time = 3600  # 1 hour in seconds
        total_models = len(self.models)

        # Estimate total time
        total_time = avg_time * total_models

        # Calculate estimated completion time
        completion_time = datetime.now() + timedelta(seconds=total_time)

        # Update time estimates
        time_estimates['estimated_remaining_time'] = total_time
        time_estimates['estimated_total_time'] = total_time
        time_estimates['estimated_completion_time'] = completion_time.isoformat()
        time_estimates['avg_model_time'] = avg_time
        time_estimates['total_completed_time'] = 0  # No completed models yet

        # Add model-specific estimates
        model_estimates = {model: avg_time for model in self.models}
        time_estimates['model_estimates'] = model_estimates

        # Include completed models in the output
        time_estimates['completed_models'] = self.completed_models

        return time_estimates

    def _calculate_weighted_average(self, times):
        """
        Calculate a weighted average of processing times, giving more weight to recent completions.

        Args:
            times (list): List of processing times

        Returns:
            float: Weighted average time
        """
        # Assign weights (more recent completions have higher weights)
        weights = [math.exp(i/2) for i in range(len(times))]
        total_weight = sum(weights)

        # Calculate weighted average
        weighted_sum = sum(t * w for t, w in zip(times, weights))
        return weighted_sum / total_weight if total_weight > 0 else 0

    def update_model_estimate(self, model_name, estimated_time):
        """
        Update the estimated processing time for a specific model.

        Args:
            model_name (str): Name of the model
            estimated_time (float): Estimated processing time in seconds
        """
        self.model_estimates[model_name] = estimated_time

    def _load_completed_models_times(self):
        """
        Check for already completed models and load their processing times.
        This ensures we have accurate time data for models that were already processed.
        """
        from utils.data_handler import is_model_completed
        from utils.llm_processor import sanitize_model_name

        # For each model, check if it's already completed
        for model_name in self.models.keys():
            completed, _ = is_model_completed(model_name, None, None, self.log_dir)

            if completed:
                self._load_completed_model_time(model_name, sanitize_model_name)

    def _load_completed_model_time(self, model_name, sanitize_model_name):
        """
        Load processing time for a completed model.

        Args:
            model_name (str): Name of the model
            sanitize_model_name (function): Function to sanitize model name for file paths
        """
        # Model is already completed, try to get its processing time
        times_dir = os.path.join(self.log_dir, "processing_times")
        if not os.path.exists(times_dir):
            return

        times_file = os.path.join(times_dir, f"{sanitize_model_name(model_name)}_times.json")
        if not os.path.exists(times_file) or os.path.getsize(times_file) == 0:
            return

        try:
            with open(times_file, 'r') as file:
                data = json.load(file)
                times = data.get('processing_times', [])

                if times:
                    # Calculate total processing time for this model
                    total_time = sum(times)

                    # Record this as a completed model
                    self.completed_models[model_name] = {
                        'processing_time': total_time,
                        'completed_at': data.get('last_updated', datetime.now().isoformat()),
                        'elapsed_since_start': 0,  # Already completed before this run
                        'entry_count': len(times)
                    }

                    # Remove this model from estimates since it's already completed
                    if model_name in self.model_estimates:
                        del self.model_estimates[model_name]

                    print(f"Loaded processing time for completed model {model_name}: {total_time:.2f}s for {len(times)} entries")
        except Exception as e:
            print(f"Error loading processing times for completed model {model_name}: {e}")
