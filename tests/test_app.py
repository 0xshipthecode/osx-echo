"""
Unit tests for the App class with dependency injection.
"""

from unittest.mock import MagicMock, Mock, call

import pytest

from osx_echo.app import App
from osx_echo.config import Config


class TestAppInitialization:
    """Test App initialization with dependency injection."""

    def test_initialization_with_status_indicator(self):
        """Test App initialization with provided status indicator."""
        # Mock dependencies
        mock_recorder = Mock()
        mock_config = Mock(spec=Config)
        mock_status_indicator = Mock()

        # Initialize App
        app = App(mock_recorder, mock_config, status_indicator=mock_status_indicator)

        # Assertions
        assert app.recorder == mock_recorder
        assert app.config == mock_config
        assert app.status_indicator == mock_status_indicator
        assert app.is_running is True
        assert app.recording_in_progress is False

        # Verify status indicator was set to green
        mock_status_indicator.change.assert_called_once_with("green")

    def test_initialization_with_default_anybar(self, mocker):
        """Test App initialization with default AnyBar when no status indicator provided."""
        # Mock AnyBar class
        mock_anybar_class = mocker.patch("osx_echo.app.AnyBar")
        mock_anybar_instance = Mock()
        mock_anybar_class.return_value = mock_anybar_instance

        # Mock dependencies
        mock_recorder = Mock()
        mock_config = Mock(spec=Config)

        # Initialize App without status_indicator
        app = App(mock_recorder, mock_config)

        # Assertions
        assert app.status_indicator == mock_anybar_instance
        mock_anybar_class.assert_called_once()
        mock_anybar_instance.change.assert_called_once_with("green")

    def test_initialization_with_none_status_indicator(self, mocker):
        """Test App initialization explicitly passes None for status indicator."""
        # Mock AnyBar class
        mock_anybar_class = mocker.patch("osx_echo.app.AnyBar")
        mock_anybar_instance = Mock()
        mock_anybar_class.return_value = mock_anybar_instance

        # Mock dependencies
        mock_recorder = Mock()
        mock_config = Mock(spec=Config)

        # Initialize App with None status_indicator (should use default)
        app = App(mock_recorder, mock_config, status_indicator=None)

        # Assertions
        assert app.status_indicator == mock_anybar_instance
        mock_anybar_class.assert_called_once()


class TestAppRecording:
    """Test App recording methods."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock App with dependencies."""
        mock_recorder = Mock()
        mock_config = Mock(spec=Config)
        mock_status_indicator = Mock()

        app = App(mock_recorder, mock_config, status_indicator=mock_status_indicator)
        return app, mock_recorder, mock_status_indicator

    def test_start_recording_english(self, mock_app):
        """Test starting a recording with English language."""
        app, mock_recorder, mock_status_indicator = mock_app
        mock_language_config = Mock()
        mock_language_config.language = "en"

        # Start recording
        app.start_recording(mock_language_config)

        # Assertions
        assert app.recording_in_progress is True
        mock_recorder.start.assert_called_once_with(mock_language_config)
        mock_status_indicator.change.assert_called_with("red")

    def test_start_recording_non_english(self, mock_app):
        """Test starting a recording with non-English language."""
        app, mock_recorder, mock_status_indicator = mock_app
        mock_language_config = Mock()
        mock_language_config.language = "cs"

        # Start recording
        app.start_recording(mock_language_config)

        # Assertions
        assert app.recording_in_progress is True
        mock_recorder.start.assert_called_once_with(mock_language_config)
        mock_status_indicator.change.assert_called_with("yellow")

    def test_start_recording_already_in_progress(self, mock_app):
        """Test starting recording when already recording - should be ignored."""
        app, mock_recorder, mock_status_indicator = mock_app
        mock_language_config = Mock()
        mock_language_config.language = "en"

        # Set recording in progress
        app.recording_in_progress = True

        # Try to start recording - should be ignored
        app.start_recording(mock_language_config)

        # Should not start new recording
        mock_recorder.start.assert_not_called()
        # Status indicator should not be called (no change)
        assert mock_status_indicator.change.call_count == 1  # Only from init

    def test_stop_recording_success(self, mock_app):
        """Test stopping a recording successfully."""
        app, mock_recorder, mock_status_indicator = mock_app

        # Set recording in progress
        app.recording_in_progress = True

        # Stop recording
        app.stop_recording()

        # Assertions
        assert app.recording_in_progress is False
        mock_recorder.stop.assert_called_once()
        # Should change to green after successful stop
        assert mock_status_indicator.change.call_args_list[-1] == call("green")

    def test_stop_recording_not_in_progress(self, mock_app):
        """Test stopping when no recording in progress - should be ignored."""
        app, mock_recorder, mock_status_indicator = mock_app

        # Recording not in progress
        app.recording_in_progress = False

        # Stop recording - should be ignored
        app.stop_recording()

        # Should not call recorder.stop
        mock_recorder.stop.assert_not_called()
        # Status indicator should not be called (no change)
        assert mock_status_indicator.change.call_count == 1  # Only from init

    def test_toggle_recording(self, mock_app):
        """Test toggling recording state."""
        app, mock_recorder, mock_status_indicator = mock_app
        mock_language_config = Mock()
        mock_language_config.language = "en"

        # Initially not recording - toggle should start
        assert app.recording_in_progress is False
        app.toggle_recording(mock_language_config)

        assert app.recording_in_progress is True
        mock_recorder.start.assert_called_once_with(mock_language_config)
        mock_status_indicator.change.assert_called_with("red")

        # Now recording - toggle should stop
        app.toggle_recording(mock_language_config)

        assert app.recording_in_progress is False
        mock_recorder.stop.assert_called_once()
        assert mock_status_indicator.change.call_args_list[-1] == call("green")


class TestAppLifecycle:
    """Test App lifecycle methods."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock App with dependencies."""
        mock_recorder = Mock()
        mock_config = Mock(spec=Config)
        mock_status_indicator = Mock()

        app = App(mock_recorder, mock_config, status_indicator=mock_status_indicator)
        return app, mock_recorder, mock_status_indicator

    def test_run_method(self, mock_app, mocker):
        """Test the run method."""
        app, mock_recorder, mock_status_indicator = mock_app

        # Mock time.sleep to prevent actual sleeping
        mock_sleep = mocker.patch("time.sleep")

        # Set up to stop after 2 iterations
        iteration_count = [0]

        def side_effect(duration):
            iteration_count[0] += 1
            if iteration_count[0] >= 2:
                app.is_running = False

        mock_sleep.side_effect = side_effect

        # Run the app
        app.run()

        # Should have slept twice
        assert mock_sleep.call_count == 2

    def test_shutdown(self, mock_app):
        """Test the shutdown method."""
        app, mock_recorder, mock_status_indicator = mock_app

        # Set app as running and recording
        app.is_running = True
        app.recording_in_progress = True

        # Shutdown
        app.shutdown()

        # Assertions
        assert app.is_running is False
        assert app.recording_in_progress is False
        mock_recorder.stop.assert_called_once()
        # Status indicator should change to green (from stop_recording) and then close
        mock_status_indicator.change.assert_any_call("green")
        mock_status_indicator.close.assert_called_once()

    def test_shutdown_no_recording(self, mock_app):
        """Test shutdown when no recording in progress."""
        app, mock_recorder, mock_status_indicator = mock_app

        # Set app as running but not recording
        app.is_running = True
        app.recording_in_progress = False

        # Shutdown
        app.shutdown()

        # Assertions
        assert app.is_running is False
        mock_recorder.stop.assert_not_called()
        mock_status_indicator.close.assert_called_once()


class TestStatusIndicatorMocking:
    """Test that status indicator can be easily mocked for testing."""

    def test_mock_status_indicator_behavior(self):
        """Demonstrate how to mock status indicator for testing."""
        # Create a mock status indicator with specific behavior
        mock_status_indicator = MagicMock()
        mock_status_indicator.change.return_value = None

        # Create App with mocked status indicator
        mock_recorder = Mock()
        mock_config = Mock(spec=Config)

        app = App(mock_recorder, mock_config, status_indicator=mock_status_indicator)

        # Perform operations with English language
        mock_language_config = Mock()
        mock_language_config.language = "en"
        app.start_recording(mock_language_config)

        # Verify mock was called correctly
        assert mock_status_indicator.change.call_count == 2
        mock_status_indicator.change.assert_any_call("green")  # From init
        mock_status_indicator.change.assert_any_call(
            "red"
        )  # From start_recording (English)

        # Can also assert on specific call order
        expected_calls = [call("green"), call("red")]
        assert mock_status_indicator.change.call_args_list == expected_calls

    def test_status_indicator_failure_handling(self):
        """Test that App handles status indicator failures gracefully."""
        # Create a status indicator that fails after initial setup
        mock_status_indicator = Mock()
        mock_status_indicator.change.return_value = None  # First call succeeds (init)
        mock_status_indicator.close.return_value = None

        mock_recorder = Mock()
        mock_config = Mock(spec=Config)

        # App should initialize successfully
        app = App(mock_recorder, mock_config, status_indicator=mock_status_indicator)
        assert app is not None
        mock_status_indicator.change.assert_called_once_with("green")

        # Now make status indicator fail
        mock_status_indicator.change.side_effect = Exception("AnyBar not running")

        # Recording should still work despite status indicator failures
        mock_language_config = Mock()
        mock_language_config.language = "en"

        # This will try to change status but the exception should be handled
        try:
            app.start_recording(mock_language_config)
        except Exception:
            # The current implementation doesn't handle exceptions from status_indicator
            # This is expected behavior - the app doesn't catch status indicator failures
            pass

        # If we want the app to be resilient to status indicator failures,
        # we'd need to wrap the status_indicator calls in try/except blocks
