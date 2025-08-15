"""
This module contains the App class, which is the main application
for the OSX Echo dictation tool. It provides a control interface for the
recording and transcription process with status indicators using pyAnyBar.
"""

from .anybar import AnyBar
import time

from .config import Config, LanguageConfig


class App:
    """
    App is the main class that governs the recording and transcribing.

    This class manages the recording state, interacts with a recorder object to control
    the actual recording process, and uses pyAnyBar to show status indicators.

    Attributes:
        recording_in_progress (bool): Indicates whether recording is currently active.
        recorder: An object responsible for handling the actual recording functionality.
    """

    def __init__(self, recorder, config: Config, status_indicator=None):
        """
        Initialize the App.

        Args:
            recorder: An object that handles the recording functionality.
            config (Config): Configuration object with application settings.
            status_indicator: Optional status indicator instance (defaults to AnyBar).
        """
        self.recording_in_progress = False
        self.recorder = recorder
        self.config = config

        # Use provided status indicator or default to AnyBar
        self.status_indicator = (
            status_indicator if status_indicator is not None else AnyBar()
        )
        self.status_indicator.change("green")

        # Flag to control the app's running state
        self.is_running = True

    def start_recording(self, language_config: LanguageConfig):
        """
        Start the recording process.

        This method updates the app's state and starts the recorder if not already recording.

        Args:
            language_config (LanguageConfig): Language configuration to use for transcription.
        """
        if not self.recording_in_progress:
            self.recording_in_progress = True
            # Change AnyBar indicator to red to show recording is in progress
            status_color = "red" if language_config.language == "en" else "yellow"
            self.status_indicator.change(status_color)
            self.recorder.start(language_config)

    def stop_recording(self):
        """
        Stop the recording process.

        This method updates the app's state and stops the recorder if currently recording.
        """
        if self.recording_in_progress:
            self.recording_in_progress = False
            # Change AnyBar indicator back to green to show recording stopped
            self.status_indicator.change("green")
            self.recorder.stop()

    def toggle_recording(self, language_config: LanguageConfig):
        """
        Toggle the recording state.

        This method switches between starting and stopping the recording
        based on the current recording state.

        Args:
            language_config (LanguageConfig): Language configuration to use when starting recording.
        """
        if self.recording_in_progress:
            self.stop_recording()
        else:
            self.start_recording(language_config)

    def run(self):
        """
        Run the application in a loop to keep it alive.

        This method replaces the rumps.App.run() method and provides a simple
        loop to keep the application running.
        """
        try:
            # Simple loop to keep the app running
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """
        Clean shutdown of the application.
        """
        if self.recording_in_progress:
            self.stop_recording()
        self.is_running = False
        # Close the AnyBar connection
        self.status_indicator.close()
