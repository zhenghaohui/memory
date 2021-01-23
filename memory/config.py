class Config:
    def __init__(self, workspace: str, max_showing_nodes_when_searching=15):
        self.workspace = workspace
        self.tui_width = 100
        self.max_showing_nodes_when_searching = max_showing_nodes_when_searching
