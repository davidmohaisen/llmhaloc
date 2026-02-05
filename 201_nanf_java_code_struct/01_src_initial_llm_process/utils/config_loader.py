"""
Configuration loader for LLM vulnerability function localization.

This module handles loading and merging configuration from YAML files.

"""

import os
import socket
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


def detect_machine():
    """
    Detect which machine configuration to use based on hostname.

    Returns:
        str: Machine name ('mac', 'studio', etc.)
    """
    hostname = socket.gethostname().lower()

    if 'mac' in hostname:
        return 'mac'
    elif 'studio' in hostname:
        return 'studio'
    else:
        # Default to mac if can't determine
        logger.warning(f"Could not determine machine type from hostname '{hostname}', defaulting to 'mac'")
        return 'mac'


def load_config(machine_name=None):
    """
    Load and merge configuration files.

    Args:
        machine_name (str, optional): Name of the machine configuration to load.
                                     If None, tries to detect from hostname.

    Returns:
        dict: Merged configuration data
    """
    # If machine_name not provided, try to detect from hostname
    if machine_name is None:
        machine_name = detect_machine()

    project_root = get_project_root()
    config_dir = project_root / 'config'

    # Load common configuration
    common_config_path = os.path.join(config_dir, 'common.yaml')
    common_config = load_yaml_config(common_config_path)

    # Load machine-specific configuration
    machine_config_path = os.path.join(config_dir, f'{machine_name}.yaml')
    try:
        machine_config = load_yaml_config(machine_config_path)
    except FileNotFoundError:
        logger.error(f"Machine configuration file not found for '{machine_name}'")
        raise ValueError(f"Unknown machine configuration: {machine_name}")

    # Merge configurations (machine config takes precedence)
    config = {**common_config}

    # Add machine info
    config['machine'] = machine_config.get('machine', {})
    config['machine']['name'] = machine_name

    # Add models
    config['models'] = machine_config.get('models', {})

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
