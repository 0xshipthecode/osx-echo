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
import os
import re
import logging

from pynput import keyboard

from .config import LanguageConfig
from .logging_config import get_performance_logger

logger = logging.getLogger("transcriber")
perf_logger = get_performance_logger(__name__)


class Transcriber:
    """
    Transcriber uses whisper.cpp to convert audio to text and types out the result.

    This class encapsulates the functionality to transcribe audio files using
    the whisper.cpp library and automatically type out the transcribed text
    using keyboard input simulation.

    Attributes:
        whisper_path (str): Path to the whisper.cpp executable.
    """

    def __init__(self, whisper_main_path=None):
        """
        Initialize the Transcriber.

        Args:
            whisper_main_path (str): Path to the whisper.cpp main executable.

        Raises:
            ValueError: If whisper_main_path is None or doesn't exist.
        """
        if whisper_main_path is None:
            raise ValueError("whisper_main_path cannot be None")

        if not os.path.exists(whisper_main_path):
            raise ValueError(f"Whisper executable not found at: {whisper_main_path}")

        self.whisper_main_path = whisper_main_path
        logger.info(f"Transcriber initialized with whisper at: {whisper_main_path}")

    def transcribe(self, audio_path: str, language_support: LanguageConfig):
        """
        Transcribe the given audio file and type out the result.

        This method runs the whisper.cpp executable to transcribe the audio file,
        reads the resulting text file, and then types out the content using
        keyboard input simulation.

        Args:
            audio_path (str): Path to the audio file to be transcribed.
            language_support (LanguageConfig): Language support configuration.

        Returns:
            str: The transcribed text (before typing).

        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            RuntimeError: If the whisper.cpp process fails.
            IOError: If file operations fail.
        """
        # Validate input file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Get audio file size for metrics
        audio_size = os.path.getsize(audio_path)

        logger.info(f"Starting transcription of {audio_path}")

        output_path = audio_path + ".txt"
        transcribed_text = None

        with perf_logger.track_operation(
            "transcription",
            language=language_support.language,
            audio_size_bytes=audio_size,
        ) as tracker:
            try:
                # Run whisper.cpp with error handling
                self._run_whisper(audio_path, output_path, language_support)

                # Read and process the transcribed text
                transcribed_text = self._read_transcription(output_path)

                # Track transcription metrics
                if transcribed_text:
                    tracker.set("transcribed_length", len(transcribed_text))
                    tracker.set("words_count", len(transcribed_text.split()))
                    self._type_transcribed_text(transcribed_text)
                else:
                    logger.warning("No text to type from transcription")
                    tracker.set("transcribed_length", 0)

                return transcribed_text

            except subprocess.CalledProcessError as e:
                logger.error(f"Whisper.cpp failed with exit code {e.returncode}")
                raise RuntimeError(
                    f"Transcription failed: whisper.cpp exited with code {e.returncode}"
                ) from e

            except subprocess.TimeoutExpired as e:
                logger.error(f"Whisper.cpp timed out after {e.timeout} seconds")
                raise RuntimeError(
                    f"Transcription timed out after {e.timeout} seconds"
                ) from e

            except Exception as e:
                logger.error(f"Unexpected error during transcription: {e}")
                raise

            finally:
                # Clean up files even if transcription fails
                self._cleanup_files(audio_path, output_path)

    def _run_whisper(
        self, audio_path: str, output_path: str, language_support: LanguageConfig
    ):
        """
        Run the whisper.cpp executable to transcribe audio.

        Args:
            audio_path (str): Path to the audio file.
            output_path (str): Expected path for the output text file.
            language_support (LanguageConfig): Language configuration.

        Raises:
            subprocess.CalledProcessError: If whisper.cpp fails.
            subprocess.TimeoutExpired: If the process times out.
            RuntimeError: If the model file doesn't exist.
        """
        # Validate model file exists
        if not os.path.exists(language_support.whisper_model_path):
            raise RuntimeError(
                f"Whisper model not found: {language_support.whisper_model_path}"
            )

        cmd = [
            self.whisper_main_path,
            "-m",
            language_support.whisper_model_path,
            "-f",
            audio_path,
            "-l",
            language_support.language,
            "-t",
            "4",
            "-otxt",
        ]

        logger.debug(f"Running whisper command: {' '.join(cmd)}")

        # Track whisper.cpp execution time
        with perf_logger.track_operation(
            "whisper_cpp_execution",
            language=language_support.language,
            model=os.path.basename(language_support.whisper_model_path),
        ):
            try:
                # Run with a timeout of 60 seconds
                result = subprocess.run(
                    cmd, check=True, capture_output=True, text=True, timeout=60
                )

                # Log any warnings from stderr
                if result.stderr:
                    logger.warning(f"Whisper stderr output: {result.stderr}")

            except subprocess.CalledProcessError as e:
                # Log the actual error output for debugging
                if e.stderr:
                    logger.error(f"Whisper error output: {e.stderr}")
                if e.stdout:
                    logger.error(f"Whisper stdout: {e.stdout}")
                raise

    def _read_transcription(self, output_path: str):
        """
        Read and clean the transcribed text from the output file.

        Args:
            output_path (str): Path to the transcription output file.

        Returns:
            str: The cleaned transcribed text.

        Raises:
            FileNotFoundError: If the output file doesn't exist.
            IOError: If reading the file fails.
        """
        if not os.path.exists(output_path):
            logger.error(f"Transcription output file not found: {output_path}")
            raise FileNotFoundError(
                f"Whisper did not create output file: {output_path}"
            )

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content:
                logger.warning("Transcription file is empty")
                return ""

            cleaned_content = _clean_content(content)
            logger.info(
                f"Transcribed content: {cleaned_content[:100]}..."
                if len(cleaned_content) > 100
                else f"Transcribed content: {cleaned_content}"
            )

            return cleaned_content

        except Exception as e:
            logger.error(f"Failed to read transcription file: {e}")
            raise IOError(f"Could not read transcription from {output_path}") from e

    def _type_transcribed_text(self, text: str):
        """
        Type the transcribed text using keyboard simulation.

        Args:
            text (str): The text to type.

        Raises:
            RuntimeError: If keyboard typing fails.
        """
        try:
            _type_content(text)
            logger.debug(f"Successfully typed {len(text)} characters")
        except Exception as e:
            logger.error(f"Failed to type transcribed text: {e}")
            raise RuntimeError(f"Could not type transcribed text: {e}") from e

    def _cleanup_files(self, audio_path: str, output_path: str):
        """
        Clean up the audio and text files.

        Args:
            audio_path (str): Path to the audio file.
            output_path (str): Path to the text output file.
        """
        # Try to remove audio file
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.debug(f"Removed audio file: {audio_path}")
            except Exception as e:
                logger.warning(f"Could not remove audio file {audio_path}: {e}")

        # Try to remove text file
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                logger.debug(f"Removed text file: {output_path}")
            except Exception as e:
                logger.warning(f"Could not remove text file {output_path}: {e}")


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
