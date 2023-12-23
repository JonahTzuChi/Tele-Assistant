import config as cfg

import os
import re
from openai import OpenAI


class OpenAiFile:
    backend = OpenAI(api_key=cfg.openai_api_key)

    @classmethod
    def store_file(cls, filename):
        if re.search("^file-", filename) is not None:
            return filename
        file = cls.backend.files.create(file=open(filename, "rb"), purpose="assistants")
        return file.id

    @classmethod
    def load_file(cls, file_id: str, export_path: str):
        if os.path.exists(export_path):
            return None
        file = cls.backend.files.content(file_id)
        file_bytes = file.read()
        with open(export_path, "wb") as f:
            f.write(file_bytes)

    @classmethod
    def delete_file(cls, file_id: str):
        file_deleted = cls.backend.files.delete(file_id)
        print(file_deleted)
