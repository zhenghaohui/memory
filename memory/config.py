import json
import os


class Config:
    def __init__(self, workspace: str, max_showing_nodes_when_searching=15):
        self.workspace = workspace
        self.max_showing_nodes_when_searching = max_showing_nodes_when_searching

        with open(self.user_config_file_path, 'r') as fd:
            self.user_config = json.loads("".join([line.strip() for line in fd]))

    @property
    def user_config_file_path(self):
        return os.path.join(self.workspace, 'config.json')
