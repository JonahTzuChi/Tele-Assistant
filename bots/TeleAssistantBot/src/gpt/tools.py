import os
import json
import re
import requests
import config as cfg

from langchain.utilities import GoogleSearchAPIWrapper
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup


class GoogleSearchAgent:
    def __init__(self):
        self.__name = "GoogleSearchAgent"
        self.__google_se = (
            GoogleSearchAPIWrapper()
        )  # configurations are done Google Site

    def description(self):
        return {
            "name": "GoogleSearch",
            "description": "Search the web through Google Search Engine, utilize this function when recent knowledge or information is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords used to run the search",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "The number of results return from the search",
                        "default": 5,
                        "validation": {
                            "min_value": 1,
                            "max_value": 10,
                            "error_message": "max_results must be an integer between 1 and 10",
                        },
                    },
                },
                "required": ["query"],
            },
        }

    def __call__(self, params: object):
        query = params.get("query")
        max_results = params.get("max_results")
        max_results = 5 if max_results is None else int(max_results)

        print(f"Begin Execution: {self.__name}...")
        output = dict()
        output["result"] = self.__google_se.results(query, max_results)
        print(f"End Execution: {self.__name}")
        return json.dumps(output)


class DuckDuckGoSearchAgent:
    def __init__(self):
        self.__name = "DuckDuckGoSearchAgent"
        self.__safesearch = "moderate"  # on, moderate, off
        self.__region = "my-en"

    def description(self):
        return {
            "name": "DuckDuckGoSearch",
            "description": "Search the web through DuckDuckGo Search Engine, utilize this function when recent knowledge or information is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords used to run the search",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "The number of results return from the search",
                        "default": 5,
                        "validation": {
                            "min_value": 1,
                            "max_value": 10,
                            "error_message": "max_results must be an integer between 1 and 10",
                        },
                    },
                },
                "required": ["query"],
            },
        }

    def __call__(self, params: object):
        query = params.get("query")
        max_results = params.get("max_results")
        max_results = 5 if max_results is None else int(max_results)

        print(f"Begin Execution: {self.__name}...")
        output = dict()
        with DDGS() as ddgs:
            output["result"] = [
                r
                for r in ddgs.text(
                    keywords=query,
                    region=self.__region,
                    safesearch=self.__safesearch,
                    max_results=max_results,
                )
            ]
        print(f"End Execution: {self.__name}")
        return json.dumps(output)


class WikipediaAgent:
    def __init__(self):
        self.__name = "WikipediaAgent"
        self.HEADERS = {"User-Agent": cfg.wikipedia_user_agent}
        self.__cache = dict()
        
    def description(self):
        return {
            "name": "scrape_wikipedia",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Valid URL to access an wikipedia page",
                        "example": "https://en.wikipedia.org/wiki/Ubuntu",
                    }
                },
                "required": ["url"],
            },
            "description": "Scrape essential information from wikipedia page.",
        }

    def __valid_url(self, url: str):
        # @TODO, language code
        return re.search("^https://\w{2}.wikipedia.org", url) is not None

    def __allowed(self):
        response = requests.get(
            "https://en.wikipedia.org/robots.txt", headers=self.HEADERS
        )
        return response.status_code == 200

    def __scrape(self, page_text: str):
        soup = BeautifulSoup(page_text, "html.parser")
        firstHeading = soup.find_all(id="firstHeading")[0].get_text()
        content = soup.find_all(id="mw-content-text")[0].get_text()

        print("content type: ", type(content))
        result = dict(firstHeading=firstHeading, content=content)
        return result

    def __call__(self, params: object):
        url = params.get("url")
        if url in self.__cache.keys():
            print("Get from cache!!!")
            return self.__cache[url]
        
        if not self.__valid_url(url):
            return "Invalid URL, only wikipedia links are supported"

        if not self.__allowed():
            return "Blocked by Wikipedia's Backend"

        page = requests.get(url, headers=self.HEADERS)
        information = self.__scrape(page.text)
        jsonStr = json.dumps(information)
        self.__cache[url] = jsonStr
        return jsonStr


class WeatherAPIAgent:
    """
    https://www.weatherapi.com/docs/#intro-request
    """
    def __init__(self):
        self.__name = "WeatherAPI"
        self.__api_key = cfg.weatherapi_api_key
        
    def description(self):
        return {
            "name": "get_weather_data",
            "description": "Get weather data from www.weatherapi.com, either current, forecast or even historical",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Either city name, US zip, UK postcode, or Latitude and Longitude"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Mode can be either current, forecast or history",
                        "default": "current",
                        "enum": ["current", "forecast", "history"]
                    },
                    "dt": {
                        "type": "string",
                        "description": "Date in yyyy-MM-dd format. This is only required for 'history'."
                    }
                },
                "required": ['q', 'mode']
            }
        }
    
    
    def __call__(self, params: object):
        # https://api.weatherapi.com/v1/forecast.json?key=cbf1d45b966e4461824131655232712&q=lumbini&days=3&aqi=no&alerts=yes
        BASE_URL = "https://api.weatherapi.com/v1"
        q = params.get("q")
        
        if q is None:
            return "Missing Arguement. q is required"
        
        mode = params.get("mode")
        
        if mode not in ["current", "forecast", "history"]:
            return "Mode must be either 'current', 'forecast' or 'history'"
        
        if mode == "current":
            url = f"{BASE_URL}/{mode}.json?key={self.__api_key}&q={q}&aqi=yes"
        elif mode == "forecast":
            url = f"{BASE_URL}/{mode}.json?key={self.__api_key}&q={q}&days=10&aqi=yes&alerts=yes"
        elif mode == "history":
            dt = params.get("dt")
            if dt is None:
                return "Missing Arguement. dt is required"
            url = f"{BASE_URL}/{mode}.json?key={self.__api_key}&q={q}&dt={dt}"
            
        response = requests.get(url)
        # print("\n\nweatherapi: ", response.text)
        
        return response.text
        
        
function_dictionary = dict()
function_dictionary["GoogleSearch"] = GoogleSearchAgent()
function_dictionary["DuckDuckGoSearch"] = DuckDuckGoSearchAgent()
function_dictionary["scrape_wikipedia"] = WikipediaAgent()
function_dictionary['get_weather_data'] = WeatherAPIAgent()

def execute_function(function_name: str, arguements: str):
    if not function_name in function_dictionary.keys():
        return "Requested function not implemented"
    return function_dictionary[function_name](arguements)
