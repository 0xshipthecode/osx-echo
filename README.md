# osx-echo

This package is heavily inspired by [whisper-dictation](https://github.com/foges/whisper-dictation) but uses whisper.cpp for transcription,
making it much faster.

## Getting started

1. This project uses `rye` to manage Python installations.

```
rye sync
```

2. Copy the `env.example` file into `.env` and set the correct values.

```
cp env.example .env
```

3. Run the app in your terminal. OS X will at first refuse to run the software, requiring you to give rights to record the microphone and then later accessibility rights to drive the keyboard.

1. `Settings` -> `Security & Privacy`
2. Click on `Accessibility`
3. Toggle the switch for your teminal application.

After those rights are granted the app should work.

## TODOs

- [ ] Fix the key listener so that it correctly handles key releases in the presence of multiple key presses.
- [ ] The hotkey configuration doesn't actually work yet. The app uses a fixed set of hotkeys, which is the left and right command key.
- [ ] Occasionally the app produces a segmentation fault, it's not clear why.
- [ ] The app leaves the recording file and to the transcription file intact instead of deleting it.
