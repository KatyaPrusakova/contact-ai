import re
import json

def extract_author(text):
    """Extract author name(s) from 'by Author Name' pattern."""
    # Look for "by Author Name" pattern - must have "by " before the name
    # Pattern looks for "by " followed by name(s) until end of line
    # Matches names with capitals, spaces, periods, hyphens, commas
    pattern = r'(?:^|\n)\s*[Bb]y\s+([A-Z][a-zA-Z\s\.\-,]+?)(?:\s*\n|$)'
    
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        author_string = match.group(1).strip()
        # Clean up extra whitespace
        author_string = re.sub(r'\s+', ' ', author_string)
        
        # Split by comma if multiple authors
        if ',' in author_string:
            # Split and clean each author name
            authors = [name.strip() for name in author_string.split(',')]
            # Filter out empty strings and "and" connectors
            authors = [a for a in authors if a and a.lower() != 'and']
            return authors
        else:
            return [author_string]
    
    return []

def clean_author_from_text(text, authors):
    """Remove author line from text."""
    if authors:
        # Join authors back to match the original format
        author_string = ', '.join(authors)
        # Remove "by Author Name(s)" line
        text = re.sub(rf'\s*[Bb]y\s+{re.escape(author_string)}\s*', '', text)
    return text.strip()

def extract_abstract(text):
    """Return empty string for abstract."""
    return ""

def parse_source18(file_path):
    """Parse source18.txt file and extract articles."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by separator lines (dashes)
    # Match lines with 10 or more dashes
    articles_raw = re.split(r'\n-{10,}\n', content)
    
    articles = []
    
    for idx, article_block in enumerate(articles_raw):
        article_block = article_block.strip()
        
        if not article_block or len(article_block) < 50:
            continue
        
        lines = article_block.split('\n')
        
        # Extract author from entire block
        author = extract_author(article_block)
        
        # Find title and build content simultaneously
        title = None
        content_lines = []
        found_title = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines at the beginning
            if not found_title and not line_stripped:
                continue
            
            # Skip separator lines (dashes)
       
            # Check if this is an author line
            if line_stripped.lower().startswith('by '):
                # Don't include in content
                continue
            
            # First non-empty, non-author, non-separator line is the title
            if not found_title and line_stripped and len(line_stripped) >= 3:
                title = line_stripped
                found_title = True
                continue
            
            # After title is found, everything else is content (except author lines)
            if found_title:
                content_lines.append(line)
        
        if not title:
            continue
        
        # Join content lines
        article_text = '\n'.join(content_lines).strip()
        
        # Abstract is empty
        abstract = extract_abstract(article_text)
        
        # Create article entry
        article_entry = {
            "Title": title,
            "Authors": author if author else [],  # author is now a list
            "Abstract": abstract,
            "Content": article_text,
            "Tags": [],
            "Volume": 20,
            "Years": 1995
        }
        
        articles.append(article_entry)
        
        # Format author display
        author_display = ', '.join(author) if author else 'Not found'
        print(f"[{len(articles)}] {title[:50]}... | Author: {author_display}")
    
    return articles

def main():
    print("="*70)
    print("Parsing source18.txt")
    print("="*70)
    
    input_file = "source20.txt"
    output_file = "source20.json"
    
    print(f"\nReading {input_file}...")
    articles = parse_source18(input_file)
    
    print(f"\n{'='*70}")
    print(f"Extracted {len(articles)} articles")
    print(f"{'='*70}")
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved to {output_file}")
    
    # Show sample
    if articles:
        print(f"\nSample article:")
        sample = articles[0]
        print(f"Title: {sample['Title']}")
        print(f"Authors: {sample['Authors']}")
        print(f"Volume: {sample['Volume']} ({sample['Years']})")
        print(f"Abstract: {sample['Abstract'][:100]}...")
        print(f"Content length: {len(sample['Content'])} chars")

if __name__ == "__main__":
    main()
