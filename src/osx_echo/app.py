"""
This module contains the DictationApp class, which is the main statusbar application
for the OSX Echo dictation tool. It provides a user interface for controlling the
recording and transcription process.
"""

import rumps

from .config import Config, LanguageConfig


class App(rumps.App):
    """
    DictationApp is the main statusbar app that governs the recording and transcribing.

    This class extends rumps.App to create a macOS menu bar application that allows
    users to start and stop recording for dictation. It manages the recording state
    and interacts with a recorder object to control the actual recording process.

    Attributes:
        recording_in_progress (bool): Indicates whether recording is currently active.
        recorder: An object responsible for handling the actual recording functionality.
    """

    def __init__(self, recorder, config: Config):
        """
        Initialize the DictationApp.

        Args:
            recorder: An object that handles the recording functionality.
        """
        super().__init__("osx_echo", "S")
        self.recording_in_progress = False
        self.recorder = recorder
        self.config = config
        menu_list = []
        for ls in self.config.language_support:
            menu_list.append(rumps.MenuItem(f"Start {
                             ls.language_name}", callback=lambda _, ls=ls: self.start_recording(ls)))

        menu_list.append(rumps.MenuItem("Stop", callback=self.stop_recording))
        self.menu = menu_list

    def start_recording(self, language_config: LanguageConfig):
        """
        Start the recording process.

        This method is called when the user clicks the "Start" menu item.
        It updates the app's state and starts the recorder if not already recording.

        Args:
            _: Unused parameter (required by rumps.clicked decorator).
        """
        if not self.recording_in_progress:
            self.recording_in_progress = True
            self.title = "R"
            self.recorder.start(language_config)

    def stop_recording(self, _):
        """
        Stop the recording process.

        This method is called when the user clicks the "Stop" menu item.
        It updates the app's state and stops the recorder if currently recording.

        Args:
            _: Unused parameter (required by rumps.clicked decorator).
        """
        if self.recording_in_progress:
            self.title = "S"
            self.recording_in_progress = False
            self.recorder.stop()

    def toggle_recording(self, language_config: LanguageConfig):
        """
        Toggle the recording state.

        This method switches between starting and stopping the recording
        based on the current recording state.
        """
        if self.recording_in_progress:
            self.stop_recording(None)
        else:
            self.start_recording(language_config)
