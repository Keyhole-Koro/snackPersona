import os
from openai import OpenAI
from openai.types.chat import ChatCompletion

class BedrockMantleClient:
    """
    A client for interacting with Amazon Bedrock using its OpenAI-compatible
    (Mantle) API endpoints. This is the recommended scalable path.
    """
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initializes the Mantle client.
        Credentials can be passed directly or read from environment variables.
        
        :param api_key: The Bedrock API key. Defaults to os.environ["OPENAI_API_KEY"].
        :param base_url: The Bedrock regional endpoint. Defaults to os.environ["OPENAI_BASE_URL"].
        """
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        base_url = base_url or os.environ.get("OPENAI_BASE_URL")

        if not api_key or not base_url:
            raise ValueError(
                "API key and base URL must be provided either as arguments "
                "or as OPENAI_API_KEY and OPENAI_BASE_URL environment variables."
            )

        try:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            print("Bedrock Mantle client initialized successfully.")
        except Exception as e:
            print(f"Error initializing OpenAI client for Bedrock: {e}")
            self.client = None

    def list_models(self) -> list:
        """Lists the model IDs available to the account/region."""
        if not self.client:
            print("Error: Client not initialized.")
            return []
        
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def create_chat_completion(self, model_id: str, messages: list, temperature: float = 0.8) -> ChatCompletion:
        """
        Calls the chat completions endpoint with a specific model.

        :param model_id: The ID of the model to use.
        :param messages: A list of message dictionaries (e.g., [{"role": "user", "content": "..."}]).
        :param temperature: The sampling temperature.
        :return: The ChatCompletion object from the OpenAI library.
        """
        if not self.client:
            print("Error: Client not initialized.")
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
            )
            return response
        except Exception as e:
            print(f"Error creating chat completion: {e}")
            return None

if __name__ == '__main__':
    # This is an example of how to use the client.
    # To run this, you MUST set the following environment variables:
    # export OPENAI_API_KEY="<YOUR_BEDROCK_API_KEY>"
    # export OPENAI_BASE_URL="https://bedrock-mantle.us-east-1.api.aws/v1" # Or your region
    
    print("--- Client Example ---")
    
    # We expect this to fail if env vars are not set.
    try:
        mantle_client = BedrockMantleClient()

        if mantle_client.client:
            # 1. List available models
            available_models = mantle_client.list_models()
            print("\nAvailable models (first 10):", available_models[:10])

            if available_models:
                # 2. Select a model and prepare messages
                # NOTE: You must have access to the model you choose.
                model_to_use = next((m for m in available_models if "anthropic.claude-3-sonnet" in m), None)
                if not model_to_use:
                    model_to_use = available_models[0] # Fallback to first model

                print(f"\nUsing model: {model_to_use}")
                
                messages_to_send = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Write a short, optimistic sentence about the future of AI."}
                ]
                
                # 3. Get a chat completion
                completion = mantle_client.create_chat_completion(
                    model_id=model_to_use,
                    messages=messages_to_send
                )

                # 4. Print the result
                if completion and completion.choices:
                    print("\nResponse:")
                    print(completion.choices[0].message.content)
                else:
                    print("\nFailed to get a valid completion.")
            else:
                print("\nNo models available.")

    except ValueError as e:
        print(f"\nClient initialization failed as expected (env vars likely not set): {e}")

    print("\n--- End of Example ---")
