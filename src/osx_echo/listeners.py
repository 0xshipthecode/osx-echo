"""
This module provides functionality for creating and managing keyboard listeners
for the OSX Echo application. It includes classes for double-tap and key-hold
listeners, as well as utility functions for building listeners and parsing keys.

The module supports different types of listeners based on configuration,
allowing for flexible control of recording start/stop actions through keyboard
interactions.
"""

import time

from pynput import keyboard

from osx_echo.constants import DBL_CLICK_TIMEOUT_MS


def build_listener_multiplexer(listeners):
    """
    Builds a listener multiplexer based on the language configurations.
    """

    return _ListenerMultiplexer(listeners)


def build_key_listener(app, language_config):
    """
    Builds a key listener based on the listener configuration.

    Args:
        app: The main application instance.
        listener_config (dict): Configuration for the listener.

    Returns:
        A listener instance (_DoubleTapListener or _KeyHoldListener).

    Raises:
        ValueError: If an invalid listener type is specified.
    """
    listener_config = language_config.trigger
    listener_type = listener_config["type"]
    if listener_type == "double_tap":
        return _DoubleTapListener(app, _parse_key(listener_config["key"]), language_config)
    if listener_type == "key_hold":
        return _KeyHoldListener(app, [_parse_key(key) for key in listener_config["keys"]], language_config)
    if listener_type == "key_press":
        return _KeyPressListener(app,  _parse_key(listener_config["key"]), language_config)

    raise ValueError(f"Invalid key type: {listener_type}")


class _ListenerMultiplexer:
    """
    This class implements a listener that detects double taps of a specified key
    to toggle recording on and off.
    """

    def __init__(self, listeners):
        self.listeners = listeners

    def on_key_press(self, key):
        """
        Handle key press events.

        Args:
            key: The key that was pressed.
        """
        for listener in self.listeners:
            listener.on_key_press(key)

    def on_key_release(self, key):
        """
        Handle key release events.

        Args:
            key: The key that was released.
        """
        for listener in self.listeners:
            listener.on_key_release(key)


class _KeyPressListener:

    def __init__(self, app, key, language_config):
        self.app = app
        self.key = key
        self.language_config = language_config

    def on_key_press(self, key):
        """
        Handle key press events.

        Args:
            key: The key that was pressed.
        """
        if key == self.key:
            self.app.toggle_recording(self.language_config)

    def on_key_release(self, key):
        """
        Handle key release events.

        Args:
            key: The key that was released.
        """
        pass


# Double Command key listener taken from: https://github.com/foges/whisper-dictation/blob/main/whisper-dictation.py
class _DoubleTapListener:
    """
    This class implements a listener that detects double taps of a specified key
    to toggle recording on and off.
    """

    def __init__(self, app, key, language_config):
        """
        Initialize the _DoubleTapListener.

        Args:
            app: The main application instance.
            key: The key to listen for double taps.
        """
        self.app = app
        self.key = key
        self.pressed = 0
        self.last_press_time = 0
        self.language_config = language_config

    def on_key_press(self, key):
        """
        Handle key press events.

        Args:
            key: The key that was pressed.
        """
        if key == self.key:
            current_time = time.time()
            if (
                self.last_press_time is not None
                and current_time - self.last_press_time < DBL_CLICK_TIMEOUT_MS / 1000
            ):  # Double click to start listening
                self.app.toggle_recording(self.language_config)
                # Not strictly necessary due to the timeout
                self.last_press_time = None
            else:  # Single click to stop listening
                self.last_press_time = current_time

    def on_key_release(self, key):
        """
        Handle key release events.

        Args:
            key: The key that was released.
        """
        pass


class _KeyHoldListener:
    """
    This listener waits for all specified keys to be pressed and held for recording to be active.
    When all keys are held, it will record. Whenever one of them is released, the recording will stop.
    """

    def __init__(self, app, keys, language_config):
        """
        Initialize the _KeyHoldListener.

        Args:
            app: The main application instance.
            keys (list): List of keys to listen for.
        """
        self.app = app
        # FIX: fix the keys_pressed array to accept the keys argument.
        self.keys_pressed = {key: False for key in keys}
        self.language_config = language_config

    def on_key_press(self, key):
        """
        Handle key press events.

        Args:
            key: The key that was pressed.
        """
        if key in self.keys_pressed:
            self.keys_pressed[key] = True
            if all(self.keys_pressed.values()):
                self.app.start_recording(self.language_config)

    def on_key_release(self, key):
        """
        Handle key release events.

        Args:
            key: The key that was released.
        """
        if key in self.keys_pressed:
            # Unpress all of the keys since individual key detection seems buggy for multiple keys pressed at a time.
            # Keys can easily remain hanging, thereby future key presses might becomd false positives.
            for k in self.keys_pressed:
                self.keys_pressed[k] = False
            self.app.stop_recording(None)


_key_mapping = {
    "f6": keyboard.Key.f6,
    "f10": keyboard.Key.f10,
    "f13": keyboard.Key.f13,
    "f14": keyboard.Key.f14,
    "cmd_l": keyboard.Key.cmd_l,
    "cmd_r": keyboard.Key.cmd_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "alt_gr": keyboard.Key.alt_gr,
    "alt": keyboard.Key.alt,
    "ctrl": keyboard.Key.ctrl,
    "shift": keyboard.Key.shift,
    "cmd": keyboard.Key.cmd,
}


def _parse_key(key):
    if key in _key_mapping:
        return _key_mapping[key]

    raise ValueError(f"Invalid key: {key}")
