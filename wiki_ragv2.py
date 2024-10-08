from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
from schemas import OpenAIChatMessage
import requests
import os

class Pipeline:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.name = "Vector Database Pipeline"
        self.valves = self.Valves(**{"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")})

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")
        
        if body.get("title", False):
            print("Title Generation")
            return "Vector Database Pipeline"
        print(f"wayhya")
        print(f"body: {body}")
        
        url = "http://192.168.88.23:5000/search"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/2023.5.8"
        }
        payload = {"query": user_message}

        response = requests.post(url, json=payload, headers=headers)
        results = response.json().get('results', [])

        context = None
        if results:
            first_result = results[0]
            context = first_result.get('document', "No information found")
            print(f"Retrieved context: {context}")
        else:
            context = "No information found"

        return context
