"""
Configuration classes for osx_echo.
"""

import json
import os
import logging
from typing import List
import pyaudio

logger = logging.getLogger("osx_echo.config")


# Valid language codes supported by whisper
VALID_LANGUAGE_CODES = {
    "en",
    "zh",
    "de",
    "es",
    "ru",
    "ko",
    "fr",
    "ja",
    "pt",
    "tr",
    "pl",
    "ca",
    "nl",
    "ar",
    "sv",
    "it",
    "id",
    "hi",
    "fi",
    "vi",
    "he",
    "uk",
    "el",
    "ms",
    "cs",
    "ro",
    "da",
    "hu",
    "ta",
    "no",
    "th",
    "ur",
    "hr",
    "bg",
    "lt",
    "la",
    "mi",
    "ml",
    "cy",
    "sk",
    "te",
    "fa",
    "lv",
    "bn",
    "sr",
    "az",
    "sl",
    "kn",
    "et",
    "mk",
    "br",
    "eu",
    "is",
    "hy",
    "ne",
    "mn",
    "bs",
    "kk",
    "sq",
    "sw",
    "gl",
    "mr",
    "pa",
    "si",
    "km",
    "sn",
    "yo",
    "so",
    "af",
    "oc",
    "ka",
    "be",
    "tg",
    "sd",
    "gu",
    "am",
    "yi",
    "lo",
    "uz",
    "fo",
    "ht",
    "ps",
    "tk",
    "nn",
    "mt",
    "sa",
    "lb",
    "my",
    "bo",
    "tl",
    "mg",
    "as",
    "tt",
    "haw",
    "ln",
    "ha",
    "ba",
    "jw",
    "su",
    "yue",  # Cantonese
}


class LanguageConfig:
    def __init__(
        self, language: str, language_name: str, whisper_model_path: str, trigger: dict
    ):
        self.language = language
        self.language_name = language_name
        self.whisper_model_path = whisper_model_path
        self.trigger = trigger

    @staticmethod
    def from_config(config: dict) -> "LanguageConfig":
        """Create LanguageConfig from dictionary with validation."""
        language = config.get("language")
        if not language:
            raise ValueError("Language code is required in language config")

        # Validate language code
        if language not in VALID_LANGUAGE_CODES:
            raise ValueError(
                f"Invalid language code '{language}'. "
                f"Must be one of: {', '.join(sorted(VALID_LANGUAGE_CODES))}"
            )

        language_name = config.get("language_name")
        if not language_name:
            raise ValueError(f"Language name is required for language '{language}'")

        whisper_model_path = config.get("whisper_model_path")
        if not whisper_model_path:
            raise ValueError(
                f"Whisper model path is required for language '{language}'"
            )

        # Validate model file exists
        if not os.path.exists(whisper_model_path):
            raise FileNotFoundError(
                f"Whisper model file not found for language '{language}': {whisper_model_path}"
            )

        trigger = config.get("trigger")
        if not trigger:
            raise ValueError(
                f"Trigger configuration is required for language '{language}'"
            )

        if "type" not in trigger:
            raise ValueError(f"Trigger type is required for language '{language}'")

        if "keys" not in trigger or not trigger["keys"]:
            raise ValueError(f"Trigger keys are required for language '{language}'")

        return LanguageConfig(
            language,
            language_name,
            whisper_model_path,
            trigger,
        )


class Config:
    """
    A configuration class for managing environment variables and settings.

    This class loads and stores various configuration parameters from environment
    variables, including paths for Whisper, listener configurations, and input
    device settings.
    """

    def __init__(
        self,
        whisper_main_path: str,
        language_support: list[LanguageConfig],
        input_device_name: str,
    ):
        """
        Initialize the Config object by loading values from environment variables.
        """
        self.whisper_main_path = whisper_main_path
        self.language_support = language_support
        self.input_device_name = input_device_name

    @staticmethod
    def from_config_file(path_to_config: str) -> "Config":
        """Load and validate configuration from JSON file.

        Args:
            path_to_config: Path to the configuration JSON file.

        Returns:
            Config: Validated configuration object.

        Raises:
            FileNotFoundError: If config file or required files don't exist.
            ValueError: If configuration is invalid.
            json.JSONDecodeError: If config file is not valid JSON.
        """
        if not os.path.exists(path_to_config):
            raise FileNotFoundError(f"Configuration file not found: {path_to_config}")

        try:
            with open(path_to_config, "r") as file:
                config = json.load(file)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

        # Validate whisper executable path
        whisper_main_path = config.get("whisper_main_path")
        if not whisper_main_path:
            raise ValueError("'whisper_main_path' is required in configuration")

        if not os.path.exists(whisper_main_path):
            raise FileNotFoundError(
                f"Whisper executable not found: {whisper_main_path}"
            )

        if not os.access(whisper_main_path, os.X_OK):
            raise ValueError(f"Whisper file is not executable: {whisper_main_path}")

        # Validate language support
        language_support = config.get("language_support")
        if language_support is None:
            raise ValueError("'language_support' is required in configuration")

        if not isinstance(language_support, list) or len(language_support) == 0:
            raise ValueError("'language_support' must be a non-empty list")

        # Parse and validate each language configuration
        language_configs = []
        seen_languages = set()
        seen_triggers = set()

        for idx, lcfg in enumerate(language_support):
            try:
                lang_config = LanguageConfig.from_config(lcfg)

                # Check for duplicate language codes
                if lang_config.language in seen_languages:
                    raise ValueError(
                        f"Duplicate language code '{lang_config.language}' in configuration"
                    )
                seen_languages.add(lang_config.language)

                # Check for duplicate trigger key combinations
                trigger_key = tuple(sorted(lang_config.trigger["keys"]))
                if trigger_key in seen_triggers:
                    raise ValueError(
                        f"Duplicate trigger key combination for language '{lang_config.language}'"
                    )
                seen_triggers.add(trigger_key)

                language_configs.append(lang_config)

            except (ValueError, FileNotFoundError) as e:
                raise ValueError(f"Error in language config [{idx}]: {e}")

        # Get input device name
        input_device_name = config.get("input_device_name")
        if not input_device_name:
            raise ValueError("'input_device_name' is required in configuration")

        # Create config object with validated device
        config_obj = Config(
            whisper_main_path,
            language_configs,
            input_device_name,
        )

        # Validate or select audio device
        config_obj._validate_and_set_device(input_device_name)

        return config_obj

    def _validate_and_set_device(self, requested_device: str) -> None:
        """Validate the requested audio device or fallback to default.

        Args:
            requested_device: Name of the requested audio device.

        Raises:
            RuntimeError: If no audio devices are available.
        """
        available_devices = self._get_available_input_devices()

        if not available_devices:
            raise RuntimeError("No audio input devices found on the system")

        # Check if requested device exists
        if requested_device in available_devices:
            logger.info(f"Using configured audio device: {requested_device}")
            self.input_device_name = requested_device
            return

        # Device not found - try to find a suitable fallback
        logger.warning(
            f"Configured audio device '{requested_device}' not found. "
            f"Available devices: {', '.join(available_devices)}"
        )

        # Try to find a microphone device
        mic_devices = [
            d
            for d in available_devices
            if "microphone" in d.lower() or "mic" in d.lower()
        ]
        if mic_devices:
            self.input_device_name = mic_devices[0]
            logger.warning(
                f"Falling back to microphone device: {self.input_device_name}"
            )
            return

        # Use the first available device
        self.input_device_name = available_devices[0]
        logger.warning(
            f"Falling back to first available device: {self.input_device_name}"
        )

    def _get_available_input_devices(self) -> List[str]:
        """Get list of available audio input devices.

        Returns:
            List of device names.
        """
        devices = []
        p = None

        try:
            p = pyaudio.PyAudio()
            api_info = p.get_host_api_info_by_index(0)
            device_count = api_info.get("deviceCount", 0)

            for idx in range(device_count):
                try:
                    device_info = p.get_device_info_by_host_api_device_index(0, idx)
                    # Only include input devices
                    if device_info.get("maxInputChannels", 0) > 0:
                        devices.append(device_info.get("name", "Unknown"))
                except Exception as e:
                    logger.debug(f"Error getting device info for index {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")
        finally:
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

        return devices

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
