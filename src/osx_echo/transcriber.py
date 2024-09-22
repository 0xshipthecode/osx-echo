import subprocess

from pynput import keyboard


def _type_content(text):
    """
    Type out content on the keyboard after stripping leading whitespace and converting newlines to spaces.
    """
    ctrl = keyboard.Controller()
    raw_text = text.lstrip().replace("\n", " ")
    ctrl.type(raw_text)


class Transcriber:
    """
    Transcriber runs whisper.cpp to transcribe audio to text
    """

    def __init__(self, whisper_path, model_path):
        self.whisper_path = whisper_path
        self.model_path = model_path

    def transcribe(self, audio_path):
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
            ]
        )

        with open(audio_path + ".txt", "r") as f:
            content = f.read()
            print(content)
            _type_content(content)
