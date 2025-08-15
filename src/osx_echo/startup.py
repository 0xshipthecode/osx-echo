import logging
import signal
import sys
import argparse
from pathlib import Path

from pynput import keyboard

from osx_echo.app import App
from osx_echo.recorder import Recorder
from osx_echo.transcriber import Transcriber
from osx_echo.listeners import build_key_listener, build_listener_multiplexer
from osx_echo.config import Config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="OSX Echo - Voice dictation using whisper.cpp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Use default config.json
  %(prog)s --config my_config.json  # Use custom config file
  %(prog)s --list-devices           # List available audio devices
  %(prog)s --validate-config        # Validate config without starting
""",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )

    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def list_audio_devices():
    """List all available audio input devices."""
    import pyaudio

    print("\nAvailable audio input devices:")
    print("=" * 50)

    p = None
    try:
        p = pyaudio.PyAudio()
        api_info = p.get_host_api_info_by_index(0)
        device_count = api_info.get("deviceCount", 0)

        input_devices = []
        for idx in range(device_count):
            try:
                device_info = p.get_device_info_by_host_api_device_index(0, idx)
                if device_info.get("maxInputChannels", 0) > 0:
                    input_devices.append(
                        {
                            "index": device_info.get("index"),
                            "name": device_info.get("name"),
                            "channels": device_info.get("maxInputChannels"),
                            "sample_rate": device_info.get("defaultSampleRate"),
                        }
                    )
            except Exception as e:
                logging.debug(f"Error getting device info for index {idx}: {e}")
                continue

        if not input_devices:
            print("No audio input devices found!")
        else:
            for device in input_devices:
                print(f"\nDevice {device['index']}: {device['name']}")
                print(f"  Channels: {device['channels']}")
                print(f"  Sample Rate: {device['sample_rate']:.0f} Hz")

    except Exception as e:
        print(f"Error listing audio devices: {e}")
        return False
    finally:
        if p:
            try:
                p.terminate()
            except Exception:
                pass

    print("\n" + "=" * 50)
    return True


def validate_config(config_path: str):
    """Validate configuration file.

    Args:
        config_path: Path to configuration file.

    Returns:
        bool: True if configuration is valid, False otherwise.
    """
    print(f"\nValidating configuration file: {config_path}")
    print("=" * 50)

    try:
        config = Config.from_config_file(config_path)

        print("✓ Configuration file is valid")
        print(f"\n✓ Whisper executable: {config.whisper_main_path}")
        print(f"✓ Audio device: {config.input_device_name}")
        print("\n✓ Language configurations:")

        for lang_config in config.language_support:
            print(f"  - {lang_config.language_name} ({lang_config.language})")
            print(f"    Model: {Path(lang_config.whisper_model_path).name}")
            print(
                f"    Trigger: {lang_config.trigger['type']} - {', '.join(lang_config.trigger['keys'])}"
            )

        print("\n" + "=" * 50)
        print("Configuration validation successful!\n")
        return True

    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    print("\n" + "=" * 50)
    print("Configuration validation failed!\n")
    return False


def start_app():
    """
    Orchestrates the startup of the OSX Echo application.

    This function performs the following steps:
    1. Parses command-line arguments
    2. Loads configuration from specified config file
    3. Sets up the Whisper-based transcriber
    4. Creates a recorder instance
    5. Initializes the main App with AnyBar integration
    6. Configures and starts the keyboard listener
    7. Sets up signal handling for graceful shutdown
    8. Runs the application

    The function uses configuration values from the Config class to set up
    various components of the application, including the Whisper model paths,
    input device index, and listener configuration.

    No parameters or return values.

    Raises:
        SystemExit: If configuration is invalid or list/validate mode is used.
        Potential exceptions from component initialization or configuration errors.
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle list devices mode
    if args.list_devices:
        success = list_audio_devices()
        sys.exit(0 if success else 1)

    # Handle validate config mode
    if args.validate_config:
        success = validate_config(args.config)
        sys.exit(0 if success else 1)

    # Load and validate configuration
    try:
        logging.info(f"Loading configuration from: {args.config}")
        config = Config.from_config_file(args.config)
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Failed to load configuration: {e}")
        logging.error("Use --list-devices to see available audio devices")
        logging.error("Use --validate-config to check your configuration file")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        sys.exit(1)

    transcriber = Transcriber(config.get_whisper_path())

    recorder = Recorder(transcriber, config.get_input_device_name())

    # Create AnyBar status indicator explicitly for better testability
    from osx_echo.anybar import AnyBar

    anybar = AnyBar()

    app = App(recorder, config, status_indicator=anybar)

    # Set up keyboard listeners for all configured languages
    listeners = [
        build_key_listener(app, language_config)
        for language_config in config.get_language_support()
    ]
    listener_multiplexer = build_listener_multiplexer(listeners)
    listener = keyboard.Listener(
        on_press=listener_multiplexer.on_key_press,
        on_release=listener_multiplexer.on_key_release,
    )
    listener.start()

    # Set up signal handling for graceful shutdown
    def signal_handler(sig, frame):
        logging.info("Shutting down app gracefully...")
        app.shutdown()
        listener.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the app (this will block until app.is_running is False)
    app.run()
