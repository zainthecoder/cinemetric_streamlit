"""
Groq API integration for LLM-based conversation evaluation
"""
import os
import requests
import json
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_ID = "llama-3.1-8b-instant"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def evaluate_conversation(
    prompt_template: str,
    metric: str,
    conversation: str,
    persona_context: str = None,
    previous_turn_context: str = None
) -> dict:
    """
    Evaluate a conversation using the Groq API
    
    Args:
        prompt_template: The persona's prompt template with {{METRIC}} and {{CONVERSATION}} placeholders
        metric: The evaluation metric (e.g., "empathy", "clarity")
        conversation: The conversation text to evaluate
        persona_context: Optional additional context about the persona
        previous_turn_context: Optional context from previous turns
        
    Returns:
        dict: {"score": int (0-10), "explanation": str}
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    
    # Build the enhanced prompt
    enhanced_prompt = prompt_template
    
    if persona_context:
        enhanced_prompt += f"\n\nPersona Profile: {persona_context}"
    
    if previous_turn_context:
        enhanced_prompt += f"\n\nPrevious Context: {previous_turn_context}"
    
    # Replace placeholders
    filled_prompt = enhanced_prompt.replace("{{METRIC}}", metric).replace("{{CONVERSATION}}", conversation)
    
    # System prompt for structured output
    system_prompt = (
        "You are an expert conversation evaluator with a deep understanding of human interactions and communication patterns. "
        "You will be taking on the persona specified in the prompt to evaluate conversations based on specific metrics. "
        "Analyze the conversation through the lens of this persona and the requested metric. "
        'IMPORTANT: Respond with ONLY a valid JSON object in this exact format: { "score": number, "explanation": string }. '
        "The score must be a number from 0 to 10, where 0 is extremely low and 10 is extremely high for the metric. "
        "The explanation should be detailed and provide specific examples from the conversation that justify your scoring. "
        "Stay true to the persona's unique perspective throughout your evaluation. "
        "Do not include any additional text, preamble, or commentary before or after the JSON object."
    )
    
    # Prepare API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": filled_prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    # Make API call
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        response_text = data["choices"][0]["message"]["content"].strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            raise ValueError("No JSON object found in response")
        
        result = json.loads(json_match.group(0))
        
        # Validate result
        if "score" not in result or "explanation" not in result:
            raise ValueError("Response missing required fields")
        
        # Normalize score to 0-10 range
        score = max(0, min(10, int(result["score"])))
        
        return {
            "score": score,
            "explanation": result["explanation"]
        }
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Groq API request failed: {str(e)}")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise Exception(f"Failed to parse Groq API response: {str(e)}")