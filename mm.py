import requests
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ollama_endpoint(prompt: str, model_name: str = "deepseek-r1:1.5b", api_url: str = "http://localhost:11434/api/generate", output_file: str = "ollama_responses.json") -> None:
    """
    Test the Ollama API endpoint with a given prompt and save full articles as Paragraph to JSON.
    """
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        response = requests.post(api_url, json=payload, timeout=70)
        response.raise_for_status() 
        result = response.json()

        logger.info(f"Ollama API call successful. Result: {result}")

        # Save the full articles as Paragraph to a JSON file
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                json.dump({"Paragraph": result}, f, ensure_ascii=False)
                f.write('\n')
            logger.info(f"Full article saved as Paragraph to {output_file}")
        except Exception as e:
            logger.error(f"Error saving response to file: {e}")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error during request to Ollama: {e} - Response: {e.response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during request to Ollama: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    input_file = "ci/cq_mini.json"
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        exit()
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {input_file}")
        exit()
    
    for item in data:
        text_content = item.get("content", "")
        
        test_prompt = f"""
        I have a text that may contain multiple paragraphs related to the same context or interview. 
        Please separate the content into meaningful paragraphs that relate to the same context or interview.
        
        Example:
        Input:
        Paragraph 1: This is the first paragraph about topic A.
        Paragraph 2: This is the second paragraph about topic A.
        Paragraph 3: This is the first paragraph about topic B.
        Output:
        Paragraph 1: This is the first paragraph about topic A.
        Paragraph 2: This is the second paragraph about topic A.
        ---
        Paragraph 3: This is the first paragraph about topic B.
        
        Now, process the following text:
        {text_content}
        """
        
        test_ollama_endpoint(test_prompt)
        print("Ollama endpoint test complete. Check the logs for the result.")