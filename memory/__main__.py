import os
from memory import Client


def cli():
    workspace = os.getcwd()
    if not os.path.exists(os.path.join(workspace, "index.md")):
        print('index.md not found under {}, are you in correct path ?'.format(workspace))
        exit(0)
    Client(os.path.join(workspace)).run()
