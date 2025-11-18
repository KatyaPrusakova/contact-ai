import networkx as nx
from collections import defaultdict

def create_category_graph(interviews: list) -> nx.Graph:
    """
    Create a network graph where nodes are categories and edges represent
    co-occurrence in interviews.
    
    Args:
        interviews: List of interview dictionaries with 'categories' field
        
    Returns:
        NetworkX graph with categories as nodes and weighted edges for co-occurrences
    """
    # Create an empty graph
    G = nx.Graph()
    
    # Track category co-occurrences
    category_pairs = defaultdict(int)
    category_counts = defaultdict(int)
    
    # Process each interview
    for interview in interviews:
        if not isinstance(interview, dict):
            continue
            
        categories = interview.get('categories', [])
        
        # Count individual categories
        for category in categories:
            category_counts[category] += 1
            
        # Add edges between all pairs of categories in this interview
        for i in range(len(categories)):
            for j in range(i + 1, len(categories)):
                pair = tuple(sorted([categories[i], categories[j]]))
                category_pairs[pair] += 1
    
    # Add nodes with size based on frequency
    for category, count in category_counts.items():
        G.add_node(category, size=count)
    
    # Add edges with weights based on co-occurrence
    for (cat1, cat2), weight in category_pairs.items():
        G.add_edge(cat1, cat2, weight=weight)
    
    return G

def get_community_clusters(G: nx.Graph) -> dict:
    """
    Detect communities in the category network using the Louvain method
    
    Args:
        G: NetworkX graph of categories
        
    Returns:
        Dictionary mapping nodes to their community IDs
    """
    try:
        import community
        return community.best_partition(G)
    except ImportError:
        print("python-louvain package not installed. Install with: pdeip install python-louvain")
        return {node: 0 for node in G.nodes()}