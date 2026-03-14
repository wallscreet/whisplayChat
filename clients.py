from dataclasses import dataclass
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List
import os
from openai import OpenAI


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