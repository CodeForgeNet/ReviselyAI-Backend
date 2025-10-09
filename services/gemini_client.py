import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)


async def get_gemini_response(prompt: str, max_tokens: int = 2048):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment variables.")

    model = genai.GenerativeModel('gemini-2.5-flash')

    full_prompt = f"Please provide a concise answer to the following question: {prompt}"

    try:
        response = await model.generate_content_async(full_prompt, generation_config={
            "max_output_tokens": max_tokens
        })

        if response.candidates and response.candidates[0].content.parts:
            generated_text = response.candidates[0].content.parts[0].text
            return generated_text
        else:

            finish_reason = response.candidates[0].finish_reason if response.candidates else None
            logger.warning(
                f"Gemini API did not return text content. Finish reason: {finish_reason}")
            return "I'm sorry, I couldn't generate a complete response. Please try again or rephrase your question."

    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise
