"""
Unit tests for the Recorder class with comprehensive error handling coverage.
"""

import time
from unittest.mock import MagicMock, Mock

import pytest

from osx_echo.config import LanguageConfig
from osx_echo.constants import RECORDING_FILE_NAME
from osx_echo.recorder import Recorder


class TestRecorderInitialization:
    """Test Recorder initialization and device discovery."""

    def test_successful_initialization(self, mocker):
        """Test successful recorder initialization."""
        mock_transcriber = Mock()

        # Initialize recorder
        recorder = Recorder(mock_transcriber, "Test Device")

        # Assertions
        assert recorder.input_device_name == "Test Device"
        assert recorder.transcriber == mock_transcriber
        assert not recorder.is_recording



class TestRecorderStartStop:
    """Test Recorder start and stop methods."""

    @pytest.fixture
    def mock_recorder(self, mocker):
        """Create a mock recorder with initialized state."""
        mock_transcriber = Mock()
        recorder = Recorder(mock_transcriber, "Test Device")

        # Mock the _recording_wrapper method to prevent actual recording
        recorder._recording_wrapper = Mock()

        return recorder

    def test_start_recording(self, mock_recorder):
        """Test starting a recording."""
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Start recording
        mock_recorder.start(mock_language_config)

        # Assertions
        assert mock_recorder.is_recording
        assert mock_recorder.language_config == mock_language_config
        assert mock_recorder._recording_thread is not None
        # Thread may finish quickly since it's mocked

        # Clean up thread
        mock_recorder.is_recording = False
        if (
            mock_recorder._recording_thread
            and mock_recorder._recording_thread.is_alive()
        ):
            mock_recorder._recording_thread.join(timeout=1)

    def test_start_recording_already_in_progress(self, mock_recorder, caplog):
        """Test starting recording when already recording."""
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Set recording flag
        mock_recorder.is_recording = True

        # Try to start again
        mock_recorder.start(mock_language_config)

        # Should log warning and return without starting new thread
        assert "Recording already in progress" in caplog.text
        assert mock_recorder._recording_thread is None

    def test_stop_recording(self, mock_recorder):
        """Test stopping a recording."""
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Start recording first
        mock_recorder.start(mock_language_config)
        time.sleep(0.1)  # Let thread start

        # Stop recording
        result = mock_recorder.stop()

        # Assertions
        assert result is True
        assert not mock_recorder.is_recording
        assert mock_recorder.language_config is None
        assert mock_recorder._recording_thread is None

    def test_stop_recording_when_not_recording(self, mock_recorder, caplog):
        """Test stopping when no recording in progress."""
        import logging

        caplog.set_level(logging.INFO)

        result = mock_recorder.stop()

        assert result is False
        assert "No recording in progress to stop" in caplog.text

    def test_thread_creation_failure(self, mock_recorder, mocker):
        """Test handling of thread creation failure."""
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Mock threading.Thread to raise exception
        mocker.patch(
            "threading.Thread", side_effect=Exception("Thread creation failed")
        )

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            mock_recorder.start(mock_language_config)

        assert "Could not start recording" in str(exc_info.value)
        assert not mock_recorder.is_recording


class TestDynamicDeviceDiscovery:
    """Test dynamic device discovery during recording."""

    def test_device_found_at_recording_time(self, mocker):
        """Test successful device discovery when recording starts."""
        # Mock PyAudio
        mock_pyaudio_class = mocker.patch("osx_echo.recorder.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        # Mock device discovery
        mock_p.get_host_api_info_by_index.return_value = {"deviceCount": 2}
        mock_p.get_device_info_by_host_api_device_index.side_effect = [
            {"index": 0, "name": "Device 1"},
            {"index": 1, "name": "Test Device"},
        ]

        # Mock stream operations
        mock_stream = MagicMock()
        mock_p.open.return_value = mock_stream
        mock_p.get_sample_size.return_value = 2

        # Mock wave file
        mock_wave_write = mocker.patch("osx_echo.recorder.Wave_write")
        mock_wave_file = MagicMock()
        mock_wave_write.return_value = mock_wave_file

        # Create recorder
        mock_transcriber = Mock()
        recorder = Recorder(mock_transcriber, "Test Device")

        # Mock recording control
        call_count = [0]
        def control_recording(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 2:
                return False
            return True

        recorder._recording_event = MagicMock()
        recorder._recording_event.is_set.side_effect = control_recording

        # Mock language config
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Mock stream read to return some data then stop
        mock_stream.read.return_value = b"audio_data"

        # Run recording
        recorder._recording(mock_language_config)

        # Verify device was discovered dynamically
        # Check that device search was performed
        mock_p.get_host_api_info_by_index.assert_called()
        mock_p.get_device_info_by_host_api_device_index.assert_called()

        # Verify stream was opened with correct device index (1 = "Test Device")
        mock_p.open.assert_called_once()
        call_args = mock_p.open.call_args
        assert call_args.kwargs['input_device_index'] == 1

    def test_device_not_found_at_recording_time(self, mocker):
        """Test device discovery failure when recording starts."""
        # Mock PyAudio
        mock_pyaudio_class = mocker.patch("osx_echo.recorder.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        # Mock device discovery - device not found
        mock_p.get_host_api_info_by_index.return_value = {"deviceCount": 2}
        mock_p.get_device_info_by_host_api_device_index.side_effect = [
            {"index": 0, "name": "Device 1"},
            {"index": 1, "name": "Device 2"},
            # For available devices list
            {"index": 0, "name": "Device 1"},
            {"index": 1, "name": "Device 2"},
        ]

        # Create recorder
        mock_transcriber = Mock()
        recorder = Recorder(mock_transcriber, "Non-existent Device")

        # Mock language config
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Recording should fail with ValueError
        with pytest.raises(ValueError) as exc_info:
            recorder._recording(mock_language_config)

        assert "Non-existent Device" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
        assert "Available devices:" in str(exc_info.value)

    def test_device_discovery_handles_reconnected_device(self, mocker):
        """Test that device discovery works when device index changes due to reconnection."""
        # Mock PyAudio
        mock_pyaudio_class = mocker.patch("osx_echo.recorder.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        # Simulate device at different index after reconnection
        mock_p.get_host_api_info_by_index.return_value = {"deviceCount": 3}
        mock_p.get_device_info_by_host_api_device_index.side_effect = [
            {"index": 0, "name": "Built-in Microphone"},
            {"index": 1, "name": "Other Device"},
            {"index": 2, "name": "Test Device"},  # Device now at index 2
        ]

        # Mock stream operations
        mock_stream = MagicMock()
        mock_p.open.return_value = mock_stream
        mock_p.get_sample_size.return_value = 2

        # Mock wave file
        mock_wave_write = mocker.patch("osx_echo.recorder.Wave_write")
        mock_wave_file = MagicMock()
        mock_wave_write.return_value = mock_wave_file

        # Create recorder
        mock_transcriber = Mock()
        recorder = Recorder(mock_transcriber, "Test Device")

        # Mock recording control
        call_count = [0]
        def control_recording(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 2:
                return False
            return True

        recorder._recording_event = MagicMock()
        recorder._recording_event.is_set.side_effect = control_recording

        # Mock language config
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Mock stream read
        mock_stream.read.return_value = b"audio_data"

        # Run recording
        recorder._recording(mock_language_config)

        # Verify stream was opened with correct device index (2 = "Test Device")
        mock_p.open.assert_called_once()
        call_args = mock_p.open.call_args
        assert call_args.kwargs['input_device_index'] == 2


class TestRecordingMethod:
    """Test the _recording method with various scenarios."""

    @pytest.fixture
    def mock_pyaudio_stream(self, mocker):
        """Mock PyAudio and stream for recording tests."""
        # Mock PyAudio
        mock_pyaudio_class = mocker.patch("osx_echo.recorder.pyaudio.PyAudio")
        mock_p = MagicMock()
        mock_pyaudio_class.return_value = mock_p

        # Mock stream
        mock_stream = MagicMock()
        mock_p.open.return_value = mock_stream
        mock_p.get_sample_size.return_value = 2  # 16-bit audio

        # Mock Wave_write
        mock_wave_write = mocker.patch("osx_echo.recorder.Wave_write")
        mock_wave_file = MagicMock()
        mock_wave_write.return_value = mock_wave_file

        return {
            "pyaudio": mock_p,
            "stream": mock_stream,
            "wave_file": mock_wave_file,
            "wave_write_class": mock_wave_write,
        }

    def test_successful_recording(self, mocker, mock_pyaudio_stream):
        """Test successful recording and transcription."""
        # Setup recorder
        mock_transcriber = Mock()
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Create recorder with mocked initialization
        # Don't use nested patch - mock_pyaudio_stream already patches PyAudio
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder.input_device_name = "Test Device"
        recorder._find_input_device = Mock(return_value=0)
        recorder.transcriber = mock_transcriber

        # Import the actual _recording method
        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording = RealRecorder._recording.__get__(recorder, Recorder)

        # Mock audio data
        audio_data = b"test_audio_data"
        mock_pyaudio_stream["stream"].read.return_value = audio_data

        # Control recording loop - stop after 2 iterations
        iteration_count = 0

        def stop_after_iterations(*args, **kwargs):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:
                recorder._recording_event.is_set.return_value = False
            return audio_data

        mock_pyaudio_stream["stream"].read.side_effect = stop_after_iterations

        # Run recording
        recorder._recording(mock_language_config)

        # Assertions
        mock_pyaudio_stream["stream"].stop_stream.assert_called_once()
        mock_pyaudio_stream["stream"].close.assert_called_once()
        mock_pyaudio_stream["pyaudio"].terminate.assert_called_once()

        # Check wave file was written
        mock_pyaudio_stream["wave_file"].setnchannels.assert_called_with(1)
        mock_pyaudio_stream["wave_file"].setsampwidth.assert_called_with(2)
        mock_pyaudio_stream["wave_file"].setframerate.assert_called_with(16000)
        mock_pyaudio_stream["wave_file"].writeframes.assert_called()
        mock_pyaudio_stream["wave_file"].close.assert_called_once()

        # Check transcriber was called
        mock_transcriber.transcribe.assert_called_once_with(
            RECORDING_FILE_NAME, mock_language_config
        )

    def test_stream_open_failure(self, mocker, mock_pyaudio_stream):
        """Test handling of stream open failure."""
        # Setup recorder
        mock_transcriber = Mock()
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Create recorder
        # Don't use nested patch - mock_pyaudio_stream already patches PyAudio
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder.input_device_name = "Test Device"
        recorder._find_input_device = Mock(return_value=0)
        recorder.transcriber = mock_transcriber

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording = RealRecorder._recording.__get__(recorder, Recorder)

        # Mock stream open to fail
        mock_pyaudio_stream["pyaudio"].open.side_effect = Exception(
            "Device not available"
        )

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            recorder._recording(mock_language_config)

        assert "Could not open audio stream" in str(exc_info.value)
        mock_pyaudio_stream["pyaudio"].terminate.assert_called_once()

    def test_stream_read_error_recovery(self, mocker, mock_pyaudio_stream, caplog):
        """Test recovery from stream read errors."""
        # Setup recorder
        mock_transcriber = Mock()
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Don't use nested patch - mock_pyaudio_stream already patches PyAudio
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder.input_device_name = "Test Device"
        recorder._find_input_device = Mock(return_value=0)
        recorder.transcriber = mock_transcriber

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording = RealRecorder._recording.__get__(recorder, Recorder)

        # Mock stream read to fail once, then succeed, then stop
        call_count = 0

        def read_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Buffer overflow")
            elif call_count == 2:
                return b"good_data"
            else:
                recorder._recording_event.is_set.return_value = False
                return b"final_data"

        mock_pyaudio_stream["stream"].read.side_effect = read_with_error

        # Run recording
        recorder._recording(mock_language_config)

        # Should log error but continue
        assert "Error reading from audio stream" in caplog.text

        # Should still write data and transcribe
        mock_pyaudio_stream["wave_file"].writeframes.assert_called()
        mock_transcriber.transcribe.assert_called_once()

    def test_wave_file_write_failure(self, mocker, mock_pyaudio_stream):
        """Test handling of wave file write failure."""
        # Setup recorder
        mock_transcriber = Mock()
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Create a real-ish recorder object
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder.input_device_name = "Test Device"
        recorder._find_input_device = Mock(return_value=0)
        recorder.transcriber = mock_transcriber

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording = RealRecorder._recording.__get__(recorder, Recorder)

        # Make the recording stop after getting some data
        frames_read = [0]

        def read_and_stop(*args, **kwargs):
            frames_read[0] += 1
            if frames_read[0] >= 2:
                recorder._recording_event.is_set.return_value = False
            return b"audio_data"

        mock_pyaudio_stream["stream"].read = read_and_stop

        # Mock wave file write to fail
        mock_pyaudio_stream["wave_write_class"].side_effect = OSError("Disk full")

        # Should raise IOError
        with pytest.raises(IOError) as exc_info:
            recorder._recording(mock_language_config)

        assert "Could not save audio" in str(exc_info.value)

    def test_transcription_failure_doesnt_crash(
        self, mocker, mock_pyaudio_stream, caplog
    ):
        """Test that transcription failure doesn't crash the recorder."""
        import logging

        caplog.set_level(logging.ERROR)

        # Setup recorder
        mock_transcriber = Mock()
        mock_transcriber.transcribe.side_effect = Exception("Whisper failed")
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Don't use nested patch - mock_pyaudio_stream already patches PyAudio
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder.input_device_name = "Test Device"
        recorder._find_input_device = Mock(return_value=0)
        recorder.transcriber = mock_transcriber

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording = RealRecorder._recording.__get__(recorder, Recorder)

        # Record one frame then stop
        call_count = [0]

        def read_and_stop(*args, **kwargs):  # Accept kwargs for exception_on_overflow
            call_count[0] += 1
            if call_count[0] >= 2:
                recorder._recording_event.is_set.return_value = False
            return b"audio_data"

        mock_pyaudio_stream["stream"].read.side_effect = read_and_stop

        # Run recording - should not raise
        recorder._recording(mock_language_config)

        # Should log error but not crash
        assert "Transcription failed" in caplog.text

        # Wave file should still be written
        mock_pyaudio_stream["wave_file"].writeframes.assert_called()

    def test_no_audio_recorded(self, mocker, mock_pyaudio_stream, caplog):
        """Test handling when no audio frames are recorded."""
        # Setup recorder
        mock_transcriber = Mock()
        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Don't use nested patch - mock_pyaudio_stream already patches PyAudio
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = False  # Stop immediately
        recorder._recording_event.clear = Mock()
        recorder.input_device_name = "Test Device"
        recorder._find_input_device = Mock(return_value=0)
        recorder.transcriber = mock_transcriber

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording = RealRecorder._recording.__get__(recorder, Recorder)

        # Run recording - should handle gracefully
        recorder._recording(mock_language_config)

        # Should log warning
        assert "No audio frames recorded" in caplog.text

        # Should not attempt to write file or transcribe
        mock_pyaudio_stream["wave_write_class"].assert_not_called()
        mock_transcriber.transcribe.assert_not_called()


class TestRecordingWrapper:
    """Test the _recording_wrapper method."""

    def test_wrapper_handles_exceptions(self, mocker, caplog):
        """Test that wrapper catches and logs exceptions."""
        # Create mock recorder
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder._recording = Mock(side_effect=Exception("Recording failed"))

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording_wrapper = RealRecorder._recording_wrapper.__get__(
            recorder, Recorder
        )

        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Run wrapper - should not raise
        recorder._recording_wrapper(mock_language_config)

        # Should log error and reset flag
        assert "Recording thread encountered an error" in caplog.text
        recorder._recording_event.clear.assert_called()

    def test_wrapper_ensures_flag_reset(self, mocker):
        """Test that wrapper always resets is_recording flag."""
        # Create mock recorder
        recorder = Mock(spec=Recorder)
        recorder._recording_event = Mock()
        recorder._recording_event.is_set.return_value = True
        recorder._recording_event.clear = Mock()
        recorder._recording = Mock()

        from osx_echo.recorder import Recorder as RealRecorder

        recorder._recording_wrapper = RealRecorder._recording_wrapper.__get__(
            recorder, Recorder
        )

        mock_language_config = Mock(spec=LanguageConfig)
        mock_language_config.language = "en"

        # Run wrapper
        recorder._recording_wrapper(mock_language_config)

        # Flag should be reset even on success
        recorder._recording_event.clear.assert_called()
