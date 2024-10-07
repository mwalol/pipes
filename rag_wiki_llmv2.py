from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import os
import requests
import json

class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class Pipeline:
    class Valves(BaseModel):
        OPENAI_API_BASE_URL: str = "http://192.168.88.193:8000/v1"
        OPENAI_API_KEY: str = ""
        VECTOR_DB_URL: str = "http://192.168.88.23:5000/search"
        MODEL_ID: str = "qwen32b-coder"  # Added model_id as a variable

    def __init__(self):
        self.type = "manifold"
        self.name = "OpenAI Pipeline with Vector Database"
        
        self.valves = self.Valves(
            OPENAI_API_KEY=os.getenv(
                "OPENAI_API_KEY", "your-openai-api-key-here"
            ),
            MODEL_ID=os.getenv(
                "MODEL_ID", "qwen32b-coder"
            ),
            VECTOR_DB_URL="http://192.168.88.23:5000/search"
        )

        self.pipelines = self.get_openai_models()

    async def on_startup(self):
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")

    async def on_valves_updated(self):
        print(f"on_valves_updated:{__name__}")
        self.pipelines = self.get_openai_models()

    def get_openai_models(self):
        if self.valves.OPENAI_API_KEY:
            try:
                headers = {
                    "Authorization": f"Bearer {self.valves.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }

                response = requests.get(
                    f"{self.valves.OPENAI_API_BASE_URL}/models", headers=headers
                )

                models = response.json()
                return [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                ]

            except Exception as e:
                print(f"Error fetching models: {e}")
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

        headers = {
            "Authorization": f"Bearer {self.valves.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

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
            response = requests.post(
                f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            response.raise_for_status()

            if body.get("stream"):
                return response.iter_lines()
            else:
                return response.json()
        except Exception as e:
            return f"Error: {e}"
