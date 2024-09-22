import os
import json

from pynput import keyboard
from dotenv import load_dotenv

from osx_echo.dictation_app import DictationApp
from osx_echo.recorder import Recorder
from osx_echo.transcriber import Transcriber
from osx_echo.listeners import build_key_listener


def start_app():
    """
    This function orchestrates the startup of the entire application.  It builds the transcriber, recorder, app,
    initializes the key select listener, starts it, and then runs the application. 
    """
    load_dotenv()

    transcriber = Transcriber(
        os.environ["WHISPER_MAIN_PATH"], os.environ["WHISPER_MODEL_PATH"])

    recorder = Recorder(transcriber)
    app = DictationApp(recorder)

    listener_config = json.loads(os.environ["LISTENER_CONFIG"])
    key_listener = build_key_listener(app, listener_config)

    listener = keyboard.Listener(
        on_press=key_listener.on_key_press, on_release=key_listener.on_key_release
    )
    listener.start()

    app.run()