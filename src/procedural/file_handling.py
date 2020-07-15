import json
import base64
from typing import Union


def encode_files(files: Union[bytes, str]):
    if isinstance(files, str):
        files = files.encode()

    data_64 = base64.b64encode(files).decode()
    #data = json.dumps({"file": data_64})
    data = {"file": data_64}
    return data
