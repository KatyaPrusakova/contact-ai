import json
import os
from supabase import create_client, Client
from typing import List, Dict, Any

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

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
    # Don't include 'id' - let Supabase auto-generate it
    prepared = {
        "title": article.get("Title", ""),
        "authors": article.get("Authors", []),
        "abstract": article.get("Abstract", ""),
        "text": article.get("Text", ""),
        "tags": article.get("Tags", []),
        "category": article.get("Category", ""),
        "volume": article.get("Volume"),
        "years": article.get("Years", "")
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

def print_sql_schema():
    """Print the SQL schema for creating the table in Supabase."""
    schema = """
-- SQL Schema for Supabase
-- Run this in your Supabase SQL Editor before uploading data

CREATE TABLE IF NOT EXISTS articles (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT[] DEFAULT '{}',
    abstract TEXT DEFAULT '',
    text TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    category TEXT DEFAULT '',
    volume INTEGER,
    years TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_articles_text ON articles USING gin(to_tsvector('english', text));
CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_volume ON articles(volume);
CREATE INDEX IF NOT EXISTS idx_articles_authors ON articles USING gin(authors);

-- Enable Row Level Security (RLS)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public read access (adjust as needed)
CREATE POLICY "Allow public read access" ON articles
    FOR SELECT TO public
    USING (true);

-- Create policy to allow authenticated users to insert (adjust as needed)
CREATE POLICY "Allow authenticated insert" ON articles
    FOR INSERT TO authenticated
    WITH CHECK (true);

-- Create policy to allow authenticated users to update (adjust as needed)
CREATE POLICY "Allow authenticated update" ON articles
    FOR UPDATE TO authenticated
    USING (true);
"""
    print(schema)
    print("\n" + "="*80)
    print("Copy and run the above SQL in your Supabase SQL Editor")
    print("="*80 + "\n")

def main():
    print("Contact Improvisation Articles - Supabase Uploader")
    print("=" * 80)
    
    # Print SQL schema
    print_sql_schema()
    
    input("Press Enter after you've created the table in Supabase...")
    
    try:
        # Create Supabase client
        supabase = create_supabase_client()
        print("✓ Connected to Supabase")
        
        # Load articles
        articles = load_articles("matched_articles_normalized.json")
        
        # Prepare articles for upload
        prepared_articles = [
            prepare_article_for_upload(article, i) 
            for i, article in enumerate(articles)
        ]
        
        # Upload articles
        upload_articles_batch(supabase, prepared_articles)
        
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
