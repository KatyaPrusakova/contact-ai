import os
import sys
import logging
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from utils.data_processing import load_data
from analysis.category_network import create_category_graph
from vis.plotly_graph import create_plotly_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Load interview data
    data_path = Path(__file__).parent / "data" / "talk.json"
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Check if data is wrapped in a container
            if isinstance(data, dict) and 'interviews' in data:
                interviews = data['interviews']
            elif isinstance(data, list):
                interviews = data
            else:
                logger.error(f"Unexpected data structure in {data_path}")
                return
    except FileNotFoundError:
        logger.error(f"Data file not found: {data_path}")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {data_path}")
        return
        
    # Log categories found
    all_categories = set()
    for interview in interviews:
        if isinstance(interview, dict):
            categories = interview.get('categories', [])
            if categories:
                all_categories.update(categories)
        else:
            logger.warning(f"Skipping invalid interview data: {interview}")
            
    logger.info(f"Found {len(all_categories)} unique categories")
    logger.info(f"Categories: {sorted(all_categories)}")
    
    # Create category network
    G = create_category_graph(interviews)
    
    # Validate graph
    logger.info(f"Graph has {len(G.nodes)} nodes and {len(G.edges)} edges")
    
    # Generate and save visualization
    output_path = Path(__file__).parent.parent / "output"
    output_path.mkdir(exist_ok=True)
    
    fig = create_plotly_graph(G)
    fig.write_html(output_path / "category_network.html")
    logger.info(f"Network visualization saved to {output_path}/category_network.html")

if __name__ == "__main__":
    main()