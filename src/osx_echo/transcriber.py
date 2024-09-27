"""
This module provides functionality for transcribing audio files and simulating keyboard input.

It contains the Transcriber class, which uses whisper.cpp to convert audio to text,
and utility functions for typing out the transcribed content using keyboard simulation.

The module relies on the pynput library for keyboard control and the subprocess module
for running the whisper.cpp executable.

Classes:
    Transcriber: Handles audio transcription and text output via simulated typing.
"""

import subprocess
import time
import re

from pynput import keyboard


class Transcriber:
    """
    Transcriber uses whisper.cpp to convert audio to text and types out the result.

    This class encapsulates the functionality to transcribe audio files using
    the whisper.cpp library and automatically type out the transcribed text
    using keyboard input simulation.

    Attributes:
        whisper_path (str): Path to the whisper.cpp executable.
        model_path (str): Path to the whisper model file to be used for transcription.
    """

    def __init__(self, whisper_path, model_path):
        self.whisper_path = whisper_path
        self.model_path = model_path

    def transcribe(self, audio_path):
        """
        Transcribe the given audio file and type out the result.

        This method runs the whisper.cpp executable to transcribe the audio file,
        reads the resulting text file, and then types out the content using
        keyboard input simulation.

        Args:
            audio_path (str): Path to the audio file to be transcribed.

        Raises:
            subprocess.CalledProcessError: If the whisper.cpp process fails.
        """
        subprocess.run(
            [
                self.whisper_path,
                "-m",
                self.model_path,
                "-f",
                audio_path,
                "-t",
                "4",
                "-otxt",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with open(audio_path + ".txt", "r", encoding="utf-8") as f:
            content = f.read()
            _type_content(_clean_content(content))


def _clean_content(content):
    """
    Clean the content by stripping surrounding whitespace, converting
    newlines to spaces and reducing multiple spaces to a single space.
    """
    return content.strip().replace("\n", " ").replace("  ", " ")


def _type_content(text):
    """
    Type out content on the keyboard after stripping leading
    whitespace and converting newlines to spaces.
    """
    ctrl = keyboard.Controller()
    raw_text = text.lstrip().replace("\n", " ")
    # Remove anything between square brackets, including the brackets themselves
    clean_text = re.sub(r"\[.*?\]", "", raw_text)
    for char in clean_text:
        ctrl.type(char)
        time.sleep(0.001)
