import json
import re
import time
import random
from google import genai
from google.genai import types, errors

# Configuration
INPUT_FILE = "source20.json"
OUTPUT_FILE = "source20_enriched.json"
MODEL_NAME = "gemini-2.0-flash-exp"

MAX_RETRIES = 5
BASE_DELAY = 2

# Initialize Gemini client
client = genai.Client(api_key="AIzaSyAV5hOBpd4xnkE3kvy14r8OwIt1pjsufeQ")

CATEGORY_KEYWORDS = {
    "Art & Performance": ["improvisation", "jam", "festival", "stage", "choreography", "creative", "artistic", "poem", "performance", "dance", "music"],
    "Somatics & Body Awareness": ["somatic", "body", "awareness", "movement", "sensation", "perception", "physical", "embodiment", "kinesthetic"],
    "Psychology": ["emotion", "trauma", "healing", "consciousness", "psychology", "integration", "mental", "mind"],
    "Pedagogy & Facilitation": ["lesson", "teaching", "facilitation", "pedagogy", "group", "instructor", "student", "practice", "workshop", "class"],
    "Culture & Community": ["community", "culture", "diversity", "global", "local", "inclusion", "society", "social"],
    "Science & Research": ["research", "anatomy", "analysis", "biomechanics", "data", "study", "academic", "scientific", "theory"]
}

ENRICHMENT_PROMPT = """
Analyze this dance/movement article and provide:

1. **Category**: Choose ONE most relevant category from this list:
   - Psychology (healing, emotion, trauma)
   - Community (society , social, culture)
   - Somatics & Body Awareness (sensation, perception, embodiment)
   - Research (study scientific, theory)
   - Pedagogy & Facilitation (teaching, workshop, class, practice)
   - Art (creative, artistic, poem, performance)

2. **Abstract**: Write a clear 2-4 sentence summary of the main content and themes.

3. **Tags**: List maximum 5 popular topics that people would easily understand and search for. 
   - Use Title Case (Capitalize Each Word)
   - Choose well-known, general topics (e.g., "Pedagogy", "Workshop Structure", "Therapy", "Movement Technique")
   - DO NOT use "Contact Improvisation" as all articles are already about this topic
   - Make them intuitive and searchable

Article Title: {title}
Authors: {authors}

Article Content:
{content}

Return ONLY valid JSON in this exact format:
{{
  "Category": "chosen category name",
  "Abstract": "your 2-4 sentence summary",
  "Tags": ["Tag One", "Tag Two", "Tag Three", "Tag Four", "Tag Five"]
}}
"""

def call_gemini_for_enrichment(article):
    """Call Gemini to generate Category, Abstract, and Tags for an article."""
    title = article.get('Title', 'Untitled')
    authors = ', '.join(article.get('Authors', [])) if article.get('Authors') else 'Unknown'
    content = article.get('Content', '')
    
    # Limit content length for API
    content_preview = content[:4000] if len(content) > 4000 else content
    
    prompt_text = ENRICHMENT_PROMPT.format(
        title=title,
        authors=authors,
        content=content_preview
    )
    
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
                    max_output_tokens=1000,
                    temperature=0.3
                )
            )
            
            if not response or not hasattr(response, 'text') or not response.text:
                time.sleep(BASE_DELAY)
                continue
            
            # Parse response
            text_response = response.text.strip()
            
            # Remove markdown wrappers
            if text_response.startswith('```json'):
                text_response = text_response[7:]
            elif text_response.startswith('```'):
                text_response = text_response[3:]
            if text_response.endswith('```'):
                text_response = text_response[:-3]
            
            text_response = text_response.strip()
            
            result = json.loads(text_response)
            
            category = result.get('Category', '')
            abstract = result.get('Abstract', '')
            tags = result.get('Tags', [])
            
            return category, abstract, tags, None
        
        except Exception as e:
            error_str = str(e)
            # Check for quota exhaustion
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
                print(f"      ⚠ QUOTA EXHAUSTED: {error_str[:100]}")
                return None, None, None, "QUOTA_EXHAUSTED"
            elif 'ServerError' in str(type(e).__name__):
                wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"      Server error, retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                print(f"      [Attempt {attempt}] Error: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(BASE_DELAY)
                    continue
    
    # Fallback
    return "Art & Performance", "", [], None

def save_progress(enriched_articles, remaining_articles, filename="source_partial.json"):
    """Save current progress to a file."""
    print(f"\n{'='*70}")
    print(f"💾 SAVING PROGRESS...")
    print(f"{'='*70}")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(enriched_articles, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(enriched_articles)} enriched articles to {filename}")
    print(f"⏸ Remaining articles: {len(remaining_articles)}")

def enrich_articles():
    """Load source18.json, enrich each article with Gemini, and save."""
    print("="*70)
    print("Enriching source18.json with Category, Abstract, and Tags")
    print("="*70)
    
    # Load articles
    print(f"\nLoading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Found {len(articles)} articles\n")
    
    enriched_articles = []
    quota_exhausted = False
    
    for idx, article in enumerate(articles, 1):
        title = article.get('Title', 'Untitled')
        print(f"[{idx}/{len(articles)}] Processing: {title[:60]}...")
        
        # Call Gemini for enrichment
        category, abstract, tags, error = call_gemini_for_enrichment(article)
        
        # Check for quota exhaustion
        if error == "QUOTA_EXHAUSTED":
            print(f"\n{'='*70}")
            print("⚠ QUOTA EXHAUSTED - Saving progress and pausing...")
            print(f"{'='*70}")
            
            # Save current progress
            remaining = articles[idx-1:]  # Include current article in remaining
            save_progress(enriched_articles, remaining, "source_partial.json")
            
            print(f"\n💤 Sleeping for 60 seconds before resuming...")
            print(f"   You can also stop the script and resume later.")
            print(f"   Processed: {len(enriched_articles)}/{len(articles)} articles")
            
            quota_exhausted = True
            time.sleep(60)  # Sleep for 1 minute
            
            # Retry current article
            print(f"\n🔄 Resuming from article {idx}...")
            category, abstract, tags, error = call_gemini_for_enrichment(article)
            
            if error == "QUOTA_EXHAUSTED":
                print("❌ Still quota exhausted. Stopping script.")
                print(f"   Resume by processing remaining {len(remaining)} articles.")
                return enriched_articles, remaining
        
        # Update article
        enriched_article = {
            "Title": article.get('Title'),
            "Authors": article.get('Authors', []),
            "Abstract": abstract,
            "Content": article.get('Content'),
            "Tags": tags,
            "Category": category,
            "Volume": article.get('Volume'),
            "Years": article.get('Years')
        }
        
        enriched_articles.append(enriched_article)
        
        print(f"  ✓ Category: {category}")
        print(f"  ✓ Tags: {len(tags)} tags")
        
        # Save progress periodically (every 5 articles)
        if idx % 5 == 0:
            save_progress(enriched_articles, articles[idx:], "source_partial.json")
        
        # Rate limiting
        time.sleep(1.5 + random.uniform(0, 0.5))
    
    # Save final results
    print(f"\n{'='*70}")
    print(f"Saving {len(enriched_articles)} enriched articles to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(enriched_articles, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Successfully saved to {OUTPUT_FILE}")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total articles enriched: {len(enriched_articles)}")
    
    # Show sample
    if enriched_articles:
        print(f"\nSample enriched article:")
        sample = enriched_articles[0]
        print(f"Title: {sample['Title']}")
        print(f"Category: {sample['Category']}")
        print(f"Abstract: {sample['Abstract'][:150]}...")
        print(f"Tags: {', '.join(sample['Tags'][:5])}...")
    
    return enriched_articles, []

def main():
    enrich_articles()

if __name__ == "__main__":
    main()
