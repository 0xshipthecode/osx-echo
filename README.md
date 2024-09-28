# osx-echo

This package is heavily inspired by [whisper-dictation](https://github.com/foges/whisper-dictation) but uses whisper.cpp for transcription,
making it much faster and only contains remnants of the original code.

## Getting started

1. This project uses `rye` to manage Python environments.

```
rye sync
```

2. Copy the `env.example` file into `.env` and set the correct values.

```
cp env.example .env
```

3. Run the app in your terminal.

```
./run
```

4. OS X will show dialogs that ask for Accessibility permissions which have to be granted for the application to function. If the dialog window doesn't open, you can manually provide the right permissions using the following steps:

1. `Settings` -> `Security & Privacy`
1. Click on `Accessibility`
1. Toggle the switch for your teminal application.

After those rights are granted the app will be able to type the transcribed text.

5. When you activate recording for the first time, the app will also require you to provide permissions to record from the microphone. After you grant these permissions, you actually be ready to work.

## TODOs

- [x] Fix the key listener so that it correctly handles key releases in the presence of multiple key presses.
- [ ] Occasionally the app produces a segmentation fault, it's not clear why.
- [x] Remove the recording file after typing completes.
