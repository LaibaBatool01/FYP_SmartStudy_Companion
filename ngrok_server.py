from flask import Flask, request, jsonify
import pandas as pd
from knowledge_graph import KnowledgeGraphBuilder
import logging
from pyngrok import ngrok

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/process_knowledge_graph', methods=['POST'])
def process_knowledge_graph():
    try:
        # Get the CSV data from the request
        csv_data = request.files['csv_file']
        
        # Read the CSV data
        df = pd.read_csv(csv_data)
        logger.info(f"Received CSV with {len(df)} rows")
        
        # Initialize KG builder
        kg_builder = KnowledgeGraphBuilder()
        kg_builder.set_domain('programming')
        
        # Build knowledge graph
        relationships_df = kg_builder.build_knowledge_graph(df)
        
        # Convert results to JSON
        results = relationships_df.to_dict(orient='records')
        
        return jsonify({
            'status': 'success',
            'relationships': results
        })
        
    except Exception as e:
        logger.error(f"Error processing knowledge graph: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def start_ngrok():
    # Start ngrok tunnel
    public_url = ngrok.connect(5000)
    logger.info(f"Ngrok tunnel established at: {public_url}")
    return public_url

if __name__ == '__main__':
    # Start ngrok tunnel
    public_url = start_ngrok()
    
    # Run Flask app
    app.run(port=5000) 