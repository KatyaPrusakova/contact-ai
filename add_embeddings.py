import os
from supabase import create_client, Client
import time
from typing import List, Dict, Any
import requests

# Configuration
SUPABASE_URL = "https://tlykfbxilbcyiownnyvi.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRseWtmYnhpbGJjeWlvd25ueXZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0ODgyNjIsImV4cCI6MjA3OTA2NDI2Mn0.AWkHw2oZzkRxm6ScuBGYKkiBtYsX8Or3P3GD28OVOUo"
OLLAMA_API_URL = "http://localhost:11434/api/embeddings"

def create_supabase_client() -> Client:
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_embedding(text: str, model: str = "mxbai-embed-large") -> List[float]:
    """Generate embedding for text using Ollama mxbai-embed-large model."""
    
    try:
        payload = {
            "model": model,
            "prompt": text
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload)
        
        if response.status_code != 200:
            error_detail = response.text
            print(f"Ollama API Error: {response.status_code} - {error_detail}")
            return None
            
        result = response.json()
        embedding = result.get('embedding')
        
        if not embedding:
            print("No embedding returned from Ollama")
            return None
        
        # mxbai-embed-large produces 1024 dimensions, pad to 1536 for database
        if len(embedding) < 1536:
            padding = [0.0] * (1536 - len(embedding))
            embedding = embedding + padding
            
        return embedding
        
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def process_articles_with_embeddings(supabase: Client, batch_size: int = 10):
    """Fetch articles, generate embeddings, and update database."""
    
    print("Fetching articles from database...")
    # Fetch all articles with all relevant fields
    response = supabase.table("articles").select("id, title, content, author, main_category, secondary_tags, years").execute()
    articles = response.data
    
    print(f"Found {len(articles)} articles")
    print(f"Processing in batches of {batch_size}...")
    
    success_count = 0
    error_count = 0
    
    for i, article in enumerate(articles):
        try:
            article_id = article['id']
            title = article['title']
            content = article['content']
            author = article.get('author', '')
            main_category = article.get('main_category', '')
            secondary_tags = article.get('secondary_tags', [])
            years = article.get('years', '')
            
            # Build comprehensive text including all metadata for rich semantic search
            # This ensures searches for author names, tags, categories, and content all work
            text_parts = [
                f"Title: {title}",
                f"Authors: {author}" if author else "",
                f"Category: {main_category}" if main_category else "",
                f"Tags: {', '.join(secondary_tags)}" if secondary_tags else "",
                f"Year: {years}" if years else "",
                f"\nContent:\n{content}"
            ]
            
            # Filter out empty parts and join
            text_to_embed = "\n".join([part for part in text_parts if part])
            
            print(f"\n[{i+1}/{len(articles)}] Processing: {title[:50]}...")
            
            # Generate embedding
            embedding = get_embedding(text_to_embed)
            
            if embedding:
                # Update article with embedding
                supabase.table("articles").update({
                    "content_embedding": embedding
                }).eq("id", article_id).execute()
                
                print(f"✓ Updated article {article_id}")
                success_count += 1
            else:
                print(f"✗ Failed to generate embedding for article {article_id}")
                error_count += 1
            
            # Rate limiting - wait between requests to avoid hitting API limits
            if (i + 1) % batch_size == 0:
                print(f"\nCompleted {i+1} articles. Pausing for 2 seconds...")
                time.sleep(2)
            else:
                time.sleep(0.2)  # Small delay between requests
                
        except Exception as e:
            print(f"✗ Error processing article {article.get('id')}: {e}")
            error_count += 1
            continue
    
    print(f"\n{'='*80}")
    print(f"Embedding generation complete!")
    print(f"✓ Success: {success_count}")
    print(f"✗ Errors: {error_count}")
    print(f"{'='*80}")

def main():
    print("Article Embedding Generator (Ollama - mxbai-embed-large)")
    print("="*80)
    print("\nThis script will:")
    print("1. Fetch all articles from Supabase")
    print("2. Generate embeddings using Ollama mxbai-embed-large model")
    print("3. Update the content_embedding column")
    print("\nNote: Make sure Ollama is running with 'ollama serve'")
    print("      and mxbai-embed-large model is pulled with 'ollama pull mxbai-embed-large'")
    print("="*80)
    
    confirm = input("\nProceed? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return
    
    try:
        # Create clients
        supabase = create_supabase_client()
        
        print("\n✓ Connected to Supabase")
        print("✓ Ollama API configured (localhost:11434)")
        
        # Process articles
        process_articles_with_embeddings(supabase)
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
