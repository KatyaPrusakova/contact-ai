import json
import re
import time
import random
from pathlib import Path
from google import genai
from google.genai import types, errors

# Configuration
INPUT_FILE = "source.txt"
OUTPUT_FILE = "parsed_articles_new.json"
MODEL_NAME = "gemini-2.0-flash-exp"
CHUNK_SIZE = 25000  # Reduced to ensure output fits within token limits
OVERLAP = 1000      # Overlap to catch articles split across chunks

MAX_RETRIES = 8
BASE_DELAY = 3

# Initialize Gemini client
client = genai.Client(api_key="AIzaSyAV5hOBpd4xnkE3kvy14r8OwIt1pjsufeQ")

GEMINI_PROMPT = """
You are an expert archival-article parser. Extract ALL complete articles from the following dance journal text.

### OUTPUT FORMAT (strict JSON)
Return ONLY a JSON array. Each article must follow this exact structure:

{{
  "Title": "TITLE IN FULL CAPS OR ORIGINAL FORM",
  "Authors": ["Author One", "Author Two"],
  "Abstract": "1–3 sentence abstract summarizing the article.",
  "Text": "The full article text exactly as it appears, preserving line breaks."
}}

### EXTRACTION RULES

1. **Title**
   - Usually appears in uppercase, title-case, or as a distinctive heading
   - May be followed by page numbers (ignore page numbers)
   - Preserve the title as written

2. **Authors**
   - Usually appear right after the title
   - May be prefixed with "by", "interview with", etc.
   - Split multiple authors into a list
   - Remove editorial notes like "interviews", "with hieroglyphs by…", etc.

3. **Abstract**
   - Create a concise 1–3 sentence summary of what the article is about
   - If the article is very short or unclear, provide best effort summary

4. **Text**
   - Include the FULL article body from start to finish
   - Preserve all punctuation and line breaks exactly as they appear
   - Stop at the next article title or volume marker
   - Do NOT invent or modify the text

5. **Ignore these items** (they are NOT articles):
   - Table of contents listings
   - Page numbers, volume numbers, issue numbers
   - Publication metadata, copyright notices, ISBN
   - Editorial credits, masthead information
   - Section dividers, headers, footers
   - Advertisements, URLs, repeated running headers

6. **Important**: Extract EVERY complete article you find. Do not skip articles.

### IMPORTANT
- Return VALID JSON ONLY
- Do NOT include explanations, comments, or markdown wrappers
- Do NOT hallucinate missing text
- If no complete articles found, return empty array: []

### INPUT TEXT:
{text}
"""

def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        start += size - overlap
    return chunks

def call_gemini(chunk: str, chunk_num: int, total: int) -> list:
    """Call Gemini to extract articles from a chunk."""
    prompt_text = GEMINI_PROMPT.format(text=chunk)
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt_text)]
                    )
                ],
                config=types.GenerateContentConfig(
                    max_output_tokens=32000,
                    temperature=0.0
                )
            )
            
            # Check if response has valid content
            if not response or not hasattr(response, 'text') or not response.text:
                print(f"  [Attempt {attempt}] Invalid response from API")
                wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
                time.sleep(wait_time)
                continue
            
            # Save raw response to file
            response_file = f"response_chunk_{chunk_num:03d}.txt"
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"  💾 Saved raw response to {response_file}")
            
            # Parse JSON response (remove markdown wrappers if present)
            text = response.text.strip()
            
            # Remove markdown code blocks
            if text.startswith('```json'):
                text = text[7:]  # Remove ```json
            elif text.startswith('```'):
                text = text[3:]   # Remove ```
            
            if text.endswith('```'):
                text = text[:-3]  # Remove trailing ```
            
            text = text.strip()
            
            parsed = json.loads(text)
            
            # Validate it's a list
            if isinstance(parsed, list):
                print(f"  ✓ Chunk {chunk_num}/{total}: Found {len(parsed)} article(s)")
                return parsed
            else:
                print(f"  ⚠️  Chunk {chunk_num}/{total}: Unexpected response format")
                return []
        
        except errors.ServerError as e:
            wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
            print(f"  [Attempt {attempt}] API busy, retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
        except json.JSONDecodeError as e:
            print(f"  [Attempt {attempt}] JSON decode error: {e}")
            print(f"  Response length: {len(response.text)} chars")
            print(f"  Response preview: {response.text[:200]}...")
            print(f"  Response end: ...{response.text[-200:]}")
            # Retry with smaller chunk or different approach
            if attempt < MAX_RETRIES:
                wait_time = BASE_DELAY
                time.sleep(wait_time)
                continue
            return []
        except Exception as e:
            print(f"  [Attempt {attempt}] Error: {e}")
            time.sleep(BASE_DELAY)
    
    print(f"  ✗ Max retries reached for chunk {chunk_num}")
    return []

def deduplicate_articles(articles):
    """Remove duplicate articles based on title similarity."""
    unique_articles = []
    seen_titles = set()
    
    for article in articles:
        title_key = article['Title'].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(article)
    
    return unique_articles

def extract_articles(text):
    """Extract articles from the source text using LLM."""
    print(f"Splitting text into chunks...")
    chunks = chunk_text(text)
    print(f"Total chunks: {len(chunks)}\n")
    
    all_articles = []
    
    for idx, chunk in enumerate(chunks, 1):
        print(f"Processing chunk {idx}/{len(chunks)}...")
        articles = call_gemini(chunk, idx, len(chunks))
        
        if articles:
            all_articles.extend(articles)
        
        # Pause between requests
        time.sleep(1.5 + random.uniform(0, 2.0))
    
    print(f"\nTotal articles extracted: {len(all_articles)}")
    
    # Deduplicate
    unique_articles = deduplicate_articles(all_articles)
    print(f"After deduplication: {len(unique_articles)} unique articles")
    
    return unique_articles



def main():
    print("="*70)
    print("Article Parser - Using Gemini LLM")
    print("="*70)
    print(f"\nReading {INPUT_FILE}...")
    
    if not Path(INPUT_FILE).exists():
        print(f"Error: {INPUT_FILE} not found!")
        return
    
    text = Path(INPUT_FILE).read_text(encoding="utf-8")
    print(f"File size: {len(text):,} characters\n")
    
    print("Extracting articles using LLM...\n")
    articles = extract_articles(text)
    
    if not articles:
        print("\n⚠️  No articles extracted!")
        return
    
    # Save to JSON
    print(f"\nSaving {len(articles)} articles to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Successfully saved to {OUTPUT_FILE}")
    
    # Print statistics
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    print(f"Total articles: {len(articles)}")
    
    # Count articles with authors
    with_authors = sum(1 for a in articles if a.get('Authors'))
    print(f"Articles with authors: {with_authors}")
    
    # Show first few articles
    print("\nFirst 3 articles:")
    for i, article in enumerate(articles[:3], 1):
        print(f"\n{i}. {article['Title']}")
        if article['Authors']:
            print(f"   By: {', '.join(article['Authors'])}")
        print(f"   Abstract: {article['Abstract'][:100]}...")

if __name__ == "__main__":
    main()
