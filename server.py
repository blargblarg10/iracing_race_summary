import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.race_pace.iracing_pace_func import plot_series
from argparse import Namespace

app = Flask(__name__, static_folder='src/race_pace/graph')
CORS(app)  # Enable CORS for all routes

@app.route('/generate-graphs', methods=['POST'])
def generate_graphs():
    try:
        # Generate graphs
        plot_series("iRacing Porsche Cup by CONSPIT")
        
        # Get list of generated graph files
        graph_dir = os.path.join('src', 'race_pace', 'graph')
        graphs = [f for f in os.listdir(graph_dir) if f.endswith('.png')]
        
        return jsonify({'status': 'success', 'graphs': graphs})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/graphs/<path:filename>')
def serve_graph(filename):
    return send_from_directory('src/race_pace/graph', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)