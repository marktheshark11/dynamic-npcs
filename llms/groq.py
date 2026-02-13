from groq import Groq
from dotenv import load_dotenv
import os
from typing import Any

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def chat(
    message: str | None = None,
    model: str = "llama-3.3-70b-versatile",
    messages: list[dict[str, str]] | None = None,
) -> str:
    """
    Send a message to the AI and get a response.
    
    Args:
        message: The message to send to the AI
        model: The model to use (default: llama-3.3-70b-versatile)
               Other options: mixtral-8x7b-32768, gemma2-9b-it
        messages: Optional chat messages array with role/content
    
    Returns:
        The AI's response as a string
    """
    if messages is None:
        if message is None:
            raise ValueError("Either 'message' or 'messages' must be provided")
        messages = [{"role": "user", "content": message}]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.7,
        max_tokens=1024,
    )
    return completion.choices[0].message.content or ""


if __name__ == "__main__":
    response = chat("What's 2+2?")
    print(response)
