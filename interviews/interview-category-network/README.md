# Project Documentation for Interview Category Network

## Overview
The Interview Category Network project aims to visualize the relationships between different categories derived from a collection of interviews. By leveraging Plotly for interactive visualizations and NetworkX for graph analysis, this project provides insights into the connections and similarities among various categories.

## Project Structure
```
interview-category-network
├── src
│   ├── data
│   │   └── interviewss.json
│   ├── analysis
│   │   ├── category_network.py
│   │   └── network_utils.py
│   ├── visualization 
│   │   ├── plotly_graph.py
│   │   └── network_viz.py
│   └── utils
│       └── data_processing.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Setup Instructions
1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd interview-category-network
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. **Load the Data**
   Use the `load_data` function from `src/utils/data_processing.py` to load the interview data from `interviewss.json`.

2. **Analyze Categories**
   Call the `create_category_graph` function from `src/analysis/category_network.py` to analyze the categories and create a network structure.

3. **Visualize the Network**
   Use the `create_plotly_graph` function from `src/visualization/plotly_graph.py` to generate an interactive visualization of the category network.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for details.