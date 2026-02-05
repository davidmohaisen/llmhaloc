"""
Configuration loader for LLM vulnerability function localization.

This module handles loading configuration from YAML files.

"""

import os
import yaml
from pathlib import Path

from .logger import Logger

# Initialize logger
logger = Logger()


def get_project_root():
    """
    Get the project root directory.

    Returns:
        Path: Path object pointing to the project root
    """
    # The config_loader.py file is in utils/ which is in the project directory
    return Path(__file__).parent.parent


def load_yaml_config(file_path):
    """
    Load a YAML configuration file.

    Args:
        file_path (str): Path to the YAML file

    Returns:
        dict: Configuration data from the YAML file

    Raises:
        FileNotFoundError: If the YAML file does not exist
        yaml.YAMLError: If the YAML file is invalid
    """
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        raise


def load_config():
    """
    Load configuration from the common.yaml file.

    Returns:
        dict: Configuration data
    """
    project_root = get_project_root()
    config_dir = project_root / 'config'

    # Load common configuration
    common_config_path = os.path.join(config_dir, 'common.yaml')
    config = load_yaml_config(common_config_path)

    # Resolve paths relative to project root
    if 'data' in config and 'base_dir' in config['data']:
        base_dir = config['data']['base_dir']
        if not os.path.isabs(base_dir):
            config['data']['base_dir'] = os.path.normpath(os.path.join(project_root, base_dir))

    if 'output' in config:
        for key in ['result_dir', 'log_dir']:
            if key in config['output'] and not os.path.isabs(config['output'][key]):
                config['output'][key] = os.path.normpath(os.path.join(project_root, config['output'][key]))

    return config
