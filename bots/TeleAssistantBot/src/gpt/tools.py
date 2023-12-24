import os
import json

from langchain.utilities import GoogleSearchAPIWrapper
from duckduckgo_search import DDGS


class GoogleSearchAgent:
    def __init__(self):
        self.__name = "GoogleSearchAgent"
        self.__google_se = GoogleSearchAPIWrapper() # configurations are done Google Site

    def description(self):
        pass

    def __call__(query, query, max_results=5):
        print(f"Begin Execution: {self.__name}...")
        output = dict()
        output['result'] = search.results(query, max_results)
        print(f"End Execution: {self.__name}")
        return json.dumps(output)

class DuckDuckGoSearchAgent:
    def __init__(self):
        self.__name = "DuckDuckGoSearchAgent"
        self.__safesearch = "moderate" # on, moderate, off
        self.__region = "my-en"

    def description(self):
        pass
        
    def __call__(self, query: str, max_results=5):
        print(f"Begin Execution: {self.__name}...")
        output = dict()
        with DDGS() as ddgs:
            output['result'] = [r for r in ddgs.text(keywords=query, region=self.__region, safesearch = self.__safesearch, max_results=max_results)]
        print(f"End Execution: {self.__name}")
        return json.dumps(output)