import time

from pynput import keyboard

from osx_echo.constants import DBL_CLICK_TIMEOUT_MS


def build_key_listener(app, listener_config):
    """
    Builds a key listener based on the listener configuration.
    """
    listener_type = listener_config["type"]
    if listener_type == "double_press_cmd":
        return _DoubleCommandKeyListener(app)
    elif listener_type == "key_hold":
        return _KeyHoldListener(app, keyboard.KeyCode.from_char(listener_config["keys"]))
         
    else:
        raise ValueError(f"Invalid key type: {listener_type}")


# Double Command key listener taken from: https://github.com/foges/whisper-dictation/blob/main/whisper-dictation.py
class _DoubleCommandKeyListener:
    """
    Listens for a double command key press to start and stop recording.
    """

    def __init__(self, app):
        self.app = app
        self.key = keyboard.Key.cmd_r
        self.pressed = 0
        self.last_press_time = 0

    def on_key_press(self, key):
        if key == self.key:
            current_time = time.time()
            if (
                self.last_press_time is not None
                and current_time - self.last_press_time < DBL_CLICK_TIMEOUT_MS / 1000
            ):  # Double click to start listening
                self.app.toggle_recording()
                # Not strictly necessary due to the timeout 
                self.last_press_time = None
            else:  # Single click to stop listening
                self.last_press_time = current_time

    def on_key_release(self, key):
        pass

class _KeyHoldListener:
    """
    This listener waits for all keys in the dictionary to be pressed and held for recording to be active.
    They're all held it will record whenever one of them is released the recording will stop.
    """

    def __init__(self, app, keys):
        self.app = app
        # FIX: fix the keys_pressed array to accept the keys argument. 
        self.keys_pressed = {keyboard.Key.cmd_l: False, keyboard.Key.cmd_r: False}

    def on_key_press(self, key):
        if key in self.keys_pressed:
            self.keys_pressed[key] = True
            if all(self.keys_pressed.values()):
                self.app.start_recording(None)

    def on_key_release(self, key):
        if key in self.keys_pressed:
            # Unpress all of the keys since individual key detection seems buggy for multiple keys pressed at a time.
            # Keys can easily remain hanging, thereby future key presses might becomd false positives.   
            for k in self.keys_pressed:
                self.keys_pressed[k] = False
            self.app.stop_recording(None)
