import os
import re
import time
import random
import json
from pathlib import Path
from google import genai
from google.genai import types, errors

# -----------------------------
# Configuration
# -----------------------------
INPUT_FILE = "source.txt"
OUTPUT_FILE = "articles.json"
MODEL_NAME = "gemini-2.5-flash"
CHUNK_SIZE = 1000  # characters per chunk
OVERLAP = 500      # overlap between chunks

MAX_RETRIES = 8
BASE_DELAY = 2  # seconds

# Initialize Gemini client
client = genai.Client(api_key="AIzaSyAV5hOBpd4xnkE3kvy14r8OwIt1pjsufeQ")


GEMINI_PROMPT = """
You are an expert archival-article parser. Transform the following
unstructured dance-journal text into a clean JSON list of article objects.

### OUTPUT FORMAT (strict JSON)
Return ONLY a JSON array. Each article must follow *this exact structure*:

{{
  "Title": "TITLE IN FULL CAPS OR ORIGINAL FORM",
  "Authors": ["Author One", "Author Two"],
  "Abstract": "1–3 sentence abstract summarizing the article.",
  "Text": "The full article text exactly as it appears, preserving line breaks."
}}

### EXTRACTION RULES

1. **Title**
   - A title is usually uppercase or title-case.
   - Should not include page numbers unless part of the actual title.
   - Preserve the title as written.

2. **Authors**
   - Authors typically appear on the same line or right below the title.
   - Split multiple authors into a list.
   - Remove editorial notes like “interviews”, “with hieroglyphs by…”, etc.

3. **Abstract**
   - Create a concise 1–3 sentence summary of the article.
   - If an article has no body text or not enough context, return "".

4. **Text**
   - Include the full article body until the next title or section break.
   - Preserve punctuation and line breaks.
   - Do NOT invent or modify the text.

5. **Ignore ALL content that is not part of an article’s meaningful text.**
   This includes (but is not limited to):
     - Table of contents
     - Page numbers or pagination artifacts
     - Issue/volume numbers, publication metadata
     - Copyright, ISBN, editorial credits
     - Advertisements, images, captions, figure labels
     - Section dividers, headers, footers
     - Website URLs, emails
     - Marginal notes or repeated running headers/footers
     - Anything decorative or unrelated to the article body
   Keep ONLY the actual article content: title, authors, main text.

6. **If no complete article is found in this chunk, return an empty array.**

### IMPORTANT
- Return VALID JSON ONLY.
- Do NOT include explanations, comments, or markdown.
- Do NOT hallucinate missing text.

### INPUT TEXT:
{text}
"""

# -----------------------------
# Helper Functions
# -----------------------------
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

def call_gemini(chunk: str) -> dict:
    
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
                    max_output_tokens=2000,
                    temperature=0.0
                )
            )
            # Check if response has valid content
            if not response or not hasattr(response, 'text') or not response.text:
                print(f"[Attempt {attempt}] Invalid response from API")
                wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
                time.sleep(wait_time)
                continue
            
            # Debug: Print model output
            print(f"\n--- Model Output (Attempt {attempt}) ---")
            print(response.text)
            print("--- End Model Output ---\n")
            
            # Assume response.text is JSON string
            parsed = json.loads(response.text)
            
            # Check if we got articles
            if isinstance(parsed, list) and len(parsed) == 0:
                print(f"⚠️  Model returned empty array - no articles found in this chunk")
            elif isinstance(parsed, list):
                print(f"✓ Found {len(parsed)} article(s) in this chunk")
            
            return parsed

        except (errors.ServerError) as e:
            wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
            print(f"[Attempt {attempt}] Gemini busy ({e}), retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
        except json.JSONDecodeError as e:
            print(f"[Attempt {attempt}] JSON decode error, skipping chunk: {e}")
            return None
        except Exception as e:
            print(f"[Attempt {attempt}] Other error: {e}")
            time.sleep(BASE_DELAY)
    print("Max retries reached, skipping this chunk.")
    return None

def append_article(article: dict):
    """Append a single article to the JSON file (checkpointing)."""
    if article is None:
        return
    # Ensure output file exists
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(OUTPUT_FILE, "r+", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
        data.append(article)
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.truncate()

# -----------------------------
# Main Extraction
# -----------------------------
def main():
    if not Path(INPUT_FILE).exists():
        print(f"Input file {INPUT_FILE} not found.")
        return

    text = Path(INPUT_FILE).read_text(encoding="utf-8")
    chunks = chunk_text(text)
    print(f"Total chunks: {len(chunks)}")

    for idx, chunk in enumerate(chunks, 1):
        print(f"\n{'='*60}")
        print(f"Processing chunk {idx}/{len(chunks)} (chars {(idx-1)*CHUNK_SIZE} to {idx*CHUNK_SIZE})")
        print(f"{'='*60}")
        
        result = call_gemini(chunk)
        if result and isinstance(result, list) and len(result) > 0:
            for article in result:
                append_article(article)
            print(f"✓ Saved {len(result)} article(s) from chunk {idx}")
        else:
            print(f"⊘ No articles to save from chunk {idx}")
        
        # Longer pause to reduce API load
        time.sleep(1.5 + random.uniform(0, 2.0))

if __name__ == "__main__":
    main()
