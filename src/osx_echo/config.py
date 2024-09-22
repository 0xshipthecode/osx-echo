import os
import json

class Config:
    """
    A configuration class for managing environment variables and settings.

    This class loads and stores various configuration parameters from environment
    variables, including paths for Whisper, listener configurations, and input
    device settings.
    """

    def __init__(self):
        """
        Initialize the Config object by loading values from environment variables.
        """
        self.whisper_main_path = os.environ["WHISPER_MAIN_PATH"]
        self.whisper_model_path = os.environ["WHISPER_MODEL_PATH"]
        self.listener_config = json.loads(os.environ["LISTENER_CONFIG"])
        self.input_device_index = int(os.environ["INPUT_DEVICE_INDEX"])

    def get_listener_config(self):
        """
        Retrieve the listener configuration.

        Returns:
            dict: The listener configuration loaded from the environment.
        """
        return self.listener_config
    
    def get_whisper_config(self):
        """
        Retrieve the Whisper configuration paths.

        Returns:
            dict: A dict containing the Whisper main path and model path.
        """
        return {"whisper_main_path": self.whisper_main_path, "whisper_model_path": self.whisper_model_path}
    
    def get_input_device_index(self):
        """
        Retrieve the input device index.

        Returns:
            str: The input device index loaded from the environment.
        """
        return self.input_device_index
