"""
Configuration Manager for the LLM Vulnerability Function Localization Web Processing System.

"""

import logging
import os
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    """
    Singleton class to manage configuration settings loaded from YAML files.
    """

    _instance = None
    _config = None
    _version = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """
        Load configuration from the YAML file.
        """
        config_path = os.path.join("config", "config.yaml")
        try:
            with open(config_path, "r") as file:
                self._config = yaml.safe_load(file)
            logging.info(f"Configuration loaded successfully from {config_path}")
        except Exception as e:
            logging.error(f"Error loading configuration from {config_path}: {str(e)}")
            # Set default configuration
            self._config = {
                "directories": {
                    "input": "../04_relevant_analysis_results",
                    "output": "../06_relevant_analysis_final_results",
                    "logs": "00_logs",
                    "templates": "templates",
                    "static": "static",
                },
                "server": {"host": "0.0.0.0", "port": 8080, "debug": False},
                "logging": {
                    "level": "DEBUG",
                    "format": "%(asctime)s - %(levelname)s - %(message)s",
                    "file_rotation": True,
                    "max_file_size_mb": 10,
                    "backup_count": 5,
                },
                "ui": {"refresh_interval_ms": 1000, "max_displayed_history": 10},
            }
            logging.warning("Using default configuration settings")

    def get(self, section: str, key: Optional[str] = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: The configuration section
            key: The specific key within the section (optional)

        Returns:
            The configuration value or None if not found
        """
        if section not in self._config:
            logging.warning(f"Configuration section '{section}' not found")
            return None

        if key is None:
            return self._config[section]

        if key not in self._config[section]:
            logging.warning(
                f"Configuration key '{key}' not found in section '{section}'"
            )
            return None

        return self._config[section][key]

    def get_input_dir(self) -> str:
        """Get the input directory path."""
        return self.get("directories", "input")

    def get_output_dir(self) -> str:
        """Get the output directory path."""
        return self.get("directories", "output")

    def get_logs_dir(self) -> str:
        """Get the logs directory path."""
        return self.get("directories", "logs")

    def get_templates_dir(self) -> str:
        """Get the templates directory path."""
        return self.get("directories", "templates")

    def get_static_dir(self) -> str:
        """Get the static files directory path."""
        return self.get("directories", "static")

    def get_server_host(self) -> str:
        """Get the server host."""
        return self.get("server", "host")

    def get_server_port(self) -> int:
        """Get the server port."""
        return self.get("server", "port")

    def get_logging_level(self) -> str:
        """Get the logging level."""
        return self.get("logging", "level")

    def get_logging_format(self) -> str:
        """Get the logging format."""
        return self.get("logging", "format")

    def get_ui_refresh_interval(self) -> int:
        """Get the UI refresh interval in milliseconds."""
        return self.get("ui", "refresh_interval_ms")

    def get_max_displayed_history(self) -> int:
        """Get the maximum number of processed items to display in history."""
        return self.get("ui", "max_displayed_history")

    def set_version(self, version: str) -> None:
        """
        Set the application version for cache busting.

        Args:
            version: The version string
        """
        self._version = version
        logging.info(f"Application version set to: {version}")

    def get_version(self) -> str:
        """
        Get the application version for cache busting.

        Returns:
            The version string or a default if not set
        """
        # Define the version file path as a constant
        VERSION_FILE = "version.txt"

        if self._version is None:
            # Try to read from version.txt file first
            try:
                if os.path.exists(VERSION_FILE):
                    with open(VERSION_FILE, "r") as f:
                        self._version = f.read().strip()
                    logging.info(f"Loaded version from file: {self._version}")
                else:
                    # Generate a default version based on timestamp if file doesn't exist
                    import random
                    import time

                    self._version = str(int(time.time())) + str(
                        random.randint(1000, 9999)
                    )
                    logging.warning(
                        f"Version file not found. Using auto-generated version: {self._version}"
                    )

                    # Write the version to file for consistency
                    try:
                        with open(VERSION_FILE, "w") as f:
                            f.write(self._version)
                        logging.info(
                            f"Created version file with version: {self._version}"
                        )
                    except Exception as e:
                        logging.warning(f"Could not write version to file: {str(e)}")
            except Exception as e:
                # Fallback to timestamp if any error occurs
                import random
                import time

                self._version = str(int(time.time())) + str(random.randint(1000, 9999))
                logging.warning(
                    f"Error reading version file: {str(e)}. Using auto-generated version: {self._version}"
                )

        return self._version


# Create a singleton instance
config = ConfigManager()
