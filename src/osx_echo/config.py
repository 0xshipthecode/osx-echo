"""
Configuration classes for osx_echo.
"""

import json
import os
class LanguageConfig:
    def __init__(self, language: str, language_name:str, whisper_model_path: str, trigger: dict):
        self.language = language
        self.language_name = language_name
        self.whisper_model_path = whisper_model_path
        self.trigger = trigger

    @staticmethod
    def from_config(config: dict) -> "LanguageConfig":
        return LanguageConfig(config["language"], config["language_name"], config["whisper_model_path"], config["trigger"])



class Config:
    """
    A configuration class for managing environment variables and settings.

    This class loads and stores various configuration parameters from environment
    variables, including paths for Whisper, listener configurations, and input
    device settings.
    """

    def __init__(self, whisper_main_path: str, language_support: list[LanguageConfig], input_device_name: str):
        """
        Initialize the Config object by loading values from environment variables.
        """
        self.whisper_main_path = whisper_main_path
        self.language_support = language_support
        self.input_device_name = input_device_name
    
    @staticmethod
    def from_config_file(path_to_config: str) -> "Config":
         with open(path_to_config, "r") as file:
            config = json.load(file)

            if not os.path.exists(config["whisper_main_path"]):
                raise FileNotFoundError(f"Whisper main path {config['whisper_main_path']} does not exist.")

            return Config(config["whisper_main_path"],
                         [LanguageConfig.from_config(lcfg) for lcfg in config["language_support"]],
                         config["input_device_name"])

    def get_language_support(self) -> list[LanguageConfig]:
        """
        Retrieve the listener configuration.

        Returns:
            dict: The listener configuration loaded from the environment.
        """
        return self.language_support

    def get_whisper_path(self):
        """
        Retrieve path to `main` executable from whisper.cpp.

        Returns:
            str: Path to `main` executable from whisper.cpp.
        """
        return self.whisper_main_path

    def get_input_device_name(self):
        """
        Retrieve the input device name.

        Returns:
            str: The input device name loaded from the environment.
        """
        return self.input_device_name
