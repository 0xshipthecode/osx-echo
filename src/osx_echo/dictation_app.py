import rumps

class DictationApp(rumps.App):
    """
    DictationApp is the main statusbar app that governs the recording and transcribing.
    """

    def __init__(self, recorder):
        super().__init__("osx_echo", "⏯")
        self.recording_in_progress = False
        self.recorder = recorder
        self.menu = [
            rumps.MenuItem("Start", callback=self.start_recording),
            rumps.MenuItem("Stop", callback=self.stop_recording),
        ]

    @rumps.clicked("Start")
    def start_recording(self, _):
        if not self.recording_in_progress:
            self.recording_in_progress = True
            self.title = "⏺"
            self.recorder.start()

    @rumps.clicked("Stop")
    def stop_recording(self, _):
        if self.recording_in_progress:
            self.title = "Ready"
            self.recording_in_progress = False
            self.recorder.stop()

    def toggle_recording(self):
        if self.recording_in_progress:
            self.stop_recording(None)
        else:
            self.start_recording(None)

