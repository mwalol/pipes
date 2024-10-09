"""
title: LangGraph Pipeline
author: open-webui
date: 2024-10-08
version: 1.0
license: MIT
description: A pipeline for using tools with LangChain and LangGraph.
requirements: langchain, langchain_community, langgraph
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, START
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
import os
import time
import random


class Pipeline:

    class Valves(BaseModel):
        INFERENCE_SERVER_URL: str
        MODEL_NAME: str
        TOOL_SERVER_URL: str

    def __init__(self):
        self.valves = self.Valves(
            **{
                "INFERENCE_SERVER_URL": os.getenv("INFERENCE_SERVER_URL", "http://192.168.88.193:8000/v1"),
                "MODEL_NAME": os.getenv("MODEL_NAME", "qwen32b-coder"),
                "TOOL_SERVER_URL": os.getenv("TOOL_SERVER_URL", "http://192.168.88.193:8000/v1"),
            }
        )

        self.llm = ChatOpenAI(
            model=self.valves.MODEL_NAME,
            openai_api_key="EMPTY",
            openai_api_base=self.valves.INFERENCE_SERVER_URL,
            max_tokens=3000,
            temperature=0.7,
        )

        self.tools = [
            self.add,
            self.multiply,
            self.divide,
            self.DuckDuckGoSearchRun
        ]

        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # System message
        self.sys_msg = SystemMessage(content="You are a helpful assistant tasked with using search and performing arithmetic on a set of inputs.")

        self.graph = self.build_graph()

    def add(self, a: int, b: int) -> int:
        """Adds a and b.

        Args:
            a: first int
            b: second int
        """
        return a + b

    def multiply(self, a: int, b: int) -> int:
        """Multiply a and b.

        Args:
            a: first int
            b: second int
        """
        return a * b

    def divide(self, a: int, b: int) -> float:
        """Divide a and b.

        Args:
            a: first int
            b: second int
        """
        return a / b

    def create_content_stream(self, content: str, chunk_size: int = 3) -> Generator[str, None, None]:
        words = content.split()
        current_chunk = []
        current_size = 0

        for word in words:
            if current_size + len(word) + (1 if current_chunk else 0) > chunk_size and current_chunk:
                yield ' '.join(current_chunk)
                time.sleep(random.uniform(0.05, 0.2))  # Random delay to simulate typing
                current_chunk = []
                current_size = 0
            
            current_chunk.append(word)
            current_size += len(word) + (1 if current_chunk else 0)

        if current_chunk:
            yield ' '.join(current_chunk)
            time.sleep(random.uniform(0.05, 0.2))  # Random delay after the last chunk too


    def DuckDuckGoSearchRun(self) -> str:
        """
        Get the result from search on the internet using DuckDuckGo.

        Returns:
            str: The result of the search.
        """
        return "Madonna was born in 1958"
    
    def reasoner(self, state: MessagesState):
        return {"messages": [self.llm_with_tools.invoke([self.sys_msg] + state["messages"])]}

    def build_graph(self):
        builder = StateGraph(MessagesState)

        # Add nodes
        builder.add_node("reasoner", self.reasoner)
        builder.add_node("tools", ToolNode(self.tools))  # for the tools

        # Add edges
        builder.add_edge(START, "reasoner")
        builder.add_conditional_edges(
            "reasoner",
            # If the latest message (result) from node reasoner is a tool call -> tools_condition routes to tools
            # If the latest message (result) from node reasoner is a not a tool call -> tools_condition routes to END
            tools_condition,
        )
        builder.add_edge("tools", "reasoner")

        return builder.compile()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipeline logic.
        # Typically, you would retrieve relevant information from your knowledge base and synthesize it to generate a response.

        human_message = HumanMessage(content=user_message)
        messages = [human_message]
        messages = self.graph.invoke({"messages": messages})

        content = messages['messages'][-1].content
        
        # If content is already a string, return it as a stream
        if isinstance(content, str):
            return self.create_content_stream(content)
        # If content is already a Generator or Iterator, return it as is
        elif isinstance(content, (Generator, Iterator)):
            return content
        # If it's neither, convert to string and return as stream
        else:
            return self.create_content_stream(str(content))
