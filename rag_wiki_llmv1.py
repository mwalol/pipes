from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from pydantic import BaseModel
import os
import requests
import json

class Pipeline:
    class Valves(BaseModel):
        OPENAI_API_BASE_URL: str = "http://192.168.88.193:8000/v1"
        OPENAI_API_KEY: str = ""
        VECTOR_DB_URL: str = "http://192.168.88.23:5000/search"

    def __init__(self):
        self.type = "manifold"
        self.name = "OpenAI Pipeline with Vector Database"
        
        self.valves = self.Valves(
            **{
                "OPENAI_API_KEY": os.getenv(
                    "OPENAI_API_KEY", "your-openai-api-key-here"
                ),
                "model_id": os.getenv(
                    "model_id", "qwen32b-coder"
                ),
                "VECTOR_DB_URL": "http://192.168.88.23:5000/search"
            }
        )

        self.pipelines = self.get_openai_models()
        pass

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        print(f"on_valves_updated:{__name__}")
        self.pipelines = self.get_openai_models()
        pass

    def get_openai_models(self):
        if self.valves.OPENAI_API_KEY:
            try:
                headers = {}
                headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
                headers["Content-Type"] = "application/json"

                r = requests.get(
                    f"{self.valves.OPENAI_API_BASE_URL}/models", headers=headers
                )

                models = r.json()
                return [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                    if "gpt" in model["id"]
                ]

            except Exception as e:
                print(f"Error: {e}")
                return [
                    {
                        "id": "error",
                        "name": "Could not fetch models from OpenAI, please update the API Key in the valves.",
                    },
                ]
        else:
            return []

    def query_vector_database(self, user_message: str) -> dict:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/2023.5.8"
        }
        payload = {"query": user_message}

        response = requests.post(self.valves.VECTOR_DB_URL, json=payload, headers=headers)
        results = response.json().get('results', [])

        if results:
            first_result = results[0]
            document = first_result.get('document', "No information found")
            metadata = first_result.get('metadata', {})
            return {
                "document": document,
                "metadata": metadata
            }
        else:
            return {
                "document": "No information found",
                "metadata": {}
            }

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")

        print(messages)
        print(user_message)

        # Query the vector database to get context
        context = self.query_vector_database(user_message)
        print(f"Retrieved context: {json.dumps(context, indent=2)}")

        headers = {}
        headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
        headers["Content-Type"] = "application/json"

        payload = {**body, "model": model_id}

        if "user" in payload:
            del payload["user"]
        if "chat_id" in payload:
            del payload["chat_id"]
        if "title" in payload:
            del payload["title"]

        # Construct the final question with the retrieved context
        final_question = f"Context: {context['document']}\nQuestion: {user_message}"
        payload["messages"] = [{"role": "user", "content": final_question}]

        print(payload)

        try:
            r = requests.post(
                model: self.valves.model_id,
                url=f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body.get("stream"):
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
