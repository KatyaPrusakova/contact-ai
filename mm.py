import re
import json
import requests
import time
from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()


def extract_articles(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Splitting on uppercase lines (likely headlines) for demo
    article_blocks = re.split(r'\n\s*([A-Z][^\n]+)\n', text)
    articles = []

    for i in range(1, len(article_blocks), 2):
        title = article_blocks[i].strip()
        body = article_blocks[i + 1].strip()

        # Authors
        author_match = re.search(r'(?:By |Author[s]*: )([^\n]+)', body)
        authors = [author_match.group(1).strip()] if author_match else []

        # Abstract
        abstract_match = re.search(r'Abstract:([^\n]+)', body)
        if abstract_match:
            abstract = abstract_match.group(1).strip()
        else:
            abstract = '.'.join(body.split('.')[:2]).strip()

        articles.append({
            'Title': title,
            'Authors': authors,
            'Abstract': abstract,
            'Text': body
        })

    return articles

def get_disc_cat_ollama(article):
    prompt = f"""
Given the following article:
Title: {article['Title']}
Abstract: {article['Abstract']}
Body (excerpt): {article['Text'][:700]}

Identify:
1. The most relevant academic or artistic discipline(s) described in the article (up to 3).
2. The most relevant category/categories from this list if applicable ("Art & Performance", "Pedagogy & Facilitation", "Culture & Community", "Somatics & Body Awareness", "Philosophy", "Science & Research", "Education & Integration", "Psychology & Consciousness").

Respond ONLY with this JSON structure:
{{
  "Discipline": [list your disciplines, comma separated if multiple],
  "Category": [list your selected categories, comma separated if multiple]
}}
"""
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=120)
        result = response.json()
        text = result["response"]
        print(f"Ollama response: {text}")
        # Clean up and parse JSON response from the model
        json_response = re.search(r'{.*}', text, re.DOTALL)
        if json_response:
            return json.loads(json_response.group(0))
        else:
            # fallback in case LLM output format is unexpected
            return {"Discipline": [], "Category": []}
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {"Discipline": [], "Category": []}

def main():
    articles = extract_articles('source.txt')
    print(f"Total articles found: {len(articles)}")

    for idx, article in enumerate(articles):
        print(f"Processing article {idx+1}/{len(articles)}: {article['Title']}")
        # Call LLM for both category and discipline
        info = get_disc_cat_ollama(article)
        article['Discipline'] = info.get("Discipline", [])
        article['Category'] = info.get("Category", [])
        # Optional: Add a tiny delay for server stability
        time.sleep(1)
    
    with open('articles_database.json', 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"Finished! Saved to articles_database.json")

if __name__ == '__main__':
    main()
