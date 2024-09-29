# osx-echo

This package is heavily inspired by [whisper-dictation](https://github.com/foges/whisper-dictation) but uses whisper.cpp for transcription,
making it much faster and only contains remnants of the original code.

## Getting started

1. This project uses `rye` to manage Python environments.

```
rye sync
```

2. Create a `config.json` file in the root directory with your configuration settings. Here's an example structure with comments explaining each field:

```json
{
  // Path to the Whisper.cpp main executable
  "whisper_main_path": "/path/to/whisper.cpp/main",

  // Array of supported languages and their configurations
  "language_support": [
    {
      // Language code
      "language": "en",
      // Full name of the language
      "language_name": "English",
      // Path to the Whisper model for this language
      "whisper_model_path": "/path/to/whisper.cpp/models/ggml-base.en.bin",
      // Trigger configuration for activating this language
      "trigger": {
        // Type of trigger (currently supports "key_hold")
        "type": "key_hold",
        // Keys to hold for activating this language
        "keys": ["cmd_l", "cmd_r"]
      }
    },
    {
      "language": "cs",
      "language_name": "Čeština",
      "whisper_model_path": "/path/to/whisper.cpp/models/ggml-base.bin",
      "trigger": {
        "type": "key_hold",
        "keys": ["cmd_l", "alt_r"]
      }
    }
  ],
  // Name of the input audio device to use
  "input_device_name": "MacBook Air Microphone"
}
```

Ensure that you update the paths and settings according to your system configuration.

3. Run the app in your terminal.

```
./run
```

4. OS X will show dialogs that ask for Accessibility permissions which have to be granted for the application to function. If the dialog window doesn't open, you can manually provide the right permissions using the following steps:

1. `Settings` -> `Security & Privacy`
1. Click on `Accessibility`
1. Toggle the switch for your terminal application.

After those rights are granted the app will be able to type the transcribed text.

5. When you activate recording for the first time, the app will also require you to provide permissions to record from the microphone. After you grant these permissions, you will be ready to work.

## Multiple Language Support

osx-echo supports multiple languages for transcription. You can configure different languages in the `language_support` array of the `config.json` file. For each language, you can specify:

- The language code and name
- The path to the appropriate Whisper model
- A unique key combination to trigger transcription for that language

To switch between languages during use, simply use the key combination specified in the trigger configuration for each language.

## TODOs

- [x] Fix the key listener so that it correctly handles key releases in the presence of multiple key presses.
- [ ] Occasionally the app produces a segmentation fault, it's not clear why.
- [x] Remove the recording file after typing completes.
