# Uploading Contact Improvisation Articles to Supabase

## Step 1: Install Dependencies

```bash
pip install -r requirements_supabase.txt
```

## Step 2: Get Your Supabase Credentials

1. Go to your Supabase project: https://supabase.com/dashboard
2. Click on your project
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** (looks like: `https://xxxxx.supabase.co`)
   - **anon/public key** (the `anon` key under "Project API keys")

## Step 3: Set Environment Variables

```bash
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_KEY='your-anon-key-here'
```

Or create a `.env` file:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
```

## Step 4: Create Database Table

The script will show you the SQL schema. Copy it and:

1. Go to your Supabase project
2. Click **SQL Editor** in the left sidebar
3. Paste the SQL schema
4. Click **Run** to create the table

## Step 5: Run the Upload Script

```bash
python3 upload_to_supabase.py
```

The script will:
- Connect to your Supabase database
- Upload all 158 articles in batches
- Create proper indexes for search
- Verify the upload

## Database Schema

The `articles` table will have:
- **id**: Auto-incrementing primary key
- **title**: Article title
- **authors**: Array of author names
- **abstract**: Article abstract
- **text**: Full article text
- **tags**: Array of tags
- **category**: Article category (Art & Performance, Somatics & Body Awareness, etc.)
- **volume**: CQ volume number
- **years**: Publication years
- **created_at**: Timestamp
- **updated_at**: Timestamp

## Querying Your Data

After upload, you can query using Supabase client or API:

```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get all articles
articles = supabase.table("articles").select("*").execute()

# Search by title
results = supabase.table("articles")\
    .select("*")\
    .ilike("title", "%contact%")\
    .execute()

# Filter by category
results = supabase.table("articles")\
    .select("*")\
    .eq("category", "Art & Performance")\
    .execute()

# Search by tag
results = supabase.table("articles")\
    .select("*")\
    .contains("tags", ["Improvisation"])\
    .execute()

# Full-text search on article text
results = supabase.table("articles")\
    .select("*")\
    .text_search("text", "gravity falling")\
    .execute()
```

## Troubleshooting

- **Connection Error**: Check your SUPABASE_URL and SUPABASE_KEY
- **Permission Error**: Make sure RLS policies are set correctly
- **Upload Fails**: The script continues with next batch if one fails
- **Large Text Fields**: Some articles have very long text, this is normal

## Next Steps

After uploading, you can:
1. Use Supabase REST API to query data
2. Build a web interface with Next.js/React
3. Create full-text search with PostgreSQL
4. Add authentication for write operations
5. Export data for ML/AI training
