import streamlit as st
from pdf_toc_extractor import PDFTOCExtractor
from read_toc_file_AND_make_df import read_toc_file
import tempfile
import os
import requests
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

def clean_title(title: str) -> str:
    """Clean the title by removing special characters and multiple spaces"""
    # Replace common problematic characters
    title = title.replace('', '')
    
    # Remove non-printable characters while keeping basic punctuation and spaces
    cleaned = ''.join(char for char in title if char.isprintable() or char.isspace())
    
    # Remove multiple spaces and trim
    cleaned = ' '.join(cleaned.split())
    
    # Remove dots between words but keep trailing dots
    if cleaned.endswith('...'):
        cleaned = cleaned[:-3].replace('.', '') + '...'
    else:
        cleaned = cleaned.replace('.', '')
        
    return cleaned.strip()

def display_knowledge_graph(relationships_df):
    """Display the knowledge graph using Plotly"""
    G = nx.from_pandas_edgelist(
        relationships_df,
        source='prerequisite',
        target='topic',
        create_using=nx.DiGraph()
    )
    
    pos = nx.spring_layout(G)
    
    edge_trace = go.Scatter(
        x=[], y=[], 
        line=dict(width=0.5, color='#888'),
        hoverinfo='none', 
        mode='lines'
    )
    
    node_trace = go.Scatter(
        x=[], y=[], 
        text=[], 
        mode='markers+text',
        hoverinfo='text', 
        marker=dict(
            size=20,
            color='lightblue',
            line=dict(color='black', width=1)
        )
    )
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)
    
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
    
    node_trace.x = node_x
    node_trace.y = node_y
    node_trace.text = node_text
    
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Initialize session state
if 'show_graph' not in st.session_state:
    st.session_state.show_graph = False

# Main application
st.title('PDF Knowledge Graph Generator')
st.write("Upload a PDF file to extract its table of contents and generate a knowledge graph.")

# File uploader
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Create temporary files
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as pdf_temp:
        pdf_temp.write(uploaded_file.getvalue())
        pdf_path = pdf_temp.name
    
    # Extract TOC
    extractor = PDFTOCExtractor(uploaded_file)
    built_in_toc, text_toc = extractor.get_all_tocs()

    if built_in_toc or text_toc:
        st.header("Table of Contents")
        
        # TOC Selection
        selected_toc = None
        if built_in_toc and text_toc:
            st.subheader("Multiple TOCs Found")
            toc_choice = st.selectbox(
                "Select the TOC to use", 
                ["Built-in TOC", "Extracted TOC"]
            )
            selected_toc = built_in_toc if toc_choice == "Built-in TOC" else text_toc
        else:
            selected_toc = built_in_toc if built_in_toc else text_toc
        
        if selected_toc:
            st.subheader("Selected TOC")
            
            # Initialize session state for TOC display
            if 'show_all' not in st.session_state:
                st.session_state.show_all = False
            if 'all_items' not in st.session_state:
                st.session_state.all_items = selected_toc.copy()
            
            # Toggle button for showing all items
            if st.button("Toggle Full TOC"):
                st.session_state.show_all = not st.session_state.show_all
            
            # Display TOC items
            display_items = (st.session_state.all_items 
                           if st.session_state.show_all 
                           else st.session_state.all_items[:5])
            
            items_to_remove = []
            for i, item in enumerate(display_items):
                title = clean_title(item['title'])
                if title:
                    display_text = f"{title} .... {item['page']}"
                    checkbox = st.checkbox(display_text, key=f"toc_item_{i}")
                    if checkbox:
                        items_to_remove.append(item)
            
            # Delete selected items
            if items_to_remove and st.button("Delete Selected Items"):
                st.session_state.all_items = [
                    item for item in st.session_state.all_items 
                    if item not in items_to_remove
                ]
                st.rerun()
            
            # Save TOC to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as toc_temp:
                for item in st.session_state.all_items:
                    title = clean_title(item['title'])
                    if title:
                        toc_temp.write(f"{title} .... {item['page']}\n")
                toc_path = toc_temp.name
            
            # Process button
            if st.button("Generate Knowledge Graph"):
                with st.spinner("Processing... This may take a few minutes."):
                    try:
                        # Process TOC and create DataFrame
                        df = read_toc_file(toc_path, pdf_path)
                        if df is not None:
                            # Filter short content
                            df = df[df['Content'].str.split().str.len() >= 50]
                            
                            # Save temporary CSV
                            csv_path = os.path.join(tempfile.gettempdir(), "temp_content.csv")
                            df.to_csv(csv_path, index=False)
                            
                            # Send to ngrok server
                            NGROK_URL = "2q2Talb1F4DdZMIBWywoqxqVTGR_2V4LEaUkEALEVNnPF52HX"  
                            
                            with open(csv_path, 'rb') as f:
                                files = {'csv_file': f}
                                response = requests.post(
                                    f"{NGROK_URL}/process_knowledge_graph",
                                    files=files
                                )
                            
                            if response.status_code == 200:
                                result = response.json()
                                if result['status'] == 'success':
                                    # Create and display graph
                                    relationships_df = pd.DataFrame(result['relationships'])
                                    
                                    st.subheader("Knowledge Graph")
                                    display_knowledge_graph(relationships_df)
                                    
                                    # Save results
                                    output_filename = f"{uploaded_file.name}_knowledge_graph.csv"
                                    relationships_df.to_csv(output_filename, index=False)
                                    
                                    # Download button
                                    with open(output_filename, 'r') as f:
                                        st.download_button(
                                            "Download Knowledge Graph Data",
                                            f.read(),
                                            file_name=output_filename,
                                            mime="text/csv"
                                        )
                                else:
                                    st.error("Failed to process knowledge graph")
                            else:
                                st.error("Error connecting to processing server")
                    
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                    
                    finally:
                        # Cleanup temporary files
                        for path in [csv_path, toc_path, pdf_path]:
                            try:
                                if os.path.exists(path):
                                    os.unlink(path)
                            except Exception:
                                pass
            
            # Download TOC button
            toc_content = "\n".join([
                f"{clean_title(item['title'])} .... {item['page']}"
                for item in st.session_state.all_items
                if clean_title(item['title'])
            ])
            st.download_button(
                "Download TOC",
                toc_content,
                file_name=f"{uploaded_file.name}_toc.txt",
                mime="text/plain"
            )
    
    else:
        st.error("No table of contents found in the document.")

# Footer
st.markdown("---")
st.markdown(
    "This tool extracts the table of contents from PDF files and generates "
    "a knowledge graph showing the relationships between topics."
) 