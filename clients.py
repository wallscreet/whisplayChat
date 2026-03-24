from dataclasses import dataclass
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List
import os
from openai import OpenAI
from messages import MessageCache
from instructions import ModelInstructions


load_dotenv()


class LLMClient(ABC):
    """
    Abstract base class for all LLM clients. Defines the standard interface so different SDKs can be swapped out without changing the chat client code.
    """

    @abstractmethod
    def get_response(self, model: str, messages: List[dict], temp: float = 0.3, **kwargs) -> str:
        """
        Get a response from the model as plain text.
        """
        pass

    @abstractmethod
    def get_structured_response(self, model: str, response_format: type[BaseModel], content: str, **kwargs) -> BaseModel:
        """
        Get a structured/parsed response from the model.
        """
        pass

    @abstractmethod
    def get_response_with_tools(self, model: str, messages: List[dict], temp: float = 0.3, **kwargs) -> str:
        """
        Get a response with the tool pipeline included.
        """
        pass


@dataclass
class XAIClient(LLMClient):
    """
    ok TESTED
    """
    api_key: str = os.getenv("XAI_API_KEY")
    base_url: str = "https://api.x.ai/v1"

    def __post_init__(self):
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=3600,
        )
    
    def get_response(self, model: str, messages: list = None):
        """
        Get a response from an xAi model.
        """
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            print(f"Tokens Usage:\n{completion.usage}\n")
            return completion.choices[0].message.content

        except Exception as e:
            print(f"Error: {e}")
    
    def get_structured_response(self, model: str, response_format: type[BaseModel] = None, content: str = None) -> BaseModel:
        """
        Get a structured output response from the xAi api.
        """
        messages = [
            {
                "role": "system",
                "content": "Extract structured information from the content."
            },
            {
                "role": "user",
                "content": content
            }
        ]

        try:
            completion = self.client.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_format,
            )
            return completion.choices[0].message.parsed
        
        except Exception as e:
            print(f"Error: {e}")
    
    def get_response_with_tools(self, model: str, messages: list, tools: list = None):
        """
        Get a response from the xAi api with tools pipeline
        """
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
            )
            print(f"Tokens Usage:\n{completion.usage}\n")
            return completion.choices[0].message, completion.usage
        except Exception as e:
            print(f"Error: {e}")


@dataclass
class OllamaClient(LLMClient):
    """
    ok TESTED
    The ollama docs say I can use the openai sdk and use the v1 endpoint.
    """
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"

    def __post_init__(self):
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def get_response(self, model: str, messages: list = None):
        """
        Get a response from a local Ollama model.
        """
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            print(f"Tokens Usage:\n{completion.usage}\n")
            return completion.choices[0].message.content

        except Exception as e:
            print(f"Error: {e}")
    
    def get_structured_response(self, model: str, response_format: type[BaseModel] = None, content: str = None) -> BaseModel:
        """
        Get a structured output response from the local Ollama api.
        """
        messages = [
            {
                "role": "system",
                "content": "Extract structured information from the content."
            },
            {
                "role": "user",
                "content": content
            }
        ]

        try:
            completion = self.client.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_format,
            )
            return completion.choices[0].message.parsed
        
        except Exception as e:
            print(f"Error: {e}")
    
    def get_response_with_tools(self, model: str, messages: list, tools: list = None):
        """
        Get a response from a local Ollama model with tools pipeline
        """
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
            )
            print(f"Tokens Usage:\n{completion.usage}\n")
            return completion.choices[0].message, completion.usage
        except Exception as e:
            print(f"Error: {e}")


class IsoClient:
    def __init__(self, 
                 llm_client: LLMClient, 
                 instructions: ModelInstructions, 
                 cache_capacity: int=20
    ):
    
        self.llm_client = llm_client
        self.message_cache = MessageCache(capacity=cache_capacity)
        self.instuctions = instructions
        self._tools = []
    
    def generate_response(self, user_input: str, model: str="grok-4-1-fast-non-reasoning"):
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant named Juliet running on a portable device. Please keep your responses short and concise and do not use any emojis."
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
        #prompt = self.build_prompt(user_input=user_input)
        return self.llm_client.get_response(model=model, messages=messages)
    
    def register_tool(self, name: str, description: str, parameters: dict):
        """Register a new tool that the LLM can call."""
        tool_spec = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self._tools.append(tool_spec)

    def get_tools(self):
        return self._tools