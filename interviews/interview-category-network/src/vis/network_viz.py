# Contents of `network_viz.py`

import json
import plotly.graph_objects as go
from analysis.category_network import create_category_graph
from vis.plotly_graph import create_plotly_graph
from utils.data_processing import load_data

def main():
    # Load interview data
    data = load_data('src/data/interviewss.json')
    
    # Create category graph
    category_graph = create_category_graph(data)
    
    # Generate Plotly graph
    fig = create_plotly_graph(category_graph)
    
    # Show the figure
    fig.show()

if __name__ == "__main__":
    main()