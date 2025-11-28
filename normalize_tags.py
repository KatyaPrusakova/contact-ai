import json
import re
from collections import Counter
from typing import List, Dict, Set

# Define the semantic categories and their keywords
CATEGORY_KEYWORDS = {
    "Art & Performance": ["improvisation", "jam", "festival", "stage", "choreography", "creative", "artistic", "poem"],
    "Somatics & Body Awareness": ["somatic", "BMI", "body", "awareness", "movement", "sensation", "perception"],
    "Psychology & Consciousness": ["emotion", "trauma", "healing", "consciousness", "psychology", "integration"],
    "Pedagogy & Facilitation": ["lesson", "teaching", "facilitation", "pedagogy", "group", "instructor", "student", "practice"],
    "Philosophy": ["ethics", "philosophy", "presence"],
    "Culture & Community": ["community", "culture", "diversity", "global", "local", "inclusion"],
    "Science & Research": ["research", "anatomy", "analysis", "biomechanics", "data", "study", "academic"]
}

def normalize_tag(tag: str, canonical_forms: Dict[str, str]) -> str:
    """
    Normalize a tag to its canonical form (proper capitalization).
    Uses a dictionary of canonical forms based on most common usage.
    """
    tag_lower = tag.lower()
    
    # If we have a canonical form, use it
    if tag_lower in canonical_forms:
        return canonical_forms[tag_lower]
    
    # Otherwise, return the tag as-is
    return tag

def build_canonical_forms(all_tags: List[str]) -> Dict[str, str]:
    """
    Build a dictionary of canonical tag forms.
    For tags with capitalization variations, use the most frequent form.
    Special rules for common terms.
    """
    # Group tags by lowercase version
    tag_groups = {}
    for tag in all_tags:
        tag_lower = tag.lower()
        if tag_lower not in tag_groups:
            tag_groups[tag_lower] = []
        tag_groups[tag_lower].append(tag)
    
    canonical_forms = {}
    
    # Special rules for common terms
    special_cases = {
        "contact improvisation": "Contact Improvisation",
        "improvisation": "Improvisation",
        "dance": "Dance",
        "movement": "Movement",
        "body awareness": "Body Awareness",
        "teaching": "Teaching",
        "gravity": "Gravity",
        "momentum": "Momentum",
        "community": "Community",
        "trust": "Trust",
        "risk": "Risk",
        "listening": "Listening",
        "attention": "Attention",
        "receptivity": "Receptivity",
        "small dance": "Small Dance",
        "performance": "Performance",
        "dance technique": "Dance Technique",
        "dance education": "Dance Education",
        "somatic practice": "Somatic Practice",
        "dance pedagogy": "Dance Pedagogy",
        "aikido": "Aikido",
        "tai chi": "Tai Chi",
    }
    
    for tag_lower, variations in tag_groups.items():
        if tag_lower in special_cases:
            canonical_forms[tag_lower] = special_cases[tag_lower]
        elif len(variations) == 1:
            # Only one form exists, use it
            canonical_forms[tag_lower] = variations[0]
        else:
            # Multiple forms exist, use the most common one
            counter = Counter(variations)
            most_common = counter.most_common(1)[0][0]
            
            # Prefer title case over all lowercase
            title_case_versions = [v for v in variations if v[0].isupper()]
            if title_case_versions:
                # Use the most common title case version
                canonical_forms[tag_lower] = Counter(title_case_versions).most_common(1)[0][0]
            else:
                canonical_forms[tag_lower] = most_common
    
    return canonical_forms

def assign_category(tags: List[str], title: str, abstract: str = "") -> str:
    """
    Assign a single category based on tags, title, and abstract.
    Returns the category with the highest score.
    """
    # Combine all text to analyze
    text = " ".join(tags + [title, abstract]).lower()
    
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = 0
        for keyword in keywords:
            # Count matches with word boundaries
            matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
            scores[category] += matches
    
    # Get the category with the highest score
    if scores:
        top_category = max(scores.items(), key=lambda x: x[1])
        if top_category[1] > 0:
            return top_category[0]
    
    # Default category if no matches
    return "Art & Performance"

def clean_invalid_tags(tags: List[str]) -> List[str]:
    """
    Remove tags that appear to be metadata or errors rather than actual tags.
    """
    invalid_patterns = [
        r'^Title:',  # Tags starting with "Title:"
        r'^Paxton$',  # Just author names without context
        r'^Hughes$',
        r'^Wright$',
        r'^Knowlton$',
        r'^Jamrog$',
        r'^Marinelli$',
        r'^Ashwill$',
        r'^Hougee$',
        r'^Svane$',
        r'^\w+$' if len(tags) == 1 else None  # Single-word tags only if it's the only tag
    ]
    
    cleaned_tags = []
    for tag in tags:
        is_invalid = False
        for pattern in invalid_patterns:
            if pattern and re.match(pattern, tag):
                is_invalid = True
                break
        
        if not is_invalid:
            cleaned_tags.append(tag)
    
    return cleaned_tags if cleaned_tags else tags  # Return original if all would be removed

def normalize_articles(input_file: str, output_file: str):
    """
    Process matched_articles.json to:
    1. Normalize tag capitalization
    2. Add category field based on tags/content
    3. Clean invalid tags
    """
    print(f"Loading articles from {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error loading JSON: {e}")
        return
    
    print(f"Loaded {len(articles)} articles")
    
    # First pass: collect all tags to build canonical forms
    all_tags = []
    for article in articles:
        if "Tags" in article and isinstance(article["Tags"], list):
            all_tags.extend(article["Tags"])
    
    print(f"Found {len(all_tags)} total tags")
    print(f"Found {len(set(t.lower() for t in all_tags))} unique tags (case-insensitive)")
    
    # Build canonical forms
    canonical_forms = build_canonical_forms(all_tags)
    print(f"Created {len(canonical_forms)} canonical tag forms")
    
    # Second pass: normalize tags and add categories
    normalized_count = 0
    categories_added = 0
    
    for i, article in enumerate(articles):
        if "Tags" in article and isinstance(article["Tags"], list):
            # Clean invalid tags
            original_tags = article["Tags"]
            cleaned_tags = clean_invalid_tags(original_tags)
            
            # Normalize capitalization
            normalized_tags = [normalize_tag(tag, canonical_forms) for tag in cleaned_tags]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_tags = []
            for tag in normalized_tags:
                tag_lower = tag.lower()
                if tag_lower not in seen:
                    seen.add(tag_lower)
                    unique_tags.append(tag)
            
            article["Tags"] = unique_tags
            
            if unique_tags != original_tags:
                normalized_count += 1
        
        # Add category if not present
        if "Category" not in article:
            title = article.get("Title", "")
            abstract = article.get("Abstract", "")
            tags = article.get("Tags", [])
            
            category = assign_category(tags, title, abstract)
            article["Category"] = category
            categories_added += 1
        
        if (i + 1) % 20 == 0:
            print(f"Processed {i + 1}/{len(articles)} articles...")
    
    # Save normalized articles
    print(f"\nSaving normalized articles to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Successfully normalized {normalized_count} articles with tag changes")
    print(f"✓ Added categories to {categories_added} articles")
    print(f"✓ Total articles processed: {len(articles)}")
    
    # Print some statistics
    print("\nCategory distribution:")
    category_counts = Counter(article.get("Category", "Unknown") for article in articles)
    for category, count in category_counts.most_common():
        print(f"  {category}: {count}")

if __name__ == "__main__":
    input_file = "matched_articles.json"
    output_file = "matched_articles_normalized.json"
    
    normalize_articles(input_file, output_file)
    print("\n✓ Normalization complete!")
