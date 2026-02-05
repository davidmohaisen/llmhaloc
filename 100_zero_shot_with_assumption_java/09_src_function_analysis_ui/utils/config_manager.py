"""
Configuration manager for the LLM Vulnerability Function Localization Web Processing.
"""

import os
import yaml
from typing import Dict, Any, Optional


class ConfigManager:
    """
    Configuration manager for the application.
    Handles loading and accessing configuration values from YAML files.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file.
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the YAML file.

        Returns:
            Dict containing the configuration values.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Return default configuration
            return {
                'directories': {
                    'input': '../08_function_analysis_results',
                    'output': '../10_function_results',
                    'logs': '00_logs'
                },
                'server': {
                    'host': '0.0.0.0',
                    'port': 8080
                },
                'logging': {
                    'level': 'DEBUG',
                    'format': '%(asctime)s - %(levelname)s - %(message)s',
                    'file_rotation': True,
                    'max_bytes': 10485760,
                    'backup_count': 5
                },
                'ui': {
                    'title': 'Function Analysis Dashboard',
                    'refresh_interval': 1000,
                    'cache_busting': True
                }
            }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: The configuration key, can be nested using dot notation (e.g., 'server.port').
            default: Default value to return if the key is not found.

        Returns:
            The configuration value or the default value if not found.
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value

    def get_input_dir(self) -> str:
        """
        Get the input directory path.

        Returns:
            The input directory path.
        """
        return self.get('directories.input', '../08_function_analysis_results')

    def get_output_dir(self) -> str:
        """
        Get the output directory path.

        Returns:
            The output directory path.
        """
        return self.get('directories.output', '../10_function_results')

    def get_logs_dir(self) -> str:
        """
        Get the logs directory path.

        Returns:
            The logs directory path.
        """
        return self.get('directories.logs', '00_logs')

    def get_server_host(self) -> str:
        """
        Get the server host.

        Returns:
            The server host.
        """
        return self.get('server.host', '0.0.0.0')

    def get_server_port(self) -> int:
        """
        Get the server port.

        Returns:
            The server port.
        """
        return self.get('server.port', 8080)

    def get_logging_level(self) -> str:
        """
        Get the logging level.

        Returns:
            The logging level.
        """
        return self.get('logging.level', 'DEBUG')

    def get_logging_format(self) -> str:
        """
        Get the logging format.

        Returns:
            The logging format.
        """
        return self.get('logging.format', '%(asctime)s - %(levelname)s - %(message)s')

    def get_ui_title(self) -> str:
        """
        Get the UI title.

        Returns:
            The UI title.
        """
        return self.get('ui.title', 'Function Analysis Dashboard')

    def get_ui_refresh_interval(self) -> int:
        """
        Get the UI refresh interval.

        Returns:
            The UI refresh interval in milliseconds.
        """
        return self.get('ui.refresh_interval', 1000)


# Create a singleton instance
config = ConfigManager()
