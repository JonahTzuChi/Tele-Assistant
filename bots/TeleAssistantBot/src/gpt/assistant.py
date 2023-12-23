import config as cfg
from gpt.poll import LinearAdditiveGrowth, LinearMultiplicativeGrowth, ExponentialGrowth
from gpt.exceptions import ViolateContentModerationError, TimeoutError
from gpt.openai_file import OpenAiFile

import tiktoken
from openai import OpenAI
from openai.resources.moderations import Moderations

import time
from typing import Any, Optional
import asyncio
import re
import os


class AssistantGPT:
    backend = OpenAI(api_key=cfg.openai_api_key)
    moderator = Moderations(backend)

    @classmethod
    def new_thread(cls):
        return cls.backend.beta.threads.create()

    @classmethod
    def new_assistant(cls, params: dict):
        """ @todo Implement this """
        # params['id'] = assistant.id
        return params

    @classmethod
    def __is_appropriate_prompt(cls, prompt) -> bool:
        result = cls.moderator.create(input=prompt, model="text-moderation-latest")
        return not any(map(lambda x: x.flagged, result.results))

    @classmethod
    async def __polling(
        cls,
        thread_id: str,
        run_id: str,
        interval: int = 1,
        timeout: int = 180,
        callback=LinearAdditiveGrowth(),
    ) -> str:
        _elapsed_time = 0
        while True:
            await asyncio.sleep(interval)
            retrieve = cls.backend.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
            status = retrieve.status
            if status in [
                "completed",
                "requires_action",
                "cancelling",
                "cancelled",
                "failed",
                "expired",
            ]:
                return status
            _elapsed_time += interval
            if _elapsed_time >= timeout:
                return status
            if callback is not None:
                interval = callback(interval)

    @classmethod
    async def __cancel(
        cls,
        thread_id: str,
        run_id: str,
        interval: int = 1,
        timeout: int = 180,
        callback=LinearAdditiveGrowth(),
    ) -> bool:
        # Return True if the run is cancelled within timeout window else False
        _elapsed_time = 0
        while True:
            await asyncio.sleep(interval)
            run = cls.backend.beta.threads.runs.cancel(
                thread_id=thread_id, run_id=run_id
            )
            if run.status == "cancelled":
                return True
            _elapsed_time += interval
            if _elapsed_time >= timeout:
                break
            if callback is not None:
                interval = callback(interval)
        return False

    @classmethod
    async def instruct(
        cls,
        assistant_id: str,
        thread_id: str,
        prompt: str,
        file_names: list,
        max_retries: int = 5,
    ):
        file_ids = list()
        if len(file_names) > 0:
            file_ids = list(map(OpenAiFile.store_file, file_names))

        if not cls.__is_appropriate_prompt(prompt):
            raise ViolateContentModerationError(
                "The content violates the content moderation policy"
            )

        attempt = 0
        while attempt < max_retries:
            message = cls.backend.beta.threads.messages.create(
                thread_id=thread_id, role="user", content=prompt, file_ids=file_ids
            )
            print(message)
            run_message = cls.backend.beta.threads.runs.create(
                thread_id=thread_id, assistant_id=assistant_id
            )
            print(run_message)
            status = await cls.__polling(thread_id=thread_id, run_id=run_message.id)
            if status == "completed":
                messages = cls.backend.beta.threads.messages.list(thread_id=thread_id)
                return messages.data

            is_cancelled = await cls.__cancel(
                thread_id=thread_id, run_id=run_message.id
            )
            if not is_cancelled:
                raise TimeoutError(
                    "The service endpoint seems to be down. Failed to cancel the run!!!"
                )
            attempt += 1
        raise TimeoutError(
            f"The service endpoint seems to be down.!!! Tried {attempt} attempts."
        )
