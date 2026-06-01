import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        # Allow overriding via environment
        env_model = os.getenv("DEFAULT_MODEL")
        if env_model and "gpt" not in env_model.lower() and "phi" not in env_model.lower():
            model_name = env_model
            
        super().__init__(model_name, api_key)
        
        # Configure API key
        api_key_to_use = self.api_key or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key_to_use)
        
        # Make model name robust
        self.resolved_model_name = model_name
        if not self.resolved_model_name.startswith("models/") and "/" not in self.resolved_model_name:
            self.resolved_model_name = f"models/{self.resolved_model_name}"
                
        try:
            self.model = genai.GenerativeModel(self.resolved_model_name)
        except Exception as e:
            # Fallback to standard 1.5 flash if name initialization fails
            fallback_model = "models/gemini-1.5-flash"
            print(f"⚠️ Warning: Failed to init Gemini model '{self.resolved_model_name}'. Falling back to '{fallback_model}'. Error: {e}")
            self.resolved_model_name = fallback_model
            self.model = genai.GenerativeModel(fallback_model)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Gemini, system instruction can be prepended or passed.
        # For maximum compatibility with old SDKs, we prepend it.
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System Instruction:\n{system_prompt}\n\nUser Question:\n{prompt}"

        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config={"stop_sequences": ["Observation:", "Observation 1:", "Observation 2:", "Observation 3:", "\nObservation"]}
            )
            content = response.text
        except Exception as e:
            # If standard call fails, try with models/gemini-1.5-flash
            if self.resolved_model_name != "models/gemini-1.5-flash":
                print(f"⚠️ Warning: Request failed with {self.resolved_model_name}. Retrying with models/gemini-1.5-flash...")
                self.resolved_model_name = "models/gemini-1.5-flash"
                self.model = genai.GenerativeModel(self.resolved_model_name)
                response = self.model.generate_content(
                    full_prompt,
                    generation_config={"stop_sequences": ["Observation:", "Observation 1:", "Observation 2:", "Observation 3:", "\nObservation"]}
                )
                content = response.text
            else:
                raise e

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Gemini usage data safely parsed
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage["prompt_tokens"] = getattr(response.usage_metadata, "prompt_token_count", 0)
                usage["completion_tokens"] = getattr(response.usage_metadata, "candidates_token_count", 0)
                usage["total_tokens"] = getattr(response.usage_metadata, "total_token_count", 0)
        except Exception:
            pass

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System Instruction:\n{system_prompt}\n\nUser Question:\n{prompt}"

        try:
            response = self.model.generate_content(full_prompt, stream=True)
            for chunk in response:
                yield chunk.text
        except Exception:
            # Fallback streaming if model errors
            self.model = genai.GenerativeModel("models/gemini-1.5-flash")
            response = self.model.generate_content(full_prompt, stream=True)
            for chunk in response:
                yield chunk.text

