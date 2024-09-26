"""
This module contains the Recorder class, which is responsible for capturing audio
from the default recording device, saving it as a wave file, and initiating
transcription.

The module uses PyAudio for audio capture and the wave module for saving audio data.
It also interacts with a transcriber object to convert the recorded audio to text.
"""

import threading
from wave import Wave_write

import pyaudio


class Recorder:
    """
    Recorder is responsible for grabbing audio from the default recording device,
    saving it as a wave file, and calling a transcriber to convert the audio to text.

    The recording process runs in a separate thread to allow for non-blocking operation.

    TODO: Handle multiple audio devices and allow user to select one.
    """

    def __init__(self, transcriber, input_device_name):
        """
        Initialize the Recorder.

        Args:
            transcriber: An object responsible for transcribing audio.
            input_device_name (str): exact name of the input device to use.

        Note:
            This method also prints information about available audio devices.
        """
        self.is_recording = False
        self.transcriber = transcriber
        self.input_device_index = None

        p = pyaudio.PyAudio()
        api_info = p.get_host_api_info_by_index(0)
        for idx in range(api_info.get('deviceCount')):
            device_info = (p.get_device_info_by_host_api_device_index(0, idx))
            print(f"Device {device_info["index"]}: {device_info["name"]}")
            if device_info['name'] == input_device_name:
                self.input_device_index = device_info['index']

        print(f"Selected device index {self.input_device_index} [{input_device_name}]")
        assert self.input_device_index is not None

    def start(self):
        """
        Start the recording process in a new thread.

        This method sets the recording flag to True and spawns a new thread
        that runs the _recording method.
        """
        if not self.is_recording:
            self.is_recording = True
            thread = threading.Thread(target=self._recording)
            thread.start()

    def stop(self):
        """
        Stop the recording process.

        This method sets the recording flag to False, which will cause the
        recording thread to finish its execution.
        """
        self.is_recording = False

    def _recording(self):
        """
        Internal method to handle the recording process.

        This method runs in a separate thread and captures audio until `is_recording`
        is set to False. It then saves the recorded audio as a wave file and
        initiates the transcription process.

        The audio is recorded with the following parameters:
        - Format: 16-bit PCM
        - Channels: 1 (mono)
        - Sample rate: 16000 Hz
        """
        self.is_recording = True
        frames_per_buffer = 1024
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=frames_per_buffer,
            input_device_index=self.input_device_index
        )

        frames = []
        while self.is_recording:
            data = stream.read(frames_per_buffer)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        audio_data = b"".join(frames)
        w = Wave_write("recording.wav")
        w.setnchannels(1)
        w.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        w.setframerate(16000)
        w.writeframes(audio_data)
        w.close()

        # daisy chain the transcriber analyze the wav file and type result
        self.transcriber.transcribe("recording.wav")
