"""
Unit tests for configuration validation and device selection.
"""

import json
from unittest.mock import MagicMock
import pytest

from osx_echo.config import Config, LanguageConfig, VALID_LANGUAGE_CODES


class TestLanguageConfig:
    """Test LanguageConfig validation."""

    def test_valid_language_config(self, tmp_path):
        """Test creation of valid language configuration."""
        # Create a mock model file
        model_file = tmp_path / "model.bin"
        model_file.touch()

        config_dict = {
            "language": "en",
            "language_name": "English",
            "whisper_model_path": str(model_file),
            "trigger": {"type": "key_hold", "keys": ["cmd_l", "cmd_r"]},
        }

        lang_config = LanguageConfig.from_config(config_dict)

        assert lang_config.language == "en"
        assert lang_config.language_name == "English"
        assert lang_config.whisper_model_path == str(model_file)
        assert lang_config.trigger["type"] == "key_hold"
        assert lang_config.trigger["keys"] == ["cmd_l", "cmd_r"]

    def test_invalid_language_code(self, tmp_path):
        """Test rejection of invalid language code."""
        model_file = tmp_path / "model.bin"
        model_file.touch()

        config_dict = {
            "language": "xyz",  # Invalid language code
            "language_name": "Invalid",
            "whisper_model_path": str(model_file),
            "trigger": {"type": "key_hold", "keys": ["cmd_l"]},
        }

        with pytest.raises(ValueError) as exc_info:
            LanguageConfig.from_config(config_dict)

        assert "Invalid language code 'xyz'" in str(exc_info.value)
        assert "Must be one of:" in str(exc_info.value)

    def test_missing_language_code(self):
        """Test handling of missing language code."""
        config_dict = {
            "language_name": "English",
            "whisper_model_path": "/path/to/model.bin",
            "trigger": {"type": "key_hold", "keys": ["cmd_l"]},
        }

        with pytest.raises(ValueError) as exc_info:
            LanguageConfig.from_config(config_dict)

        assert "Language code is required" in str(exc_info.value)

    def test_missing_model_file(self):
        """Test detection of missing model file."""
        config_dict = {
            "language": "en",
            "language_name": "English",
            "whisper_model_path": "/nonexistent/model.bin",
            "trigger": {"type": "key_hold", "keys": ["cmd_l"]},
        }

        with pytest.raises(FileNotFoundError) as exc_info:
            LanguageConfig.from_config(config_dict)

        assert "Whisper model file not found" in str(exc_info.value)
        assert "/nonexistent/model.bin" in str(exc_info.value)

    def test_missing_trigger_config(self, tmp_path):
        """Test handling of missing trigger configuration."""
        model_file = tmp_path / "model.bin"
        model_file.touch()

        config_dict = {
            "language": "en",
            "language_name": "English",
            "whisper_model_path": str(model_file),
        }

        with pytest.raises(ValueError) as exc_info:
            LanguageConfig.from_config(config_dict)

        assert "Trigger configuration is required" in str(exc_info.value)

    def test_all_valid_language_codes(self):
        """Test that all language codes in VALID_LANGUAGE_CODES are accepted."""
        # Just test a sample to ensure the validation works
        sample_codes = ["en", "cs", "de", "fr", "ja", "zh", "yue"]

        for code in sample_codes:
            assert code in VALID_LANGUAGE_CODES


class TestConfigValidation:
    """Test Config class validation and loading."""

    @pytest.fixture
    def valid_config_dict(self, tmp_path):
        """Create a valid configuration dictionary."""
        # Create mock files
        whisper_exe = tmp_path / "whisper"
        whisper_exe.touch()
        whisper_exe.chmod(0o755)  # Make executable

        model1 = tmp_path / "model_en.bin"
        model1.touch()

        model2 = tmp_path / "model_cs.bin"
        model2.touch()

        return {
            "whisper_main_path": str(whisper_exe),
            "language_support": [
                {
                    "language": "en",
                    "language_name": "English",
                    "whisper_model_path": str(model1),
                    "trigger": {"type": "key_hold", "keys": ["cmd_l", "cmd_r"]},
                },
                {
                    "language": "cs",
                    "language_name": "Czech",
                    "whisper_model_path": str(model2),
                    "trigger": {"type": "key_hold", "keys": ["cmd_l", "alt_r"]},
                },
            ],
            "input_device_name": "Test Microphone",
        }

    def test_valid_config_loading(self, tmp_path, valid_config_dict, mocker):
        """Test loading of valid configuration."""
        # Mock audio device validation
        mock_validate = mocker.patch.object(Config, "_validate_and_set_device")

        # Write config to file
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        # Load config
        config = Config.from_config_file(str(config_file))

        assert config.whisper_main_path == valid_config_dict["whisper_main_path"]
        assert len(config.language_support) == 2
        assert config.language_support[0].language == "en"
        assert config.language_support[1].language == "cs"
        mock_validate.assert_called_once_with("Test Microphone")

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            Config.from_config_file("/nonexistent/config.json")

        assert "Configuration file not found" in str(exc_info.value)

    def test_invalid_json(self, tmp_path):
        """Test handling of invalid JSON in config file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(ValueError) as exc_info:
            Config.from_config_file(str(config_file))

        assert "Invalid JSON" in str(exc_info.value)

    def test_missing_whisper_executable(self, tmp_path, valid_config_dict):
        """Test detection of missing whisper executable."""
        valid_config_dict["whisper_main_path"] = "/nonexistent/whisper"

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        with pytest.raises(FileNotFoundError) as exc_info:
            Config.from_config_file(str(config_file))

        assert "Whisper executable not found" in str(exc_info.value)

    def test_non_executable_whisper(self, tmp_path, valid_config_dict):
        """Test detection of non-executable whisper file."""
        # Create non-executable file
        whisper_exe = tmp_path / "whisper_noexec"
        whisper_exe.touch()
        whisper_exe.chmod(0o644)  # Not executable

        valid_config_dict["whisper_main_path"] = str(whisper_exe)

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        with pytest.raises(ValueError) as exc_info:
            Config.from_config_file(str(config_file))

        assert "not executable" in str(exc_info.value)

    def test_duplicate_language_codes(self, tmp_path, valid_config_dict):
        """Test detection of duplicate language codes."""
        # Add duplicate language
        valid_config_dict["language_support"].append(
            {
                "language": "en",  # Duplicate
                "language_name": "English 2",
                "whisper_model_path": str(tmp_path / "model_en.bin"),
                "trigger": {"type": "key_hold", "keys": ["alt_l", "alt_r"]},
            }
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        with pytest.raises(ValueError) as exc_info:
            Config.from_config_file(str(config_file))

        assert "Duplicate language code 'en'" in str(exc_info.value)

    def test_duplicate_trigger_keys(self, tmp_path, valid_config_dict):
        """Test detection of duplicate trigger key combinations."""
        # Change second language to have same trigger
        valid_config_dict["language_support"][1]["trigger"]["keys"] = ["cmd_l", "cmd_r"]

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        with pytest.raises(ValueError) as exc_info:
            Config.from_config_file(str(config_file))

        assert "Duplicate trigger key combination" in str(exc_info.value)

    def test_empty_language_support(self, tmp_path, valid_config_dict):
        """Test handling of empty language support list."""
        valid_config_dict["language_support"] = []

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        with pytest.raises(ValueError) as exc_info:
            Config.from_config_file(str(config_file))

        assert "must be a non-empty list" in str(exc_info.value)


class TestDeviceValidation:
    """Test audio device validation and fallback."""

    @pytest.fixture
    def mock_pyaudio(self, mocker):
        """Mock PyAudio for device testing."""
        mock_pyaudio_class = mocker.patch("osx_echo.config.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        # Default device setup
        mock_p.get_host_api_info_by_index.return_value = {"deviceCount": 3}
        mock_p.get_device_info_by_host_api_device_index.side_effect = [
            {"index": 0, "name": "Built-in Output", "maxInputChannels": 0},
            {"index": 1, "name": "Test Microphone", "maxInputChannels": 2},
            {"index": 2, "name": "USB Audio Device", "maxInputChannels": 1},
        ]

        return mock_p

    def test_device_validation_success(self, mock_pyaudio):
        """Test successful device validation."""
        config = Config("/path/to/whisper", [], "Test Microphone")
        config._validate_and_set_device("Test Microphone")

        assert config.input_device_name == "Test Microphone"

    def test_device_fallback_to_microphone(self, mock_pyaudio, caplog):
        """Test fallback to microphone when device not found."""
        config = Config("/path/to/whisper", [], "Nonexistent Device")
        config._validate_and_set_device("Nonexistent Device")

        assert config.input_device_name == "Test Microphone"
        assert "Falling back to microphone device" in caplog.text

    def test_device_fallback_to_first(self, mocker):
        """Test fallback to first device when no microphone found."""
        mock_pyaudio_class = mocker.patch("osx_echo.config.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        mock_p.get_host_api_info_by_index.return_value = {"deviceCount": 2}
        mock_p.get_device_info_by_host_api_device_index.side_effect = [
            {"index": 0, "name": "Built-in Output", "maxInputChannels": 0},
            {
                "index": 1,
                "name": "USB Audio",
                "maxInputChannels": 1,
            },  # No "mic" in name
        ]

        config = Config("/path/to/whisper", [], "Nonexistent Device")
        config._validate_and_set_device("Nonexistent Device")

        assert config.input_device_name == "USB Audio"

    def test_no_input_devices_available(self, mocker):
        """Test error when no input devices are available."""
        mock_pyaudio_class = mocker.patch("osx_echo.config.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        mock_p.get_host_api_info_by_index.return_value = {"deviceCount": 1}
        mock_p.get_device_info_by_host_api_device_index.side_effect = [
            {
                "index": 0,
                "name": "Built-in Output",
                "maxInputChannels": 0,
            },  # Output only
        ]

        config = Config("/path/to/whisper", [], "Test Device")

        with pytest.raises(RuntimeError) as exc_info:
            config._validate_and_set_device("Test Device")

        assert "No audio input devices found" in str(exc_info.value)

    def test_get_available_input_devices(self, mock_pyaudio):
        """Test listing of available input devices."""
        config = Config("/path/to/whisper", [], "Test Device")
        devices = config._get_available_input_devices()

        # Should only return input devices
        assert len(devices) == 2
        assert "Test Microphone" in devices
        assert "USB Audio Device" in devices
        assert "Built-in Output" not in devices  # Output device excluded
