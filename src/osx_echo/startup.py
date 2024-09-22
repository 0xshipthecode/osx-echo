import os
import json

from pynput import keyboard
from dotenv import load_dotenv

from osx_echo.dictation_app import DictationApp
from osx_echo.recorder import Recorder
from osx_echo.transcriber import Transcriber
from osx_echo.listeners import build_key_listener
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
    load_dotenv()

    config = Config()

    whisper_config = config.get_whisper_config()
    transcriber = Transcriber(whisper_config["whisper_main_path"], whisper_config["whisper_model_path"])

    recorder = Recorder(transcriber, config.get_input_device_index())
    app = DictationApp(recorder)

    key_listener = build_key_listener(app, config.get_listener_config())

    listener = keyboard.Listener(
        on_press=key_listener.on_key_press, on_release=key_listener.on_key_release
    )
    listener.start()

    app.run()
