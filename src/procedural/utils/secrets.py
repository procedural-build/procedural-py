import os


def get_secrets(path):
    files = ["user", "password", "url"]
    data = {}

    for file in files:
        full_path = os.path.join(path, file)
        with open(full_path, 'r') as f:
            data[file] = f.read()

    return data["user"], data["password"], data["url"]