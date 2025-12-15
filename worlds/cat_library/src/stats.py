from unaiverse.stats import Stats


class WStats(Stats):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can add custom initialization here if needed
        self._deb("Custom Cat Library Stats Class Initialized!")

    def _deb(self, msg: str):
        """Prints a debug message if enabled."""
        if self.DEBUG:
            prefix = "[DEBUG " + ("WORLD" if self._is_world else "AGENT") + "]"
            self._out(f"{prefix} [WStats] {msg}")

    def _err(self, msg: str):
        """Prints an error message."""
        self._out("<ERROR> [WStats] " + msg)
