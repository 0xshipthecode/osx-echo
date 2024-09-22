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
            check=True  # Add this line
        )

        with open(audio_path + ".txt", "r", encoding="utf-8") as f:
            content = f.read()
            print(content)
            _type_content(content)
