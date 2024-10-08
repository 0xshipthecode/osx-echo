import os
import json

from pynput import keyboard

from osx_echo.app import App
from osx_echo.recorder import Recorder
from osx_echo.transcriber import Transcriber
from osx_echo.listeners import build_key_listener, build_listener_multiplexer
from osx_echo.config import Config


def start_app():
    """
    Orchestrates the startup of the OSX Echo application.

    This function performs the following steps:
    1. Loads environment variables from .env file
    2. Initializes the configuration
    3. Sets up the Whisper-based transcriber
    4. Creates a recorder instance
    5. Initializes the main DictationApp
    6. Configures and starts the keyboard listener
    7. Runs the application

    The function uses configuration values from the Config class and environment
    variables to set up various components of the application, including the
    Whisper model paths, input device index, and listener configuration.

    No parameters or return values.

    Raises:
        Potential exceptions from component initialization or configuration errors.
    """
    config = Config.from_config_file("config.json")

    transcriber = Transcriber(config.get_whisper_path())

    recorder = Recorder(transcriber, config.get_input_device_name())
    app = App(recorder, config)

    listeners = [build_key_listener(app, language_config) for language_config in config.get_language_support()]
    listener_multiplexer = build_listener_multiplexer(listeners)
    listener = keyboard.Listener(
         on_press=listener_multiplexer.on_key_press, on_release=listener_multiplexer.on_key_release
    )
    listener.start()

    app.run()
