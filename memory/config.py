import os


class Config:
    def __init__(self, workspace: str, max_showing_nodes_when_searching=15):
        self.workspace = workspace
        self.max_showing_nodes_when_searching = max_showing_nodes_when_searching

    @property
    def tui_width(self):
        return os.get_terminal_size().columns
