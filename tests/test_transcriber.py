"""
Unit tests for the Transcriber class with comprehensive error handling coverage.
"""

import os
import subprocess
from unittest.mock import Mock, call

import pytest

from osx_echo.config import LanguageConfig
from osx_echo.transcriber import Transcriber, _clean_content, _type_content


class TestTranscriberInitialization:
    """Test Transcriber initialization."""

    def test_successful_initialization(self, tmp_path):
        """Test successful transcriber initialization with valid executable."""
        # Create a mock executable file
        whisper_path = tmp_path / "whisper"
        whisper_path.touch()

        transcriber = Transcriber(str(whisper_path))

        assert transcriber.whisper_main_path == str(whisper_path)

    def test_initialization_with_none_path(self):
        """Test initialization fails when path is None."""
        with pytest.raises(ValueError) as exc_info:
            Transcriber(None)

        assert "whisper_main_path cannot be None" in str(exc_info.value)

    def test_initialization_with_nonexistent_path(self):
        """Test initialization fails when executable doesn't exist."""
        with pytest.raises(ValueError) as exc_info:
            Transcriber("/nonexistent/path/to/whisper")

        assert "Whisper executable not found" in str(exc_info.value)


class TestTranscribeMethod:
    """Test the transcribe method."""

    @pytest.fixture
    def mock_transcriber(self, tmp_path):
        """Create a mock transcriber with a valid whisper path."""
        whisper_path = tmp_path / "whisper"
        whisper_path.touch()
        return Transcriber(str(whisper_path))

    @pytest.fixture
    def mock_audio_file(self, tmp_path):
        """Create a mock audio file."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        return str(audio_file)

    @pytest.fixture
    def mock_language_config(self, tmp_path):
        """Create a mock language configuration."""
        model_path = tmp_path / "model.bin"
        model_path.touch()

        config = Mock(spec=LanguageConfig)
        config.whisper_model_path = str(model_path)
        config.language = "en"
        return config

    def test_successful_transcription(
        self, mocker, mock_transcriber, mock_audio_file, mock_language_config
    ):
        """Test successful transcription process."""
        # Mock subprocess.run
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stderr="", stdout="")

        # Create output file that whisper would create
        output_file = mock_audio_file + ".txt"
        with open(output_file, "w") as f:
            f.write("Hello world")

        # Mock _type_content
        mock_type = mocker.patch("osx_echo.transcriber._type_content")

        # Run transcription
        result = mock_transcriber.transcribe(mock_audio_file, mock_language_config)

        # Assertions
        assert result == "Hello world"
        mock_run.assert_called_once()
        mock_type.assert_called_once_with("Hello world")

        # Verify files were cleaned up
        assert not os.path.exists(mock_audio_file)
        assert not os.path.exists(output_file)

    def test_audio_file_not_found(self, mock_transcriber, mock_language_config):
        """Test handling of missing audio file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            mock_transcriber.transcribe("/nonexistent/audio.wav", mock_language_config)

        assert "Audio file not found" in str(exc_info.value)

    def test_whisper_process_failure(
        self, mocker, mock_transcriber, mock_audio_file, mock_language_config
    ):
        """Test handling of whisper.cpp process failure."""
        # Mock subprocess.run to raise CalledProcessError
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "whisper", stderr="Error: Invalid model"
        )

        with pytest.raises(RuntimeError) as exc_info:
            mock_transcriber.transcribe(mock_audio_file, mock_language_config)

        assert "Transcription failed" in str(exc_info.value)
        assert "exited with code 1" in str(exc_info.value)

        # Verify audio file was still cleaned up
        assert not os.path.exists(mock_audio_file)

    def test_whisper_timeout(
        self, mocker, mock_transcriber, mock_audio_file, mock_language_config
    ):
        """Test handling of whisper.cpp timeout."""
        # Mock subprocess.run to raise TimeoutExpired
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired("whisper", 60)

        with pytest.raises(RuntimeError) as exc_info:
            mock_transcriber.transcribe(mock_audio_file, mock_language_config)

        assert "Transcription timed out" in str(exc_info.value)
        assert "60 seconds" in str(exc_info.value)

        # Verify cleanup still happened
        assert not os.path.exists(mock_audio_file)

    def test_output_file_not_created(
        self, mocker, mock_transcriber, mock_audio_file, mock_language_config
    ):
        """Test handling when whisper doesn't create output file."""
        # Mock subprocess.run to succeed
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stderr="", stdout="")

        # Don't create the output file

        with pytest.raises(FileNotFoundError) as exc_info:
            mock_transcriber.transcribe(mock_audio_file, mock_language_config)

        assert "Whisper did not create output file" in str(exc_info.value)

    def test_empty_transcription(
        self, mocker, mock_transcriber, mock_audio_file, mock_language_config, caplog
    ):
        """Test handling of empty transcription."""
        import logging

        caplog.set_level(logging.WARNING)

        # Mock subprocess.run
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stderr="", stdout="")

        # Create empty output file
        output_file = mock_audio_file + ".txt"
        with open(output_file, "w") as f:
            f.write("")

        # Mock _type_content
        mock_type = mocker.patch("osx_echo.transcriber._type_content")

        # Run transcription
        result = mock_transcriber.transcribe(mock_audio_file, mock_language_config)

        # Assertions
        assert result == ""
        assert "No text to type from transcription" in caplog.text
        mock_type.assert_not_called()

    def test_typing_failure(
        self, mocker, mock_transcriber, mock_audio_file, mock_language_config
    ):
        """Test handling of keyboard typing failure."""
        # Mock subprocess.run
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(stderr="", stdout="")

        # Create output file
        output_file = mock_audio_file + ".txt"
        with open(output_file, "w") as f:
            f.write("Hello world")

        # Mock _type_content to raise exception
        mock_type = mocker.patch("osx_echo.transcriber._type_content")
        mock_type.side_effect = Exception("Keyboard error")

        with pytest.raises(RuntimeError) as exc_info:
            mock_transcriber.transcribe(mock_audio_file, mock_language_config)

        assert "Could not type transcribed text" in str(exc_info.value)

        # Verify cleanup still happened
        assert not os.path.exists(mock_audio_file)
        assert not os.path.exists(output_file)


class TestRunWhisperMethod:
    """Test the _run_whisper method."""

    @pytest.fixture
    def mock_transcriber(self, tmp_path):
        """Create a mock transcriber."""
        whisper_path = tmp_path / "whisper"
        whisper_path.touch()
        return Transcriber(str(whisper_path))

    def test_model_file_not_found(self, mock_transcriber):
        """Test handling of missing model file."""
        config = Mock(spec=LanguageConfig)
        config.whisper_model_path = "/nonexistent/model.bin"
        config.language = "en"

        with pytest.raises(RuntimeError) as exc_info:
            mock_transcriber._run_whisper("audio.wav", "output.txt", config)

        assert "Whisper model not found" in str(exc_info.value)

    def test_whisper_with_stderr_warnings(
        self, mocker, mock_transcriber, tmp_path, caplog
    ):
        """Test that stderr warnings are logged."""
        import logging

        caplog.set_level(logging.WARNING)

        # Create model file
        model_path = tmp_path / "model.bin"
        model_path.touch()

        config = Mock(spec=LanguageConfig)
        config.whisper_model_path = str(model_path)
        config.language = "en"

        # Mock subprocess.run with stderr
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            stderr="Warning: Low confidence transcription", stdout="", returncode=0
        )

        mock_transcriber._run_whisper("audio.wav", "output.txt", config)

        assert "Warning: Low confidence transcription" in caplog.text


class TestReadTranscriptionMethod:
    """Test the _read_transcription method."""

    @pytest.fixture
    def mock_transcriber(self, tmp_path):
        """Create a mock transcriber."""
        whisper_path = tmp_path / "whisper"
        whisper_path.touch()
        return Transcriber(str(whisper_path))

    def test_read_successful(self, mock_transcriber, tmp_path):
        """Test successful reading of transcription."""
        output_file = tmp_path / "output.txt"
        output_file.write_text("  Hello world  \n\n")

        result = mock_transcriber._read_transcription(str(output_file))

        assert result == "Hello world"

    def test_read_file_not_found(self, mock_transcriber):
        """Test handling of missing output file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            mock_transcriber._read_transcription("/nonexistent/output.txt")

        assert "Whisper did not create output file" in str(exc_info.value)

    def test_read_io_error(self, mocker, mock_transcriber, tmp_path):
        """Test handling of IO errors when reading."""
        output_file = tmp_path / "output.txt"
        output_file.touch()

        # Mock open to raise IOError
        mocker.patch("builtins.open", side_effect=OSError("Permission denied"))

        with pytest.raises(IOError) as exc_info:
            mock_transcriber._read_transcription(str(output_file))

        assert "Could not read transcription" in str(exc_info.value)


class TestCleanupFiles:
    """Test the _cleanup_files method."""

    @pytest.fixture
    def mock_transcriber(self, tmp_path):
        """Create a mock transcriber."""
        whisper_path = tmp_path / "whisper"
        whisper_path.touch()
        return Transcriber(str(whisper_path))

    def test_cleanup_both_files(self, mock_transcriber, tmp_path):
        """Test successful cleanup of both files."""
        audio_file = tmp_path / "audio.wav"
        text_file = tmp_path / "output.txt"
        audio_file.touch()
        text_file.touch()

        mock_transcriber._cleanup_files(str(audio_file), str(text_file))

        assert not audio_file.exists()
        assert not text_file.exists()

    def test_cleanup_nonexistent_files(self, mock_transcriber, caplog):
        """Test cleanup handles nonexistent files gracefully."""
        mock_transcriber._cleanup_files(
            "/nonexistent/audio.wav", "/nonexistent/output.txt"
        )

        # Should not raise any exceptions
        assert True

    def test_cleanup_with_permission_error(
        self, mocker, mock_transcriber, tmp_path, caplog
    ):
        """Test cleanup handles permission errors gracefully."""
        import logging

        caplog.set_level(logging.WARNING)

        audio_file = tmp_path / "audio.wav"
        text_file = tmp_path / "output.txt"
        audio_file.touch()
        text_file.touch()

        # Mock os.remove to raise PermissionError
        original_remove = os.remove

        def mock_remove(path):
            if "audio" in path:
                raise PermissionError("Cannot delete")
            original_remove(path)

        mocker.patch("os.remove", side_effect=mock_remove)

        mock_transcriber._cleanup_files(str(audio_file), str(text_file))

        assert "Could not remove audio file" in caplog.text
        assert "Cannot delete" in caplog.text


class TestUtilityFunctions:
    """Test utility functions."""

    def test_clean_content(self):
        """Test _clean_content function."""
        assert _clean_content("  Hello  \n  World  ") == "Hello   World"
        assert _clean_content("Multiple  spaces") == "Multiple spaces"
        assert _clean_content("\n\n") == ""
        assert _clean_content("") == ""

    def test_type_content(self, mocker):
        """Test _type_content function."""
        mock_controller = mocker.patch("pynput.keyboard.Controller")
        mock_ctrl_instance = Mock()
        mock_controller.return_value = mock_ctrl_instance

        _type_content("Hello [INAUDIBLE] World")

        # Should type "Hello  World" (brackets removed)
        expected_calls = [call(c) for c in "Hello  World"]
        mock_ctrl_instance.type.assert_has_calls(expected_calls)

    def test_type_content_with_newlines(self, mocker):
        """Test _type_content handles newlines."""
        mock_controller = mocker.patch("pynput.keyboard.Controller")
        mock_ctrl_instance = Mock()
        mock_controller.return_value = mock_ctrl_instance

        _type_content("\nHello\nWorld")

        # Should type "Hello World" (leading whitespace stripped, newlines to spaces)
        expected_calls = [call(c) for c in "Hello World"]
        mock_ctrl_instance.type.assert_has_calls(expected_calls)
