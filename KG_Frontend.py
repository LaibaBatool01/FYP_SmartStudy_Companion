import streamlit as st
import networkx as nx
from pyvis.network import Network
import pandas as pd
import json
import streamlit.components.v1 as components

# Read prerequisites data from CSV
programming_prereqs = pd.read_csv('FULLprerequisites_graph1.csv', header=None, names=['Prerequisite', 'Topic'], skiprows=1)

def generate_graph_data():
    # Convert CSV data to nodes and edges format
    nodes = []
    node_id = 1
    node_mapping = {}
    
    # Get unique nodes from prerequisites and topics
    unique_nodes = set(programming_prereqs['Prerequisite']) | set(programming_prereqs['Topic'])
    
    for node in unique_nodes:
        nodes.append({
            "id": node_id,
            "label": node,
            "title": node  # Add hover tooltip
        })
        node_mapping[node] = node_id
        node_id += 1
    
    # Create edges from prerequisites data
    edges = []
    for i in range(len(programming_prereqs['Prerequisite'])):
        edges.append({
            "from": node_mapping[programming_prereqs['Prerequisite'][i]], # Prerequisite points to Topic
            "to": node_mapping[programming_prereqs['Topic'][i]], # Arrow head on Topic
            "weight": 1,
            "title": f"{programming_prereqs['Prerequisite'][i]} → {programming_prereqs['Topic'][i]}"
        })
    
    return nodes, edges

def create_force_graph(nodes, edges, height=500):
    # Initialize network
    net = Network(height=f"{height}px", width="100%", bgcolor="#ffffff", font_color="black")
    
    # Add nodes and edges
    for node in nodes:
        net.add_node(node["id"], 
                    label=node["label"],
                    title=node["title"],
                    color="#97C2FC",  # Light blue color
                    shape="dot")
    
    for edge in edges:
        net.add_edge(edge["from"], edge["to"], 
                    value=edge["weight"], 
                    title=edge["title"],
                    arrows="to")
    
    # Set options for better visualization with node overlap prevention
    net.set_options('''
    {
        "physics": {
            "enabled": true,
            "stabilization": {
                "enabled": true,
                "iterations": 300,
                "updateInterval": 10,
                "fit": true
            },
            "barnesHut": {
                "gravitationalConstant": -50000,
                "centralGravity": 0.001,
                "springLength": 3000,
                "springConstant": 0.001,
                "damping": 0.09,
                "avoidOverlap": 15
            },
            "maxVelocity": 15,
            "minVelocity": 0.1,
            "solver": "barnesHut"
        },
        "nodes": {
            "font": {
                "size": 40,
                "face": "arial",
                "color": "black",
                "bold": true,
                "strokeWidth": 8,
                "strokeColor": "#ffffff",
                "multi": true,
                "align": "center"
            },
            "size": 150,
            "borderWidth": 6,
            "shape": "box",
            "margin": 40,
            "widthConstraint": {
                "minimum": 300,
                "maximum": 500
            },
            "color": {
                "background": "#97C2FC",
                "border": "#2B7CE9",
                "highlight": {
                    "background": "#ff0000",
                    "border": "#ff0000"
                }
            }
        },
        "edges": {
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 3
                }
            },
            "color": {
                "color": "#2B7CE9",
                "highlight": "#ff0000"
            },
            "width": 5,
            "smooth": {
                "enabled": true,
                "type": "curvedCW",
                "roundness": 0.2
            },
            "length": 3000
        },
        "layout": {
            "improvedLayout": true,
            "hierarchical": {
                "enabled": false,
                "levelSeparation": 3000,
                "nodeSpacing": 2000,
                "blockShifting": true,
                "edgeMinimization": true,
                "direction": "UD"
            }
        },
        "interaction": {
            "dragNodes": true,
            "dragView": true,
            "hover": true,
            "navigationButtons": true,
            "keyboard": true,
            "multiselect": true,
            "selectable": true,
            "selectConnectedEdges": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "zoomSpeed": 1
        },
        "manipulation": {
            "enabled": true,
            "initiallyActive": true,
            "addNode": true,
            "addEdge": true,
            "editNode": true,
            "editEdge": true,
            "deleteNode": true,
            "deleteEdge": true
        }
    }
    ''')
    
    # Add stabilization and manipulation handlers
    net.html = net.html.replace('</script>', '''
        // Enable manipulation toolbar
        network.on("stabilizationIterationsDone", function() {
            network.setOptions({ physics: { enabled: false } });
            console.log("Stabilization finished");
        });

        // Add double-click to edit node labels
        network.on("doubleClick", function(params) {
            if (params.nodes.length === 1) {
                var nodeId = params.nodes[0];
                var node = network.body.data.nodes.get(nodeId);
                var newLabel = prompt("Enter new label:", node.label);
                if (newLabel !== null) {
                    network.body.data.nodes.update({id: nodeId, label: newLabel});
                }
            }
        });

        // Add keyboard controls
        document.addEventListener("keydown", function(event) {
            switch(event.key) {
                case "ArrowUp":
                    network.moveTo({offset: {y: 100}}); break;
                case "ArrowDown":
                    network.moveTo({offset: {y: -100}}); break;
                case "ArrowLeft":
                    network.moveTo({offset: {x: 100}}); break;
                case "ArrowRight":
                    network.moveTo({offset: {x: -100}}); break;
                case "+":
                    network.moveTo({scale: network.getScale() * 1.2}); break;
                case "-":
                    network.moveTo({scale: network.getScale() * 0.8}); break;
            }
        });

        // Add node selection handler
        network.on("selectNode", function(params) {
            if (params.nodes.length > 0) {
                var selectedNodeId = params.nodes[0];
                
                // Update nodes
                var nodeUpdates = [];
                var nodes = network.body.data.nodes.get();
                nodes.forEach(function(node) {
                    if (node.id === selectedNodeId) {
                        nodeUpdates.push({
                            id: node.id,
                            color: {background: '#ff0000', border: '#ff0000'}
                        });
                    } else {
                        nodeUpdates.push({
                            id: node.id,
                            color: {background: '#97C2FC', border: '#2B7CE9'}
                        });
                    }
                });
                network.body.data.nodes.update(nodeUpdates);
                
                // Update edges
                var edgeUpdates = [];
                var edges = network.body.data.edges.get();
                edges.forEach(function(edge) {
                    if (edge.from === selectedNodeId || edge.to === selectedNodeId) {
                        edgeUpdates.push({
                            id: edge.id,
                            color: {color: '#ff0000', highlight: '#ff0000'}
                        });
                    } else {
                        edgeUpdates.push({
                            id: edge.id,
                            color: {color: '#2B7CE9', highlight: '#1B4C89'}
                        });
                    }
                });
                network.body.data.edges.update(edgeUpdates);
            }
        });

        // Add deselection handler
        network.on("deselectNode", function(params) {
            // Reset nodes
            var nodes = network.body.data.nodes.get();
            nodes.forEach(function(node) {
                network.body.data.nodes.update({
                    id: node.id,
                    color: {background: '#97C2FC', border: '#2B7CE9'}
                });
            });
            
            // Reset edges
            var edges = network.body.data.edges.get();
            edges.forEach(function(edge) {
                network.body.data.edges.update({
                    id: edge.id,
                    color: {color: '#2B7CE9', highlight: '#1B4C89'}
                });
            });
        });
        </script>
    ''')
    
    # Add custom JavaScript with error handling
    net.html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <title>Network</title>
            <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <link href="https://unpkg.com/vis-network/styles/vis-network.min.css" rel="stylesheet" type="text/css" />
            <style type="text/css">
                #mynetwork {{
                    border: 2px solid lightgray;
                    background: #ffffff;
                }}
            </style>
        </head>
        <body>
            <div id="mynetwork"></div>
            <script type="text/javascript">
                try {{
                    var container = document.getElementById('mynetwork');
                    var network = new vis.Network(container, data, options);
                    
                    network.on("stabilizationProgress", function(params) {{
                        console.log("Stabilization progress:", params.iterations, "/", params.total);
                    }});
                    
                    network.on("stabilizationIterationsDone", function() {{
                        console.log("Stabilization finished");
                        network.setOptions({{ physics: false }});  // Disable physics after stabilization
                    }});
                    
                    network.on("manipulationEditNode", function(params) {{
                        var name = prompt("Enter node name:");
                        if (name) {{
                            params.node.label = name;
                            params.node.title = name;
                            network.body.data.nodes.update(params.node);
                        }}
                    }});
                    
                    network.on("beforeDrawing", function(ctx) {{
                        var edges = network.body.data.edges.get();
                        edges.forEach(function(edge) {{
                            if (edge.from === edge.to) {{
                                network.body.data.edges.remove(edge.id);
                            }}
                        }});
                    }});
                }} catch (error) {{
                    console.error("Error initializing network:", error);
                    document.getElementById('mynetwork').innerHTML = 
                        "An error occurred while loading the graph. Please check the console for details.";
                }}
            </script>
        </body>
    </html>
    """
    
    # Save and return HTML
    net.save_graph("temp_graph.html")
    with open("temp_graph.html", "r", encoding="utf-8") as f:
        html = f.read()
    return html

def main():
    st.title("Programming Prerequisites Knowledge Graph")
    
    try:
        # Generate graph data from CSV
        nodes, edges = generate_graph_data()
        
        # Graph height control
        height = st.sidebar.slider("Graph height", 600, 1000, 800)
        
        # Display graph
        html = create_force_graph(nodes, edges, height)
        components.html(html, height=height)
        
        # Display data tables
        with st.expander("View Data Tables"):
            st.subheader("Prerequisites Data")
            st.dataframe(programming_prereqs)
            
            st.subheader("Nodes Data")
            st.dataframe(pd.DataFrame(nodes))
            
            st.subheader("Edges Data")
            st.dataframe(pd.DataFrame(edges))
        
        # Add help section
        with st.expander("Help & Instructions"):
            st.markdown("""
            ### How to use this graph:
            - **Zoom**: Use mouse wheel or pinch gesture
            - **Pan**: Click and drag on empty space
            - **Move nodes**: Click and drag nodes
            - **Delete nodes**: Click on a node to delete it
            - **View node/edge details**: Hover over elements
            - **Add node**: Click the add node button and enter name
            - **Add edge**: Click the add edge button and connect two different nodes
            
            ### Troubleshooting:
            If you encounter any errors:
            1. Check your browser's console (F12) for detailed error messages
            2. Click the Copilot icon in Edge browser to explain console errors
            3. Ensure all dependencies are properly loaded
            4. Try refreshing the page
            5. Clear browser cache if issues persist
            """)
    except Exception as e:
        st.error(f"An error occurred while rendering the graph: {str(e)}")

if __name__ == "__main__":
    main()