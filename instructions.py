from dataclasses import dataclass


@dataclass
class ModelInstructions:
    name: str = None
    description: str = None
    llm_model: str = None