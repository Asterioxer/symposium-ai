import threading
from typing import List, Generator, Optional, Tuple
import ollama


class LLMEngine:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.client = ollama.Client(host=self.host)

    def is_available(self) -> bool:
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        try:
            response = self.client.list()
            model_names = []
            models_list = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
            for m in models_list:
                name = m.get("name") if isinstance(m, dict) else getattr(m, "model", getattr(m, "name", None))
                if name:
                    model_names.append(name)

            # Sort lightweight instruction models first for faster response times
            def sort_key(name: str):
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

            model_names.sort(key=sort_key)
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
        if not system_prompt:
            system_prompt = (
                "You are an assistant for live meetings, interviews, and technical discussions. "
                "Provide direct, concise, and structured answers to the user's question."
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

                content = (
                    msg.get("content", "")
                    if isinstance(msg, dict)
                    else getattr(msg, "content", "")
                )
                if content:
                    yield ("content", content)

                thinking = (
                    msg.get("thinking", "")
                    if isinstance(msg, dict)
                    else getattr(msg, "thinking", "")
                )
                if thinking:
                    yield ("thinking", thinking)

        except Exception as e:
            yield ("content", f"\nError connecting to Ollama: {e}")


if __name__ == "__main__":
    engine = LLMEngine()
    models = engine.get_available_models()
    print("Available models:", models)
    if models:
        choice = models[0]
        print(f"Testing stream with {choice}...")
        for kind, token in engine.stream_answer("What is 2+2? Answer in one word.", model=choice):
            print(token, end="", flush=True)
        print()
