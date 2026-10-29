"""
Local LLM Engine for Parakeet AI Prototype.
Communicates with local Ollama runtime to provide real-time token streaming.
Supports both direct-response models and reasoning models (thinking tokens).
"""

import threading
from typing import List, Generator, Optional, Tuple
import ollama


class LLMEngine:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.client = ollama.Client(host=self.host)

    def is_available(self) -> bool:
        """Checks if the local Ollama server is running and reachable."""
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """Returns a prioritized list of installed Ollama model names."""
        try:
            response = self.client.list()
            model_names = []
            models_list = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
            for m in models_list:
                name = m.get("name") if isinstance(m, dict) else getattr(m, "model", getattr(m, "name", None))
                if name:
                    model_names.append(name)

            # Sort models: prioritize fast direct models (llama, mistral) first
            def priority_key(name: str):
                nl = name.lower()
                if "llama3.2" in nl or "llama-3.2" in nl:
                    return 0
                if "llama" in nl:
                    return 1
                if "qwen3.5:4b" in nl:
                    return 2
                if "qwen" in nl:
                    return 3
                return 4

            model_names.sort(key=priority_key)
            return model_names
        except Exception:
            return []

    def stream_answer(
        self,
        question: str,
        model: str,
        system_prompt: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        num_ctx: int = 2048,
    ) -> Generator[Tuple[str, str], None, None]:
        """
        Streams answer tokens from local Ollama for the given question.
        Yields tuples of (token_type, token_text), where token_type is:
          - 'content': standard response token
          - 'thinking': internal reasoning token (for thinking models)
        """
        if not system_prompt:
            system_prompt = (
                "You are Symposium AI, an intelligent real-time voice copilot for meetings, interviews, "
                "and technical discussions. Provide direct, concise, articulate, and well-structured answers "
                "to the user's question. Get straight to the point."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        try:
            stream = self.client.chat(
                model=model,
                messages=messages,
                stream=True,
                options={"num_ctx": num_ctx, "temperature": 0.7},
            )

            for chunk in stream:
                if stop_event is not None and stop_event.is_set():
                    break

                msg = getattr(chunk, "message", None)
                if msg is None and isinstance(chunk, dict):
                    msg = chunk.get("message", {})

                # Extract content
                content = (
                    msg.get("content", "")
                    if isinstance(msg, dict)
                    else getattr(msg, "content", "")
                )
                if content:
                    yield ("content", content)

                # Extract thinking tokens if model is a reasoning model
                thinking = (
                    msg.get("thinking", "")
                    if isinstance(msg, dict)
                    else getattr(msg, "thinking", "")
                )
                if thinking:
                    yield ("thinking", thinking)

        except Exception as e:
            yield ("content", f"\n[Error communicating with local Ollama: {e}]")


if __name__ == "__main__":
    print("Testing LLMEngine...")
    engine = LLMEngine()
    models = engine.get_available_models()
    print("Sorted models:", models)
    if models:
        top_model = models[0]
        print(f"Top model: {top_model}")
        for kind, text in engine.stream_answer("What is 1+1? Answer in one word.", model=top_model):
            print(f"[{kind}] {text}", end="", flush=True)
        print("\nTest finished!")
