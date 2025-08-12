"""
This module contains the Recorder class, which is responsible for capturing audio
from the default recording device, saving it as a wave file, and initiating
transcription.

The module uses PyAudio for audio capture and the wave module for saving audio data.
It also interacts with a transcriber object to convert the recorded audio to text.
"""

import threading
from wave import Wave_write

import logging

import pyaudio

from .config import LanguageConfig
from .constants import RECORDING_FILE_NAME

logger = logging.getLogger("osx_echo.recorder")


class Recorder:
    """
    Recorder is responsible for grabbing audio from the default recording device,
    saving it as a wave file, and calling a transcriber to convert the audio to text.

    The recording process runs in a separate thread to allow for non-blocking operation.
    """

    def __init__(self, transcriber, input_device_name):
        """
        Initialize the Recorder.

        Args:
            transcriber: An object responsible for transcribing audio.
            input_device_name (str): exact name of the input device to use.

        Raises:
            ValueError: If the specified input device is not found.
            RuntimeError: If PyAudio initialization fails.

        Note:
            This method also prints information about available audio devices.
        """
        self.is_recording = False
        self.transcriber = transcriber
        self.input_device_index = None
        self.language_config = None
        self._recording_thread = None
        
        # Find and set the input device
        self.input_device_index = self._find_input_device(input_device_name)
        
    def _find_input_device(self, device_name):
        """
        Find the input device by name.
        
        Args:
            device_name (str): The name of the device to find.
            
        Returns:
            int: The index of the found device.
            
        Raises:
            RuntimeError: If PyAudio initialization fails.
            ValueError: If the device is not found.
        """
        try:
            p = pyaudio.PyAudio()
            try:
                device_index = self._search_for_device(p, device_name)
                if device_index is None:
                    available = self._get_available_devices(p)
                    raise ValueError(
                        f"Input device '{device_name}' not found. "
                        f"Available devices: {', '.join(available)}"
                    )
                
                print(f"Selected device index {device_index} [{device_name}]")
                logger.info(f"Selected device index {device_index} [{device_name}]")
                return device_index
                
            finally:
                p.terminate()
                
        except ValueError:
            # Re-raise ValueError as is
            raise
        except Exception as e:
            logger.error(f"Failed to initialize audio system: {e}")
            raise RuntimeError(f"Audio system initialization failed: {e}") from e
    
    def _search_for_device(self, p, device_name):
        """
        Search for a device by name in the PyAudio system.
        
        Args:
            p: PyAudio instance.
            device_name (str): The name of the device to find.
            
        Returns:
            int or None: The device index if found, None otherwise.
            
        Raises:
            RuntimeError: If no audio devices are found.
        """
        api_info = p.get_host_api_info_by_index(0)
        device_count = api_info.get("deviceCount", 0)
        
        if device_count == 0:
            raise RuntimeError("No audio devices found")
        
        for idx in range(device_count):
            try:
                device_info = p.get_device_info_by_host_api_device_index(0, idx)
                current_device_name = device_info.get("name", "Unknown")
                device_index = device_info.get("index", -1)
                
                logger.info(f"Device {device_index}: {current_device_name}")
                print(f"Device {device_index}: {current_device_name}")
                
                if current_device_name == device_name:
                    return device_index
                    
            except Exception as e:
                logger.warning(f"Error getting device info for index {idx}: {e}")
                continue
        
        return None
    
    def _get_available_devices(self, p):
        """
        Get a list of available device names.
        
        Args:
            p: PyAudio instance.
            
        Returns:
            list: List of available device names.
        """
        available_devices = []
        api_info = p.get_host_api_info_by_index(0)
        device_count = api_info.get("deviceCount", 0)
        
        for idx in range(device_count):
            try:
                device_info = p.get_device_info_by_host_api_device_index(0, idx)
                available_devices.append(device_info.get("name", "Unknown"))
            except Exception:
                pass
                
        return available_devices

    def start(self, language_config: LanguageConfig):
        """
        Start the recording process in a new thread.

        This method sets the recording flag to True and spawns a new thread
        that runs the _recording method.
        
        Args:
            language_config (LanguageConfig): Language configuration for transcription.
            
        Raises:
            RuntimeError: If a recording is already in progress or thread creation fails.
        """
        if self.is_recording:
            logger.warning("Recording already in progress")
            return
            
        try:
            logger.info("Starting recording...")
            self.is_recording = True
            self.language_config = language_config
            
            self._recording_thread = threading.Thread(
                target=self._recording_wrapper,
                args=(language_config,),
                daemon=True
            )
            self._recording_thread.start()
            
        except Exception as e:
            self.is_recording = False
            self.language_config = None
            logger.error(f"Failed to start recording: {e}")
            raise RuntimeError(f"Could not start recording: {e}") from e

    def stop(self):
        """
        Stop the recording process.

        This method sets the recording flag to False, which will cause the
        recording thread to finish its execution.
        
        Returns:
            bool: True if recording was stopped, False if no recording was in progress.
        """
        if not self.is_recording:
            logger.info("No recording in progress to stop")
            return False
            
        logger.info("Stopping recording")
        self.is_recording = False
        
        # Wait for the recording thread to finish with a timeout
        if self._recording_thread and self._recording_thread.is_alive():
            try:
                self._recording_thread.join(timeout=5.0)
                if self._recording_thread.is_alive():
                    logger.warning("Recording thread did not stop within timeout")
            except Exception as e:
                logger.error(f"Error waiting for recording thread to stop: {e}")
        
        self.language_config = None
        self._recording_thread = None
        return True

    def _recording_wrapper(self, language_config: LanguageConfig):
        """
        Wrapper for the recording method to handle exceptions in the thread.
        
        Args:
            language_config (LanguageConfig): Language configuration for transcription.
        """
        try:
            self._recording(language_config)
        except Exception as e:
            logger.error(f"Recording thread encountered an error: {e}", exc_info=True)
            self.is_recording = False
        finally:
            self.is_recording = False

    def _recording(self, language_config: LanguageConfig):
        """
        Internal method to handle the recording process.

        This method runs in a separate thread and captures audio until `is_recording`
        is set to False. It then saves the recorded audio as a wave file and
        initiates the transcription process.

        The audio is recorded with the following parameters:
        - Format: 16-bit PCM
        - Channels: 1 (mono)
        - Sample rate: 16000 Hz

        Args:
            language_config (LanguageConfig): language configuration to use for transcription.
            
        Raises:
            RuntimeError: If audio stream cannot be opened or read.
            IOError: If audio file cannot be written.
        """
        frames_per_buffer = 1024
        sample_rate = 16000
        audio_format = pyaudio.paInt16
        channels = 1
        
        p = None
        stream = None
        frames = []
        
        try:
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            
            # Open audio stream with error handling
            try:
                stream = p.open(
                    format=audio_format,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=frames_per_buffer,
                    input_device_index=self.input_device_index,
                )
                logger.info(f"Audio stream opened successfully on device {self.input_device_index}")
            except Exception as e:
                logger.error(f"Failed to open audio stream: {e}")
                raise RuntimeError(f"Could not open audio stream on device {self.input_device_index}: {e}") from e
            
            # Record audio
            while self.is_recording:
                try:
                    data = stream.read(frames_per_buffer, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    logger.error(f"Error reading from audio stream: {e}")
                    # Continue recording despite read errors
                    continue
            
            logger.info(f"Recording stopped, captured {len(frames)} frames")
            
        finally:
            # Clean up audio resources
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                    logger.debug("Audio stream closed successfully")
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")
            
            if p is not None:
                try:
                    p.terminate()
                    logger.debug("PyAudio terminated successfully")
                except Exception as e:
                    logger.error(f"Error terminating PyAudio: {e}")
        
        # Only process audio if we have recorded data
        if not frames:
            logger.warning("No audio frames recorded")
            return
        
        # Save audio to file with error handling
        wave_file = None
        try:
            audio_data = b"".join(frames)
            wave_file = Wave_write(RECORDING_FILE_NAME)
            wave_file.setnchannels(channels)
            wave_file.setsampwidth(p.get_sample_size(audio_format))
            wave_file.setframerate(sample_rate)
            wave_file.writeframes(audio_data)
            logger.info(f"Audio written to file {RECORDING_FILE_NAME}, size: {len(audio_data)} bytes")
            
        except Exception as e:
            logger.error(f"Failed to write audio file: {e}")
            raise IOError(f"Could not save audio to {RECORDING_FILE_NAME}: {e}") from e
            
        finally:
            if wave_file is not None:
                try:
                    wave_file.close()
                except Exception as e:
                    logger.error(f"Error closing wave file: {e}")
        
        # Transcribe the audio with error handling
        try:
            self.transcriber.transcribe(RECORDING_FILE_NAME, language_config)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            # Don't re-raise transcription errors - recording was successful
            # The error is logged and the user can be notified through other means
