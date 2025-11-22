
import os
from abc import ABC, abstractmethod

from PIL import Image
import google.generativeai as genai

gemini_api_key = os.environ.get("GEMINI_API_KEY")


class Conversation(ABC):
    @abstractmethod
    def __init__(self, user_prompt, system_prompt=None):
        pass

    @abstractmethod
    def add_message(self, message):
        pass


class GeminiConversation(Conversation):
    def __init__(self, user_prompt, system_prompt=None):
        self.messages = []
        if system_prompt is not None:
            self.messages.append({"role": "user", "parts": system_prompt})
            self.messages.append({"role": "model", "parts": "Understood."})

        first_message = {"role": "user", "parts": user_prompt}
        self.messages.append(first_message)

    def add_message(self, message):
        assert isinstance(message["parts"], list), "Message must be in Gemini format"
        self.messages.append(message)


class Model(ABC):
    def __init__(self, model_name):
        self.model_name = model_name

    @abstractmethod
    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        pass

    def count_tokens(self, system_prompt, user_prompt, assistant_response, image_paths=None):
        pass

def create_model(model_name):
    supported = {"gemini-2.0-flash", "gemini-flash-latest"}
    if model_name not in supported:
        raise NotImplementedError("This build only supports Gemini Flash models.")

    actual_model = "gemini-2.0-flash"
    return GeminiModel(actual_model)


api_name_to_colloquial = {
    "gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini-flash-latest": "Gemini Flash",
}


class GeminiModel(Model):
    def __init__(self, model_name="gemini-2.0-flash"):
        if not gemini_api_key:
            raise EnvironmentError("Set GEMINI_API_KEY before starting Aura.")

        genai.configure(api_key=gemini_api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name)
        self.convo = None

    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        parts = [user_prompt]
        if image_paths:
            for path in image_paths:
                with Image.open(path) as img:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    parts.append(img.copy())

        self.convo = GeminiConversation(user_prompt=parts, system_prompt=system_prompt)
        response = self.model.generate_content(self.convo.messages)
        return response.text

    def count_tokens(self, system_prompt, user_prompt, assistant_response, image_paths=None):
        system_token_count = self.model.count_tokens(system_prompt).total_tokens
        user_token_count = self.model.count_tokens(user_prompt).total_tokens
        image_token_count = 0

        if image_paths:
            for image_path in image_paths:
                image_token_count += self.model.count_tokens(image_path).total_tokens

        total_input_tokens = system_token_count + user_token_count + image_token_count
        assistant_token_count = self.model.count_tokens(assistant_response).total_tokens

        output_dict = {
            "system_tokens": system_token_count,
            "user_tokens": user_token_count,
            "image_tokens": image_token_count,
            "total_input_tokens": total_input_tokens,
            "input_cost": 0,
            "output_tokens": assistant_token_count,
            "output_cost": 0,
            "total_cost": 0,
        }

        return output_dict