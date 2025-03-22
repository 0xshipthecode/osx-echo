import logging
import signal

from pynput import keyboard

from osx_echo.app import App
from osx_echo.recorder import Recorder
from osx_echo.transcriber import Transcriber
from osx_echo.listeners import build_key_listener, build_listener_multiplexer
from osx_echo.config import Config

logging.basicConfig(level=logging.INFO)


def start_app():
    """
    Orchestrates the startup of the OSX Echo application.

    This function performs the following steps:
    1. Loads configuration from config.json file
    2. Sets up the Whisper-based transcriber
    3. Creates a recorder instance
    4. Initializes the main App with AnyBar integration
    5. Configures and starts the keyboard listener
    6. Sets up signal handling for graceful shutdown
    7. Runs the application

    The function uses configuration values from the Config class to set up
    various components of the application, including the Whisper model paths,
    input device index, and listener configuration.

    No parameters or return values.

    Raises:
        Potential exceptions from component initialization or configuration errors.
    """
    config = Config.from_config_file("config.json")

    transcriber = Transcriber(config.get_whisper_path())

    recorder = Recorder(transcriber, config.get_input_device_name())
    app = App(recorder, config)

    # Set up keyboard listeners for all configured languages
    listeners = [build_key_listener(app, language_config)
                 for language_config in config.get_language_support()]
    listener_multiplexer = build_listener_multiplexer(listeners)
    listener = keyboard.Listener(
        on_press=listener_multiplexer.on_key_press, on_release=listener_multiplexer.on_key_release
    )
    listener.start()
    
    # Set up signal handling for graceful shutdown
    def signal_handler(sig, frame):
        logging.info("Shutting down app gracefully...")
        app.shutdown()
        listener.stop()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the app (this will block until app.is_running is False)
    app.run()
