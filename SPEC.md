# osx-echo: High-Level Specification

## 1. Overview

**osx-echo** is a macOS native dictation application that provides a fast and efficient way to transcribe spoken words into text in soft real-time. It leverages the power of `whisper.cpp` for local, high-performance speech-to-text conversion, offering an alternative to cloud-based dictation services. The application is designed to be lightweight and configurable, allowing users to define their own keyboard shortcuts and language models. The application is intended to be used to transcribe short utterances and type them out on the keyboard into any text field that is currently in focus.

## 2. User Services

The primary service provided by **osx-echo** is to enable users to dictate text into any active application on their macOS system. The user interacts with the application through keyboard shortcuts to start and stop recording. The application provides visual feedback on its status through the macOS menu bar.

### Key Features:

- **Keyboard-driven dictation:** Users can start and stop dictation using configurable keyboard shortcuts.
- **Multi-language support:** The application can be configured to use different `whisper.cpp` models for different languages, each with its own activation shortcut.
- **Visual feedback:** The application uses `AnyBar` to display a status icon in the menu bar, indicating whether it is idle, recording, or transcribing.
- **Local transcription:** All transcription is done locally using `whisper.cpp`, ensuring privacy and offline functionality.

## 3. System Components

The application is composed of several key components that work together to provide the dictation service.

### 3.1. `App` (Main Application)

- **Purpose:** The central component that orchestrates the entire application. It manages the application's state (e.g., `recording_in_progress`), initializes other components, and handles the main application loop.
- **Interactions:**
  - Receives commands from the `KeyListener` to start or stop recording.
  - Instructs the `Recorder` to begin or end audio capture.
  - Updates the `AnyBar` to reflect the current application state.

### 3.2. `Config` (Configuration Manager)

- **Purpose:** Responsible for loading and providing access to the application's configuration from a `config.json` file. This includes paths to `whisper.cpp`, language model settings, and keyboard shortcut definitions.
- **Interactions:**
  - Read by the `App` at startup to configure the application.
  - Provides settings to the `Recorder`, `Transcriber`, and `KeyListener` components.

### 3.3. `KeyListener` (Keyboard Shortcut Manager)

- **Purpose:** Listens for global keyboard events to detect user-defined shortcuts for starting and stopping dictation. It supports different types of triggers, such as key holds and double-taps.
- **Interactions:**
  - Monitors keyboard input using the `pynput` library.
  - When a valid shortcut is detected, it calls the appropriate method on the `App` instance (e.g., `app.start_recording()`).

### 3.4. `Recorder` (Audio Capture)

- **Purpose:** Manages the process of recording audio from the user's microphone. It uses `pyaudio` to capture audio and saves it to a temporary file.
- **Interactions:**
  - Initiated by the `App` to start recording.
  - Once recording is stopped, it passes the path to the recorded audio file to the `Transcriber`.

### 3.5. `Transcriber` (Speech-to-Text Engine)

- **Purpose:** The core component responsible for converting the recorded audio into text. It uses the `whisper.cpp` command-line tool to perform the transcription.
- **Interactions:**
  - Receives the audio file path from the `Recorder`.
  - Executes `whisper.cpp` as a subprocess.
  - Reads the transcribed text from the output file.
  - Uses `pynput` to simulate keyboard input and type the transcribed text into the active application.

### 3.6. `AnyBar` (Status Indicator)

- **Purpose:** Provides visual feedback to the user about the application's status by changing the color of an icon in the macOS menu bar.
- **Interactions:**
  - Controlled by the `App` to change its color based on the application's state (e.g., green for idle, red for recording).

## 4. Component Interaction Diagram

```
+-----------------+      +----------------+      +----------------+
|   KeyListener   |----->|      App       |<---->|     AnyBar     |
+-----------------+      +----------------+      +----------------+
        |                      |
        | (start/stop)         | (start/stop)
        |                      |
        v                      v
+-----------------+      +----------------+      +----------------+
|    Recorder     |----->|   Transcriber  |----->|   whisper.cpp  |
+-----------------+      +----------------+      +----------------+
        |                      ^
        | (audio file)         | (config)
        |                      |
        +----------------------+
```

## 5. Data Flow

1.  The user presses the configured keyboard shortcut.
2.  The `KeyListener` detects the shortcut and notifies the `App`.
3.  The `App` changes its state to "recording" and updates the `AnyBar` icon to red.
4.  The `App` instructs the `Recorder` to start capturing audio.
5.  The `Recorder` records audio from the microphone and saves it to a temporary `.wav` file.
6.  When the user releases the key(s), the `KeyListener` notifies the `App` to stop recording.
7.  The `App` changes its state to "idle" and updates the `AnyBar` icon to green.
8.  The `Recorder` stops recording and passes the audio file path to the `Transcriber`.
9.  The `Transcriber` invokes `whisper.cpp` with the appropriate language model to transcribe the audio file.
10. The `Transcriber` reads the resulting text file.
11. The `Transcriber` simulates keyboard input to type the text into the currently focused application.
12. The temporary audio and text files are deleted.
