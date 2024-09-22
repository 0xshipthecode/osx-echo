import threading
import pyaudio
import wave


class Recorder:
    """
    Recorder is responsible for grabbing the audio from the default recording device and saving it to the file as wave.
    It then calls the transcriber to transcribe the audio to text.

    TODO: handle multiple audio devices and allow user to select one.
    """

    def __init__(self, transcriber):
        self.is_recording = False
        self.transcriber = transcriber

    def start(self):
        print("Recording!")
        self.is_recording = True
        thread = threading.Thread(target=self._recording)
        thread.start()

    def stop(self):
        print("Done recording!")
        self.is_recording = False

    def _recording(self):
        self.is_recording = True
        frames_per_buffer = 1024
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=frames_per_buffer,
        )

        frames = []
        while self.is_recording:
            data = stream.read(frames_per_buffer)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        audio_data = b"".join(frames)
        with wave.open("recording.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            w.setframerate(16000)
            w.writeframes(audio_data)

        self.transcriber.transcribe("recording.wav")

