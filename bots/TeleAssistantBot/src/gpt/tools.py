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

    def __call__(self, params: object):
        query = params.get("query")
        max_results = params.get("max_results")
        max_results = 5 if max_results is None else int(max_results)
        
        print(f"Begin Execution: {self.__name}...")
        output = dict()
        output['result'] = self.__google_se.results(query, max_results)
        print(f"End Execution: {self.__name}")
        return json.dumps(output)

class DuckDuckGoSearchAgent:
    def __init__(self):
        self.__name = "DuckDuckGoSearchAgent"
        self.__safesearch = "moderate" # on, moderate, off
        self.__region = "my-en"

    def description(self):
        pass
        
    def __call__(self, params: object):
        query = params.get("query")
        max_results = params.get("max_results")
        max_results = 5 if max_results is None else int(max_results)
            
        print(f"Begin Execution: {self.__name}...")
        output = dict()
        with DDGS() as ddgs:
            output['result'] = [r for r in ddgs.text(keywords=query, region=self.__region, safesearch = self.__safesearch, max_results=max_results)]
        print(f"End Execution: {self.__name}")
        return json.dumps(output)
    
    
function_dictionary = dict()
function_dictionary['GoogleSearch'] = GoogleSearchAgent()
function_dictionary['DuckDuckGoSearch'] = DuckDuckGoSearchAgent()

def execute_function(function_name: str, arguements: str):
    if not function_name in function_dictionary.keys():
        return "Requested function not implemented"
    return function_dictionary[function_name](arguements)