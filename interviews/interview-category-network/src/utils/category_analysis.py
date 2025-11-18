import json
from sentence_transformers import SentenceTransformer, util
from collections import defaultdict
from typing import List, Dict, Tuple
import logging
import torch
from pathlib import Path
from sklearn.cluster import AgglomerativeClustering
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CategoryAnalyzer:
    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize with BERT model and similarity threshold"""
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.similarity_threshold = similarity_threshold
        
    def get_all_categories(self, interviews: List[Dict]) -> List[str]:
        """Extract all unique categories from interviews"""
        categories = set()
        for interview in interviews:
            categories.update(interview.get('categories', []))
        return list(categories)
    
    def find_similar_categories(self, categories: List[str]) -> List[Tuple[str, str, float]]:
        """Find semantically similar category pairs using BERT embeddings"""
        similar_pairs = []
        
        # Compute embeddings for all categories
        embeddings = self.model.encode(categories, convert_to_tensor=True)
        
        # Compute cosine similarity between all pairs
        cosine_scores = util.pytorch_cos_sim(embeddings, embeddings)
        
        # Find similar pairs
        for i in range(len(categories)):
            for j in range(i + 1, len(categories)):
                similarity = cosine_scores[i][j].item()
                if similarity >= self.similarity_threshold:
                    similar_pairs.append((categories[i], categories[j], similarity))
        
        return sorted(similar_pairs, key=lambda x: x[2], reverse=True)
    
    def group_similar_categories(self, categories: List[str]) -> Dict[str, List[str]]:
        """Group similar categories together"""
        groups = defaultdict(list)
        processed = set()
        
        similar_pairs = self.find_similar_categories(categories)
        
        for cat1, cat2, similarity in similar_pairs:
            if cat1 not in processed and cat2 not in processed:
                group_name = cat1  # Use first category as group name
                groups[group_name].extend([cat1, cat2])
                processed.update([cat1, cat2])
            elif cat1 not in processed:
                for group_name, group in groups.items():
                    if cat2 in group:
                        groups[group_name].append(cat1)
                        processed.add(cat1)
                        break
            elif cat2 not in processed:
                for group_name, group in groups.items():
                    if cat1 in group:
                        groups[group_name].append(cat2)
                        processed.add(cat2)
                        break
        
        # Add ungrouped categories
        for category in categories:
            if category not in processed:
                groups[category].append(category)
        
        return dict(groups)

    def get_category_counts(self, interviews: List[Dict]) -> Dict[str, int]:
        """
        Count the number of articles/interviews for each category
        
        Args:
            interviews: List of interview dictionaries
            
        Returns:
            Dictionary mapping categories to their counts
        """
        category_counts = defaultdict(int)
        for interview in interviews:
            categories = interview.get('categories', [])
            for category in categories:
                category_counts[category] += 1
        return dict(category_counts)

    def get_main_categories(self, categories: List[str], n_clusters: int = 6) -> Dict[str, List[str]]:
        """
        Group all categories into main themes using hierarchical clustering
        
        Args:
            categories: List of category names
            n_clusters: Number of main categories to create
            
        Returns:
            Dictionary mapping main category names to lists of subcategories
        """
        # Get embeddings for all categories
        embeddings = self.model.encode(categories, convert_to_tensor=True)
        
        # Convert to numpy for clustering
        embeddings_np = embeddings.cpu().numpy()
        
        # Perform hierarchical clustering
        clustering = AgglomerativeClustering(n_clusters=n_clusters)
        cluster_labels = clustering.fit_predict(embeddings_np)
        
        # Group categories by cluster
        clusters = defaultdict(list)
        for category, label in zip(categories, cluster_labels):
            clusters[label].append(category)
            
        # Find the most representative category for each cluster
        main_categories = {}
        for cluster_id, cluster_categories in clusters.items():
            # Get embeddings for this cluster's categories
            cluster_embeddings = self.model.encode(cluster_categories, convert_to_tensor=True)
            
            # Calculate centroid
            centroid = torch.mean(cluster_embeddings, dim=0)
            
            # Find category closest to centroid
            distances = torch.norm(cluster_embeddings - centroid, dim=1)
            main_category = cluster_categories[torch.argmin(distances)]
            
            main_categories[main_category] = cluster_categories
            
        return main_categories

    def update_json_with_main_categories(self, data: Dict, main_categories: Dict[str, List[str]]) -> Dict:
        """
        Update the JSON data to include main categories for each interview
        
        Args:
            data: Original JSON data dictionary
            main_categories: Dictionary of main categories and their subcategories
            
        Returns:
            Updated JSON data dictionary
        """
        # Create reverse mapping from subcategory to main category
        subcat_to_main = {}
        for main_cat, subcats in main_categories.items():
            for subcat in subcats:
                subcat_to_main[subcat] = main_cat
        
        # Update each interview with main categories
        for interview in data['interviews']:
            main_cats = set()
            for category in interview.get('categories', []):
                if category in subcat_to_main:
                    main_cats.add(subcat_to_main[category])
            interview['main_categories'] = list(main_cats)
        
        return data

def main():
    # Get the correct path to the data file
    current_dir = Path(__file__).parent
    data_file = current_dir.parent / "data" / "interviewss.json"
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Data file not found at: {data_file}")
        logger.info("Please ensure interviewss.json exists in the src/data directory")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in file: {data_file}")
        return
    
    analyzer = CategoryAnalyzer(similarity_threshold=0.6)
    
    # Get category counts
    category_counts = analyzer.get_category_counts(data['interviews'])
    logger.info("\nArticles per category:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"{category:<30} : {count:>3} articles")
    
    # Get all unique categories
    categories = analyzer.get_all_categories(data['interviews'])
    logger.info(f"Found {len(categories)} unique categories")
    
    # Find similar categories
    similar_pairs = analyzer.find_similar_categories(categories)
    logger.info("\nSimilar category pairs:")
    for cat1, cat2, similarity in similar_pairs:
        logger.info(f"{cat1:<30} - {cat2:<30} : {similarity:.3f}")
    
    # Group similar categories
    groups = analyzer.group_similar_categories(categories)
    logger.info("\nCategory groups:")
    for group_name, group_categories in groups.items():
        if len(group_categories) > 1:  # Only show groups with multiple categories
            logger.info(f"\n{group_name}:")
            for category in group_categories:
                if category != group_name:
                    logger.info(f"  - {category}")
    
    # Group into 6 main categories
    logger.info("\n=== Main Category Groups ===")
    main_categories = analyzer.get_main_categories(categories)
    
    for main_cat, subcats in main_categories.items():
        logger.info(f"\n### {main_cat} ###")
        for subcat in sorted(subcats):
            if subcat != main_cat:
                # Get count for this category
                count = category_counts.get(subcat, 0)
                logger.info(f"  - {subcat:<30} ({count:>2} articles)")
    
    # Update JSON with main categories
    updated_data = analyzer.update_json_with_main_categories(data, main_categories)
    
    # Save updated JSON
    output_file = current_dir.parent / "data" / "interviews_with_main_categories.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        logger.info(f"\nUpdated JSON saved to: {output_file}")
    except Exception as e:
        logger.error(f"Error saving updated JSON: {e}")

if __name__ == "__main__":
    main()