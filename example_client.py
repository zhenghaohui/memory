import os

from memory import Client

if __name__ == '__main__':
    client = Client(os.path.join(os.getcwd(), 'memory/example_concept'))
    client.run()
