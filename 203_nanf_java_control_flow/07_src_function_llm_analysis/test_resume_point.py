#!/usr/bin/env python3
"""
Test script for the resume point mechanism.

This script tests the resume point mechanism by creating a sample resume point,
loading it, and verifying that it works correctly.

"""

import os
import json
from datetime import datetime

from utils.resume_manager import ResumeState
from utils.data_handler import is_fully_processed
from utils.logger import Logger

# Initialize logger
logger = Logger()

# Test data
TEST_FILE_NAME = "test_file.json"
TEST_LOG_DIR = "./00_logs"
TEST_ENTRY = {
    "id": 42,
    "sub_id": 1,
    "code_id": 2,
    "function_id": 3
}
TEST_GROUND_TRUTH = [
    {"id": 40, "sub_id": 1, "code_id": 2, "function_id": 1},
    {"id": 41, "sub_id": 1, "code_id": 2, "function_id": 2},
    {"id": 42, "sub_id": 1, "code_id": 2, "function_id": 3},  # This matches TEST_ENTRY
    {"id": 43, "sub_id": 1, "code_id": 2, "function_id": 4},
    {"id": 44, "sub_id": 1, "code_id": 2, "function_id": 5}
]
TEST_TIME_ESTIMATES = {
    "avg_time_per_entry": 10.5,
    "median_time_per_entry": 9.8,
    "weighted_avg_time": 11.2,
    "std_dev": 2.3,
    "elapsed_time": 100.0,
    "estimated_remaining_time": 200.0,
    "estimated_total_time": 300.0,
    "estimated_completion_time": datetime.now().isoformat(),
    "progress_percentage": 33.3,
    "entries_completed": 10,
    "entries_total": 30,
    "entries_remaining": 20,
    "entries_per_minute": 6.0
}


def test_save_resume_state():
    """Test saving a resume state."""
    logger.section("Testing save_resume_state")

    # Create a resume state
    resume_state = ResumeState(TEST_LOG_DIR)

    # Save the state
    result = resume_state.save_state(
        TEST_FILE_NAME,
        TEST_ENTRY,
        10,
        30,
        TEST_TIME_ESTIMATES,
        False
    )

    if result:
        logger.success("Successfully saved resume state")
    else:
        logger.error("Failed to save resume state")

    return result


def test_load_resume_state():
    """Test loading a resume state."""
    logger.section("Testing load_resume_state")

    # Create a resume state
    resume_state = ResumeState(TEST_LOG_DIR)

    # Load the state
    result = resume_state.load_state(TEST_FILE_NAME)

    if result:
        logger.success("Successfully loaded resume state")

        # Convert to dict for logging
        state_dict = {
            'last_processed': resume_state.last_processed,
            'index': resume_state.index,
            'total': resume_state.total,
            'progress_percentage': resume_state.progress_percentage,
            'completed': resume_state.completed,
            'time_estimates': resume_state.time_estimates
        }
        logger.info(f"Resume state: {json.dumps(state_dict, indent=2)}")

        # Verify the data
        if (resume_state.last_processed.get('id') == TEST_ENTRY['id'] and
            resume_state.last_processed.get('sub_id') == TEST_ENTRY['sub_id'] and
            resume_state.last_processed.get('code_id') == TEST_ENTRY['code_id'] and
            resume_state.last_processed.get('function_id') == TEST_ENTRY['function_id']):
            logger.success("Resume state contains correct entry data")
        else:
            logger.error("Resume state contains incorrect entry data")
            return False

        # Verify time estimates
        if resume_state.time_estimates.get('avg_time_per_entry') == TEST_TIME_ESTIMATES['avg_time_per_entry']:
            logger.success("Resume state contains correct time estimates")
        else:
            logger.error("Resume state contains incorrect time estimates")
            return False

        return True
    else:
        logger.error("Failed to load resume state")
        return False


def test_find_resume_index():
    """Test finding the resume index in ground truth data."""
    logger.section("Testing find_resume_index")

    # Create a resume state
    resume_state = ResumeState(TEST_LOG_DIR)

    # Load the state
    result = resume_state.load_state(TEST_FILE_NAME)

    if not result:
        logger.error("Failed to load resume state for testing find_resume_index")
        return False

    # Find the resume index
    resume_idx = resume_state.find_resume_index(TEST_GROUND_TRUTH)

    # The index should be 3 (0-based index of the entry after TEST_ENTRY)
    if resume_idx == 3:
        logger.success(f"Correctly found resume index: {resume_idx}")
        return True
    else:
        logger.error(f"Incorrect resume index: {resume_idx}, expected 3")
        return False


def test_is_fully_processed():
    """Test the is_fully_processed function with resume states."""
    logger.section("Testing is_fully_processed")

    # First, create a resume state that is not marked as completed
    resume_state = ResumeState(TEST_LOG_DIR)
    resume_state.save_state(
        TEST_FILE_NAME,
        TEST_ENTRY,
        10,
        30,
        TEST_TIME_ESTIMATES,
        False  # not completed
    )

    # Test with incomplete resume state
    result = is_fully_processed("nonexistent_file.json", TEST_GROUND_TRUTH, TEST_LOG_DIR, TEST_FILE_NAME)
    if not result:
        logger.success("Correctly identified as not fully processed with incomplete resume state")
    else:
        logger.error("Incorrectly identified as fully processed with incomplete resume state")
        return False

    # Now create a resume state that is marked as completed
    resume_state = ResumeState(TEST_LOG_DIR)
    resume_state.save_state(
        TEST_FILE_NAME,
        TEST_ENTRY,
        30,  # all entries processed
        30,
        TEST_TIME_ESTIMATES,
        True  # completed
    )

    # Test with completed resume state
    result = is_fully_processed("nonexistent_file.json", TEST_GROUND_TRUTH, TEST_LOG_DIR, TEST_FILE_NAME)
    if result:
        logger.success("Correctly identified as fully processed with completed resume state")
    else:
        logger.error("Incorrectly identified as not fully processed with completed resume state")
        return False

    return True


def test_clear_resume_state():
    """Test clearing a resume state."""
    logger.section("Testing clear_resume_state")

    # Create a resume state
    resume_state = ResumeState(TEST_LOG_DIR)

    # Clear the state
    result = resume_state.clear_state(TEST_FILE_NAME)

    if result:
        logger.success("Successfully cleared resume state")

        # Verify it's gone
        new_resume_state = ResumeState(TEST_LOG_DIR)
        if not new_resume_state.load_state(TEST_FILE_NAME):
            logger.success("Resume state was properly cleared")
            return True
        else:
            logger.error("Resume state still exists after clearing")
            return False
    else:
        logger.error("Failed to clear resume state")
        return False


def run_tests():
    """Run all tests."""
    logger.section("RESUME POINT MECHANISM TESTS")

    # Run tests in sequence
    tests = [
        ("Save Resume State", test_save_resume_state),
        ("Load Resume State", test_load_resume_state),
        ("Find Resume Index", test_find_resume_index),
        ("Is Fully Processed", test_is_fully_processed),
        ("Clear Resume State", test_clear_resume_state)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        logger.separator("-", 60)
        logger.info(f"Running test: {name}")

        try:
            result = test_func()
            if result:
                logger.success(f"Test '{name}' PASSED")
                passed += 1
            else:
                logger.error(f"Test '{name}' FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"Test '{name}' FAILED with exception: {e}")
            failed += 1

    # Print summary
    logger.separator("=", 60)
    logger.info(f"Test Summary: {passed} passed, {failed} failed")

    if failed == 0:
        logger.success("All tests PASSED!")
        return True
    else:
        logger.error(f"{failed} tests FAILED!")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
