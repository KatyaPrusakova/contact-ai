import json
import re
import os
import logging
import time
from typing import List, Dict, Any
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the semantic categories and their keywords
CATEGORY_KEYWORDS = {
    "Art & Performance": ["improvisation", "jam", "festival", "stage", "choreography", "creative", "artistic", "poem"],
    "Somatics & Body Awareness": ["somatic", "BMI", "body", "awareness", "movement", "sensation", "perception"],
    "Psychology & Consciousness": ["emotion", "trauma", "healing", "consciousness", "psychology", "integration"],
    "Pedagogy & Facilitation": ["lesson", "teaching", "facilitation", "pedagogy", "group", "instructor", "student", "practice"],
    "Philosophy": ["ethics", "philosophy", "presence"],
    "Culture & Community": ["community", "culture", "diversity","global", "local", "inclusion"],
    "Science & Research": ["research", "anatomy", "analysis", "biomechanics", "data", "study", "academic"]
}

class TextProcessor:
    def __init__(self, model_name="deepseek-r1:1.5b"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"
        self.error_responses = []

    def check_ollama_available(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get("http://localhost:11434/api/tags")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def is_same_article(self, text1: str, text2: str) -> bool:
        """
        Use LLM to determine if two text segments belong to the same article.
        """
        if not self.check_ollama_available():
            logger.error("Ollama service is not running. Please start it with 'ollama serve'")
            return True  # Default to True if Ollama is unavailable

        prompt = f"""
        You are an expert article analyzer. Determine if the two given text segments belong to the same article or interview.
        Consider the context, style, and content of the text and authors.
        Respond with 'yes' if they are part of the same article, and 'no' if they are not.
        
        Text Segment 1:
        {text1[-500:] if len(text1) > 500 else text1}
        
        Text Segment 2:
        {text2[:500] if len(text2) > 500 else text2}
        
        Answer: (yes or no)
        """
        logger.info(f"Sending prompt to Ollama: {prompt}...")  # Print the first 100 characters for debugging
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "text"
            }

            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            result = response.text.strip().lower()

            return "yes" in result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during request to Ollama: {e}")
            return True  # Default to True in case of an error
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during request to Ollama: {e}")
            return True  # Default to True in case of an error
        except Exception as e:
            logger.error(f"Unexpected error using LLM: {e}")
            return True  # Default to True in case of an error

def separate_articles(text: str, processor: TextProcessor) -> List[str]:
    """
    Separate a text into distinct articles using LLM to understand context.
    """

    articles = []
    current_article = ""
    sentences = re.split(r'(?<=[.!?]) +', text)  # Split by sentence-ending punctuation
    sentences = [s.strip() for s in sentences if s.strip()]  # Remove empty strings
    logger.info(f"Separating {len(sentences)} sentences into articles...")
    
    for sentence in sentences:
        # print(f"Processing sentence: {sentence[:50]}...")  # Print the first 50 characters for debugging
        if not current_article:
            current_article = sentence
        else:
            if processor.is_same_article(current_article, sentence):
                current_article += " " + sentence
            else:
                articles.append(current_article)
                current_article = sentence

    if current_article:
        articles.append(current_article)
    # print(f"Separated into {len(articles)} articles.")
    return articles

def assign_categories(text: str) -> List[str]:
    """Assign one or two relevant categories based on keyword matching."""
    text_lower = text.lower()
    scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = 0
        for keyword in keywords:
            matches = len(re.findall(r'\b' + keyword + r'\b', text_lower))
            scores[category] += matches
    
    # Get the top 2 categories
    top_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    relevant_categories = [cat for cat, score in top_categories[:2] if score > 0]
    
    return relevant_categories

def process_articles(input_path: str, output_path: str, error_path: str) -> None:
    """
    Process JSON object, separate text into articles, assign categories,
    and save progress and errors.
    """
    processed_articles = []
    error_list = []
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_path}")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {input_path}")
        return
    
    total_articles = len(data)
    start_time = time.time()
    
    processor = TextProcessor()
    if not processor.check_ollama_available():
        logger.error("Ollama service is not running. Please start it with 'ollama serve'")
        return
    
    for i, item in enumerate(data):
        try:
            content = item.get("content", "")
            if not content:
                logger.warning(f"Article {i+1} has no content. Skipping.")
                continue
            
            # Separate the content into distinct articles
            articles = separate_articles(content, processor)
            
            for j, article_text in enumerate(articles):
                # Assign categories to the article
                categories = assign_categories(article_text)
                
                # Create a new article object
                new_article = {
                    "article_id": f"{item.get('id', 'article')}_{j+1}",
                    "content": article_text,
                    "categories": categories,
                    "source_article_id": item.get("id", "unknown"),
                    "source_metadata": item.get("metadata", {})
                }
                
                processed_articles.append(new_article)
                logger.info(f"Processed article {len(processed_articles)}/{total_articles} chunks")
            
        except Exception as e:
            error_info = {
                "article_index": i,
                "article_id": item.get("id", "unknown"),
                "error": str(e)
            }
            error_list.append(error_info)
            logger.error(f"Error processing article {i+1}: {e}")
        
        # Save progress every 10 articles
        if (i + 1) % 10 == 0:
            save_progress(processed_articles, output_path)
            logger.info(f"Saved progress after processing {i+1} articles.")
    
    # Save final results and errors
    save_progress(processed_articles, output_path)
    save_errors(error_list, error_path)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Finished processing {len(processed_articles)} articles in {elapsed_time:.2f} seconds.")

def save_progress(articles: List[Dict[str, Any]], output_path: str) -> None:
    """Save processed articles to a JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(articles)} articles to {output_path}")
    except Exception as e:
        logger.error(f"Error saving articles: {e}")

def save_errors(errors: List[Dict[str, Any]], error_path: str) -> None:
    """Save processing errors to a JSON file."""
    try:
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(errors)} errors to {error_path}")
    except Exception as e:
        logger.error(f"Error saving errors: {e}")

if __name__ == "__main__":
    input_file = "ci/cq_mini.json"
    output_file = "ci/processed_articles.json"
    error_file = "processing_errors.json"
    
    process_articles(input_file, output_file, error_file)
    print("Processing complete.")
