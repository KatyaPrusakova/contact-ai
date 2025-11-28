import json
import re
import time
import random
from pathlib import Path
from google import genai
from google.genai import types, errors

# Configuration
SOURCE_FILE = "source.txt"
TOC_FILE = "table_content.json"
OUTPUT_FILE = "matched_articles.json"
MODEL_NAME = "gemini-2.0-flash-exp"

MAX_RETRIES = 5
BASE_DELAY = 8

# Initialize Gemini client
client = genai.Client(api_key="AIzaSyAV5hOBpd4xnkE3kvy14r8OwIt1pjsufeQ")

EXTRACT_PROMPT = """
Given this article text from a dance journal, provide:
1. A concise 1-3 sentence abstract summarizing the main content
2. 5-8 relevant tags for search (topics, themes, techniques, names mentioned)

Return ONLY valid JSON in this exact format:
{{
  "abstract": "Your 1-3 sentence summary here.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Article text:
{text}
"""

FIND_ARTICLE_PROMPT = """
You are an expert at extracting articles from archival dance journal text with OCR artifacts and formatting variations.

YOUR TASK: Find and extract the article titled "{title}" by {authors} from the text below.

IMPORTANT MATCHING RULES:
1. The title MAY appear with variations:
   - Different capitalization (ALL CAPS, Title Case, or mixed)
   - Minor spelling differences or OCR errors
   - Extra spaces, punctuation, or line breaks
   - Abbreviations or shortened versions
   
2. Be FLEXIBLE in matching:
   - "Contact Improvisation" could be "CONTACT IMPROVISATION" or "Contact lmprovisation" (OCR error)
   - "Teacher's Notebook" could be "Teachers Notebook" or "TEACHER'S NOTEBOOK"
   - Partial title matches are acceptable if the context confirms it's the right article
   
3. Search through the ENTIRE text chunk systematically:
   - Don't stop at the first potential match
   - Look for author names near potential title matches to confirm
   - Page numbers (if provided) are hints but not absolute requirements
   
4. Extraction requirements:
   - Extract the COMPLETE article from start to end
   - EXCLUDE: title line, author line(s), page numbers, headers/footers
   - INCLUDE: All body text, preserving paragraphs and structure
   - STOP at: next article title, volume marker, or clear section break
   - CLEAN: Remove "CQ/CI Sourcebook", page numbers, repetitive headers

5. If multiple similar titles exist, choose the one matching the author name(s)

Return ONLY valid JSON:
{{
  "found": true,
  "article_text": "Complete cleaned article body text here",
  "confidence": "high/medium/low",
  "matched_title_form": "The exact form of the title as it appeared"
}}

If not found after thorough search, return:
{{
  "found": false,
  "article_text": "",
  "confidence": "none",
  "search_notes": "Brief note about what you searched for"
}}

TEXT TO SEARCH:
{text}
"""

def normalize_title(title):
    """Normalize title for matching."""
    # Remove special characters, convert to lowercase
    title = re.sub(r'[^\w\s]', '', title.lower())
    # Remove extra whitespace
    title = ' '.join(title.split())
    return title

def use_gemini_to_find_article(text_chunk, title, authors, page=None):
    """Use Gemini AI to intelligently find and extract article from text chunk."""
    authors_str = ', '.join(authors) if authors else 'Unknown'
    prompt_text = FIND_ARTICLE_PROMPT.format(
        title=title,
        authors=authors_str,
        text=text_chunk,
        page=page
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
                    max_output_tokens=12000,
                    temperature=0.1
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
            
            # Save raw Gemini output
            output_file = f"gemini_extract_{normalize_title(title)[:30]}_{attempt}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== EXTRACTION REQUEST ===\n")
                f.write(f"Title: {title}\n")
                f.write(f"Authors: {authors_str}\n")
                f.write(f"Attempt: {attempt}\n\n")
                f.write(f"=== RAW RESPONSE ===\n")
                f.write(response.text)
                f.write(f"\n\n=== CLEANED RESPONSE ===\n")
                f.write(text_response)
            
            result = json.loads(text_response)
            if result.get('found') and result.get('article_text'):
                confidence = result.get('confidence', 'unknown')
                matched_form = result.get('matched_title_form', 'N/A')
                print(f"      Confidence: {confidence} | Matched as: {matched_form}")
                return result['article_text']
            else:
                search_notes = result.get('search_notes', 'No notes')
                print(f"      Not found: {search_notes}")
            return None
        
        except errors.ServerError:
            wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
            time.sleep(wait_time)
        except (json.JSONDecodeError, Exception) as e:
            print(f"    [Gemini extraction attempt {attempt}] Error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BASE_DELAY)
                continue
    
    return None

def find_article_in_source(source_text, title, authors, next_title=None, page=None):
    """
    Find article text in source file by searching through entire file in chunks.
    Uses Gemini AI for intelligent extraction.
    Returns the article text or None if not found.
    """
    lines = source_text.split('\n')
    total_lines = len(lines)
    
    # Create variations of the title to search for
    title_lower = title.lower()
    title_upper = title.upper()
    title_normalized = normalize_title(title)
    
    # Strategy 1: If page number exists, prioritize that region
    if page:
        page_str = str(page)
        print(f"    🔍 Searching for page {page}...")
        for i, line in enumerate(lines):
            if re.match(rf'^\s*{page_str}\s*$', line) or re.match(rf'^{page_str}\s+\w', line):
                # Found page, extract large region
                region_start = max(0, i - 50)
                region_end = min(total_lines, i + 2000)
                text_chunk = '\n'.join(lines[region_start:region_end])
                print(f"    📍 Found page {page} at line {i}, searching {region_end - region_start} lines...")
                print(f"    🤖 Using Gemini AI for intelligent extraction...")
                
                result = use_gemini_to_find_article(text_chunk, title, authors, page)
                if result:
                    return result
                break
    
    # Strategy 2: Quick title scan for potential regions
    potential_regions = []
    print(f"    🔍 Scanning {total_lines} lines for title matches...")
    
    for i, line in enumerate(lines):
        line_normalized = normalize_title(line)
        # Check for title match
        if (title_normalized in line_normalized or 
            title_lower in line.lower() or
            title_upper in line):
            potential_regions.append(i)
    
    if potential_regions:
        print(f"    📍 Found {len(potential_regions)} potential title match(es)")
        # Try each potential region
        for idx, region_center in enumerate(potential_regions, 1):
            region_start = max(0, region_center - 50)
            region_end = min(total_lines, region_center + 2000)
            text_chunk = '\n'.join(lines[region_start:region_end])
            print(f"    🤖 Trying region {idx}/{len(potential_regions)} (line {region_center})...")
            
            result = use_gemini_to_find_article(text_chunk, title, authors, page)
            if result:
                return result
    
    # Strategy 3: Chunk through entire file if nothing found yet
    print(f"    🔄 No quick matches found. Searching entire file in chunks...")
    CHUNK_SIZE = 8000  # Lines per chunk
    OVERLAP = 500      # Overlap between chunks
    
    chunk_num = 0
    start_line = 0
    
    while start_line < total_lines:
        chunk_num += 1
        end_line = min(start_line + CHUNK_SIZE, total_lines)
        text_chunk = '\n'.join(lines[start_line:end_line])
        
        print(f"    🤖 Searching chunk {chunk_num} (lines {start_line}-{end_line})...")
        
        result = use_gemini_to_find_article(text_chunk, title, authors, page)
        if result:
            print(f"    ✓ Found in chunk {chunk_num}!")
            return result
        
        # Move to next chunk with overlap
        start_line += CHUNK_SIZE - OVERLAP
        
        # Rate limiting between chunks
        time.sleep(2)
    
    print(f"    ✗ Article not found after searching entire file ({chunk_num} chunks)")
    return None


def call_gemini_for_metadata(text, title, authors):
    """Call Gemini to generate abstract and tags."""
    # Limit text length for API call
    text_preview = text[:3000] if len(text) > 3000 else text
    
    prompt_text = EXTRACT_PROMPT.format(text=text_preview)
    
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
                    max_output_tokens=500,
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
            
            # Save raw Gemini output
            output_file = f"gemini_metadata_{normalize_title(title)[:30]}_{attempt}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== METADATA REQUEST ===\n")
                f.write(f"Title: {title}\n")
                f.write(f"Authors: {', '.join(authors)}\n")
                f.write(f"Attempt: {attempt}\n\n")
                f.write(f"=== TEXT PREVIEW ===\n")
                f.write(text_preview[:500])
                f.write(f"\n\n=== RAW RESPONSE ===\n")
                f.write(response.text)
                f.write(f"\n\n=== CLEANED RESPONSE ===\n")
                f.write(text_response)
            
            result = json.loads(text_response)
            return result.get('abstract', ''), result.get('tags', [])
        
        except errors.ServerError:
            wait_time = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
            time.sleep(wait_time)
        except (json.JSONDecodeError, Exception) as e:
            print(f"    [Attempt {attempt}] Error generating metadata: {e}")
            time.sleep(BASE_DELAY)
    
    # Fallback: create simple abstract from first sentences
    sentences = text_preview.split('. ')[:2]
    fallback_abstract = '. '.join(sentences) + '.' if sentences else text_preview[:200]
    fallback_tags = list(set([author.split()[-1] for author in authors]))  # Author last names
    
    return fallback_abstract, fallback_tags

def main():
    print("="*70)
    print("Article Matcher - Using Table of Contents")
    print("="*70)
    
    # Load files
    print(f"\nLoading {SOURCE_FILE}...")
    source_text = Path(SOURCE_FILE).read_text(encoding='utf-8')
    print(f"Source file: {len(source_text):,} characters")
    
    print(f"\nLoading {TOC_FILE}...")
    with open(TOC_FILE, 'r', encoding='utf-8') as f:
        toc_entries = json.load(f)
    print(f"Table of contents: {len(toc_entries)} entries\n")
    
    # PHASE 1: Extract all article texts
    print("="*70)
    print("PHASE 1: EXTRACTING ARTICLE TEXTS")
    print("="*70)
    
    extracted_articles = []
    not_found = []
    
    for idx, entry in enumerate(toc_entries, 1):
        title = entry.get('name', '')
        authors = entry.get('authors', [])
        volume = entry.get('volume')
        years = entry.get('years', '')
        page = entry.get('page')
        
        print(f"\n[{idx}/{len(toc_entries)}] Extracting: {title}")
        if page:
            print(f"  📄 Page: {page}")
        
        # Get next title for better boundary detection
        next_title = toc_entries[idx]['name'] if idx < len(toc_entries) else None
        
        # Find article in source (using page number if available)
        article_text = find_article_in_source(source_text, title, authors, next_title, page)
        
        if not article_text or len(article_text) < 50:
            print(f"  ✗ Not found or too short")
            not_found.append(title)
            continue
        
        print(f"  ✓ Found ({len(article_text)} chars)")
        
        # Store article without metadata for now
        extracted_articles.append({
            "Title": title,
            "Authors": authors,
            "Text": article_text,
            "Volume": volume,
            "Years": years,
            "Page": page
        })
        
        # Rate limiting
        time.sleep(1.5 + random.uniform(0, 1.0))
    
    # Save intermediate results
    print(f"\n{'='*70}")
    print(f"PHASE 1 COMPLETE")
    print(f"{'='*70}")
    print(f"Extracted: {len(extracted_articles)}/{len(toc_entries)} articles")
    print(f"Not found: {len(not_found)} articles")
    
    # Save articles without metadata
    intermediate_file = "articles_extracted.json"
    with open(intermediate_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_articles, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved extracted articles to {intermediate_file}")
    
    # PHASE 2: Generate metadata for all extracted articles
    print(f"\n{'='*70}")
    print("PHASE 2: GENERATING METADATA")
    print("="*70)
    
    matched_articles = []
    
    for idx, article in enumerate(extracted_articles, 1):
        title = article['Title']
        authors = article['Authors']
        article_text = article['Text']
        
        print(f"\n[{idx}/{len(extracted_articles)}] Generating metadata: {title}")
        print(f"  🤖 Calling Gemini for abstract and tags...")
        
        abstract, tags = call_gemini_for_metadata(article_text, title, authors)
        
        # Add metadata to article
        matched_articles.append({
            "Title": title,
            "Authors": authors,
            "Abstract": abstract,
            "Text": article_text,
            "Tags": tags,
            "Volume": article['Volume'],
            "Years": article['Years'],
            "Page": article['Page']
        })
        
        print(f"  ✓ Complete (tags: {len(tags)})")
        
        # Rate limiting
        time.sleep(1.5 + random.uniform(0, 1.0))
    
    # Save results
    print(f"\n{'='*70}")
    print(f"Saving {len(matched_articles)} articles to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(matched_articles, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Successfully saved to {OUTPUT_FILE}")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total entries in TOC: {len(toc_entries)}")
    print(f"Articles matched: {len(matched_articles)}")
    print(f"Not found: {len(not_found)}")
    
    if not_found:
        print(f"\nArticles not found:")
        for title in not_found[:10]:
            print(f"  - {title}")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")
    
    # Show sample
    if matched_articles:
        print(f"\nSample article:")
        sample = matched_articles[0]
        print(f"Title: {sample['Title']}")
        print(f"Authors: {', '.join(sample['Authors'])}")
        print(f"Volume: {sample['Volume']} ({sample['Years']})")
        print(f"Abstract: {sample['Abstract'][:150]}...")
        print(f"Tags: {', '.join(sample['Tags'])}")
        print(f"Text length: {len(sample['Text'])} chars")

if __name__ == "__main__":
    main()
