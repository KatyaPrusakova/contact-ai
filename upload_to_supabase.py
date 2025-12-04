import json
import os
from supabase import create_client, Client
from typing import List, Dict, Any

# Supabase configuration
SUPABASE_URL = "https://tlykfbxilbcyiownnyvi.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRseWtmYnhpbGJjeWlvd25ueXZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0ODgyNjIsImV4cCI6MjA3OTA2NDI2Mn0.AWkHw2oZzkRxm6ScuBGYKkiBtYsX8Or3P3GD28OVOUo"

def create_supabase_client() -> Client:
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError(
            "Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.\n"
            "You can set them by running:\n"
            "export SUPABASE_URL='your-project-url'\n"
            "export SUPABASE_ANON_KEY='your-anon-key'"
        )
    
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def load_articles(json_file: str) -> List[Dict[str, Any]]:
    """Load articles from JSON file."""
    print(f"Loading articles from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    print(f"Loaded {len(articles)} articles")
    return articles

def prepare_article_for_upload(article: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Prepare article data for Supabase upload."""
    # Get content field (could be "Text" or "Content")
    content = article.get("Content", article.get("Text", ""))
    authors = article.get("Authors", [])
    author_str = ", ".join(authors) if authors else "Unknown"
    
    # Estimate read time (assuming 200 words per minute)
    word_count = len(content.split())
    read_time = max(1, word_count // 200)
    
    # Get abstract/excerpt
    abstract = article.get("Abstract", "")
    if not abstract and content:
        # Create excerpt from first 200 characters
        abstract = content[:200] + "..." if len(content) > 200 else content
    
    # Get tags - combine Tags array into tags string if needed
    tags_list = article.get("Tags", [])
    tags_str = ", ".join(tags_list) if tags_list else ""
    
    prepared = {
        "title": article.get("Title", "Untitled"),
        "content": content,
        "author": author_str,
        "main_category": article.get("Category", "Art & Performance"),
        "secondary_tags": tags_list,  # Keep as array for secondary_tags
        "excerpt": abstract,
        "read_time": read_time,
        "years": str(article.get("Years", "")),
        "upvotes": 0
    }
    
    return prepared

def upload_articles_batch(supabase: Client, articles: List[Dict[str, Any]], batch_size: int = 100):
    """Upload articles to Supabase in batches."""
    total = len(articles)
    print(f"\nUploading {total} articles in batches of {batch_size}...")
    
    for i in range(0, total, batch_size):
        batch = articles[i:i + batch_size]
        try:
            result = supabase.table("articles").insert(batch).execute()
            print(f"✓ Uploaded batch {i//batch_size + 1}: articles {i+1} to {min(i+batch_size, total)}")
        except Exception as e:
            print(f"✗ Error uploading batch {i//batch_size + 1}: {e}")
            print(f"  Failed on articles {i+1} to {min(i+batch_size, total)}")
            # Continue with next batch instead of stopping
            continue
    
    print(f"\n✓ Upload complete!")


def main():
    print("Contact Improvisation Articles - Supabase Uploader")
    print("=" * 80)
    
    # Use source18_enriched.json
    json_file = "source18_enriched.json"
    
    try:
        # Create Supabase client
        supabase = create_supabase_client()
        print("✓ Connected to Supabase")
        
        # Load articles
        articles = load_articles(json_file)
        
        # Prepare articles for upload
        print("\nPreparing articles for upload...")
        prepared_articles = [
            prepare_article_for_upload(article, i) 
            for i, article in enumerate(articles)
        ]
        print(f"✓ Prepared {len(prepared_articles)} articles")
        
        # Show sample
        if prepared_articles:
            print("\nSample article data:")
            sample = prepared_articles[0]
            print(f"  Title: {sample['title']}")
            print(f"  Author: {sample['author']}")
            print(f"  Category: {sample['main_category']}")
            print(f"  Tags: {sample['secondary_tags']}")
            print(f"  Read time: {sample['read_time']} min")
            print(f"  Excerpt: {sample['excerpt'][:100]}...")
        
        # Confirm before upload
        confirm = input("\nProceed with upload? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Upload cancelled.")
            return
        
        # Upload articles
        upload_articles_batch(supabase, prepared_articles, batch_size=10)
        
        # Verify upload
        print("\nVerifying upload...")
        result = supabase.table("articles").select("count", count="exact").execute()
        print(f"✓ Total articles in database: {result.count}")
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
    except FileNotFoundError:
        print(f"\n✗ Error: matched_articles_normalized.json not found")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
