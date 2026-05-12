import json
from unaiverse.stats import Stats


class WStats(Stats):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._deb("Custom Company Brain Stats Class Initialized!")

    def _deb(self, msg: str):
        if self.DEBUG:
            prefix = "[DEBUG " + ("WORLD" if self.is_world else "AGENT") + "]"
            self._out(f"{prefix} [WStats] {msg}")

    def _err(self, msg: str):
        self._out("<ERROR> [WStats] " + msg)

    def _build_vault_data(self) -> dict[str, str]:
        from ._vault_data import VAULT_DATA
        return VAULT_DATA

    def _render_page(self, vault_json: str) -> str:
        from .html_renderer import render
        return render(vault_json=vault_json)

    def plot(self, since_timestamp: int = 0) -> str | None:
        if not self.is_world:
            return None
        vault_data = self._build_vault_data()
        vault_json = json.dumps(vault_data, ensure_ascii=False)
        return self._render_page(vault_json)
