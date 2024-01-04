import config as cfg
from gpt.poll import LinearAdditiveGrowth, LinearMultiplicativeGrowth, ExponentialGrowth
from gpt.exceptions import ViolateContentModerationError, TimeoutError
from gpt.openai_file import OpenAiFile
from gpt.tools import execute_function
from gpt.guardrail import UserGuardRail

import tiktoken
from openai import OpenAI

import time
from typing import Any, Optional
import asyncio
import re
import os
import json


class AssistantGPT:
    backend = OpenAI(api_key=cfg.openai_api_key)

    @classmethod
    def new_thread(cls):
        return cls.backend.beta.threads.create()

    @classmethod
    def new_assistant(cls, params: dict):
        """@todo Implement this"""
        # params['id'] = assistant.id
        return params

    @classmethod
    def __is_appropriate_prompt(cls, prompt) -> tuple[bool, str]:
        return UserGuardRail.check(prompt)
        # cls.moderator = OpenAI(api_key=cfg.openai_api_key
        # result = cls.moderator.create(input=prompt, model="text-moderation-latest")
        # return not any(map(lambda x: x.flagged, result.results))

    @classmethod
    async def __polling(
        cls,
        thread_id: str,
        run_id: str,
        interval: int = 1,
        timeout: int = 180,
        callback=LinearAdditiveGrowth(),
    ) -> str:
        print("\n\nPolling...")
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
                return retrieve
            _elapsed_time += interval
            if _elapsed_time >= timeout:
                print(f"Timeout: {_elapsed_time}/{timeout} seconds reached.")
                return retrieve
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
        print("\n\nCancelling...")
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

        is_appropriate, _response = cls.__is_appropriate_prompt(prompt)
        
        if not is_appropriate:
            return {"msg": _response}, None
            # raise ViolateContentModerationError(
            #     "The content violates the content moderation policy"
            # )

        attempt = 0
        while attempt < max_retries:
            message = cls.backend.beta.threads.messages.create(
                thread_id=thread_id, role="user", content=prompt, file_ids=file_ids
            )
            # print("\nmessage: ", message)
            run_message = cls.backend.beta.threads.runs.create(
                thread_id=thread_id, assistant_id=assistant_id
            )
            # print("\nrun message: ", run_message)
            run = await cls.__polling(thread_id=thread_id, run_id=run_message.id)

            function_call_counter = 0
            while run.status == "requires_action":
                print("\n\nrequires_action\n\n")

                function_call_counter += 1
                if function_call_counter > 10:
                    
                    is_cancelled = await cls.__cancel(
                        thread_id=thread_id, run_id=run.id
                    )
                    if not is_cancelled:
                        return {"msg": "The service endpoint seems to be down. Failed to cancel the run!!!"}, None
                    return {"msg": f"Execute function call too many times: {function_call_counter}!!!"}, None

                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                print(tool_calls)
                tool_outputs = [{} for _ in range(len(tool_calls))]

                for idx, tool in enumerate(tool_calls):
                    tool_call_id = tool.id
                    function_name = tool.function.name
                    if function_call_counter > 5:
                        # provide soft warning
                        tool_outputs[idx] = {
                            "tool_call_id": tool_call_id, 
                            "output": "Apparently, you had reached the maximum number of function calls. \
                                Please try do your best to provide an answer with your best knowledge."
                            }
                        continue
                    print(f"\ntool_call_id: {tool_call_id}")
                    print(f"\nfunction_name: {function_name}")

                    # try except here
                    try:
                        function_arguments = json.loads(tool.function.arguments)
                        print(
                            f"\n\nCalling: {function_name}\nArguements: {function_arguments}\n"
                        )
                        output = execute_function(function_name, function_arguments)
                    except Exception as e:
                        output = f"Error: {str(e)}"
                        print(f"\n\n{output}", flush=True)
                    # print(f"\n\nOutput: {output}")
                    
                    tool_outputs[idx] = {"tool_call_id": tool_call_id, "output": output}

                run_submit_tool_outputs = (
                    cls.backend.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
                    )
                )
                run = await cls.__polling(thread_id=thread_id, run_id=run.id)

            if run.status == "completed":
                messages = cls.backend.beta.threads.messages.list(thread_id=thread_id)
                return {"msg": "completed"}, messages.data

            print(f"\n\nStatus: {run.status}")
            is_cancelled = await cls.__cancel(thread_id=thread_id, run_id=run.id)
            if not is_cancelled:
                return {"msg": "The service endpoint seems to be down. Failed to cancel the run!!!"}, None
            attempt += 1
        return {"msg": "The service endpoint seems to be down. Tried {attempt}!!!"}, None
