# Contents of `network_utils.py`

def draw_graph(graph):
    import matplotlib.pyplot as plt
    import networkx as nx

    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_size=2000, node_color='lightblue', font_size=10, font_weight='bold', edge_color='gray')
    plt.title("Category Network Graph")
    plt.show()

def save_graph(graph, filename):
    import networkx as nx

    nx.write_gml(graph, filename)