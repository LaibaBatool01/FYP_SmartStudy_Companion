import streamlit as st
import json
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import tempfile
import os
from pathlib import Path
from chatbot_api import ask_chatbot

def load_prerequisites(file_path):
    """Load prerequisites from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading prerequisites file: {e}")
        return {}

def create_graph(prerequisites):
    """Create a directed graph from prerequisites data."""
    G = nx.DiGraph()
    
    # Add all topics as nodes
    for topic in prerequisites.keys():
        G.add_node(topic)
    
    # Add edges based on prerequisites
    for topic, prereqs in prerequisites.items():
        for prereq in prereqs:
            G.add_edge(prereq, topic)
    
    return G

def create_tree_visualization(prerequisites, highlight_topic=None, highlight_hard_correct=False):
    """
    Create the HTML content for the tree visualization
    
    Args:
        prerequisites: Dictionary of topic prerequisites
        highlight_topic: Optional topic to highlight
        highlight_hard_correct: Whether the topic has been completed with hard question correct
        
    Returns:
        str: HTML content for the visualization
    """
    st.header("Hierarchical Tree Visualization")
    
    # Get user's learned topics from session state
    learned_topics = []
    if 'learned_topics' in st.session_state:
        learned_topics = st.session_state.learned_topics
    
    # Add search functionality at the top
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_topic = st.text_input("Search for a specific topic:", 
                                     value=highlight_topic if highlight_topic else "",
                                     placeholder="Enter a topic name...",
                                     key="topic_search_input")  # Added unique key
    with search_col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    # Create graph
    G = create_graph(prerequisites)
    
    # Calculate fixed positions for all nodes - this ensures graph stability
    positions = {}
    for i, node in enumerate(G.nodes()):
        # Position nodes in a grid layout with some randomization based on node name
        # Using hash of node name ensures the same node always gets the same position
        node_hash = hash(node) % 1000
        level = len(list(G.predecessors(node)))  # Use node level in hierarchy
        row = level * 250
        col = (i * 300 + node_hash) % 3000  # Distribute horizontally with some deterministic variation
        positions[node] = (col, row)
    
    # Process search if requested
    topic_found = False
    searched_node = None
    
    # First check for highlights from quiz
    if highlight_topic and highlight_topic in G.nodes():
        searched_node = highlight_topic
        topic_found = True
    # Then check for manual search
    elif search_button and search_topic:
        # Normalize search term for case-insensitive search
        search_term = search_topic.lower().strip()
        # Look for exact or partial matches
        for node in G.nodes():
            if search_term == node.lower() or search_term in node.lower():
                searched_node = node
                topic_found = True
                break
        
        if not topic_found:
            st.error(f"Topic '{search_topic}' not found in the prerequisites graph.")
    
    # Create interactive visualization with pyvis
    net = Network(height="800px", width="100%", directed=True, notebook=False)
    
    # Set network options
    net.options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",
                "sortMethod": "directed",
                "nodeSpacing": 300,
                "levelSeparation": 250,
                "treeSpacing": 300
            },
            "improvedLayout": True,
            "randomSeed": 42
        },
        "physics": {
            "enabled": False,
            "hierarchicalRepulsion": {
                "centralGravity": 0,
                "springLength": 155,
                "springConstant": 0.01,
                "nodeDistance": 180,
                "damping": 0.09
            },
            "solver": "hierarchicalRepulsion",
            "stabilization": {
                "enabled": True,
                "iterations": 1000,
                "updateInterval": 100,
                "onlyDynamicEdges": False,
                "fit": True
            }
        },
        "interaction": {
            "navigationButtons": True,
            "keyboard": True,
            "hover": True,
            "zoomView": False,
            "tooltipDelay": 100,
            "hideEdgesOnDrag": True,
            "dragNodes": False,
            "dragView": False,
            "selectable": True,
            "selectConnectedEdges": True,
            "hoverConnectedEdges": True
        },
        "nodes": {
            "shape": "box",
            "margin": 15,
            "widthConstraint": {
                "maximum": 200
            },
            "font": {
                "color": "white",
                "size": 18,
                "face": "Arial",
                "bold": True
            },
            "shadow": {
                "enabled": True
            }
        },
        "edges": {
            "color": {
                "color": "#999999"
            },
            "width": 2,
            "smooth": {
                "enabled": True,
                "type": "curvedCW"
            },
            "arrows": {
                "to": {
                    "enabled": True,
                    "scaleFactor": 1
                }
            }
        }
    }
    
    # Function to abbreviate long labels
    def abbreviate_label(label):
        # Specific abbreviations for common long topics
        abbreviations = {
            "Dynamic Memory Allocation": "Dynamic Memory",
            "Multi-dimensional Arrays": "Multi-dim Arrays",
            "String Manipulation": "String Manip",
            "Abstract Classes": "Abstract Classes",
            "Friend Functions": "Friend Functions",
            "Operator Overloading": "Operator Overload",
            "Exception Handling": "Exception Handling",
            "Function Parameters": "Function Params",
            "Function Overloading": "Function Overload",
            "Default Arguments": "Default Args",
            "Inline Functions": "Inline Functions",
            "Static Members": "Static Members",
            "Move Semantics": "Move Semantics",
            "Smart Pointers": "Smart Pointers",
            "Lambda Expressions": "Lambda Expr",
            "Rvalue References": "Rvalue Refs"
        }
        
        return abbreviations.get(label, label)
    
    # Get root nodes and terminal nodes for special styling
    root_nodes = [node for node in G.nodes() if not list(G.predecessors(node))]
    terminal_nodes = [node for node in G.nodes() if not list(G.successors(node))]
    
    # Get list of topics to highlight based on user's learned topics and quiz results
    highlight_nodes = []
    
    if highlight_topic and highlight_topic in learned_topics:
        if highlight_hard_correct:
            # If Hard question is correct: Highlight ALL selected topics INCLUDING quiz topic
            highlight_nodes = learned_topics.copy()
        else:
            # If Medium/Easy questions are correct: Highlight selected topics EXCEPT quiz topic
            highlight_nodes = [topic for topic in learned_topics if topic != highlight_topic]
    
    # Get connected nodes for the searched topic
    connected_nodes = []
    if topic_found and searched_node:
        connected_nodes = list(G.predecessors(searched_node)) + list(G.successors(searched_node))
        connected_nodes.append(searched_node)  # Include the searched node itself
        
    # If search found a node, get its connected nodes for display
    if topic_found:
        # Create a subgraph with only the connected nodes
        sub_G = G.subgraph(connected_nodes)
        nodes_to_display = list(sub_G.nodes())
        edges_to_display = list(sub_G.edges())
        
        if highlight_topic:
            st.success(f"Showing topic '{searched_node}' and its connections")
        else:
            st.success(f"Found topic: '{searched_node}' - Showing only connected topics")
    else:
        # Display all nodes if no search or search not found
        nodes_to_display = list(G.nodes())
        edges_to_display = list(G.edges())
    
    # Function to determine if a color is light (needs dark text)
    def is_light_color(color_hex):
        # Skip check for non-hex colors
        if not color_hex.startswith('#'):
            return False
            
        # Remove # prefix and standardize to 6 characters
        color_hex = color_hex.lstrip('#')
        # Handle shorthand hex (e.g., #fff -> #ffffff)
        if len(color_hex) == 3:
            color_hex = ''.join([c*2 for c in color_hex])
            
        # Convert to RGB values
        try:
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
            
            # Calculate perceived brightness using common formula
            # This accounts for human perception of different colors
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            
            # Return true if color is light (brightness > 155)
            return brightness > 155
        except ValueError:
            return False
    
    # Add nodes with proper color scheme
    for node in nodes_to_display:
        # Get abbreviated label
        label = abbreviate_label(node)
        
        # NEW GREEN AND RED COLOR SCHEME
        if node in highlight_nodes and node in learned_topics:
            # Selected topics and Hard quiz correct topics - DARK GREEN
            color = "#1B5E20"  # Dark green for selected topics + hard quiz
            border_color = "#003300"
            border_width = 5
            size = 50
            node_type = "completed"  # Track node type for popup
        elif (node == highlight_topic and not highlight_hard_correct and node in learned_topics) or node in connected_nodes:
            # Medium/Easy quiz topics and topics connected to selected topics - MEDIUM GREEN
            color = "#2E7D32"  # Medium green for quiz topic (medium/easy) and connected topics
            border_color = "#1B5E20"
            border_width = 4
            size = 45
            node_type = "ready"  # Track node type for popup
        elif node in learned_topics:
            # Any other learned topics - LIGHT GREEN
            color = "#4CAF50"  # Light green for general learned topics
            border_color = "#2E7D32"
            border_width = 3
            size = 40
            node_type = "learned"  # Track node type for popup
        elif node in root_nodes:
            # Root/foundation nodes - LIGHT RED
            color = "#EF5350"  # Light red for foundation nodes (same as non-connected)
            border_color = "#C62828"
            border_width = 2
            size = 35
            node_type = "prerequisites"  # Track node type for popup
        elif node in terminal_nodes:
            # Terminal/advanced nodes - DARKER RED
            color = "#C62828"  # Darker red for advanced nodes
            border_color = "#B71C1C"
            border_width = 2
            size = 35
            node_type = "prerequisites"  # Track node type for popup
        else:
            # All other non-learned nodes - MEDIUM RED
            color = "#E53935"  # Medium red for non-connected, non-learned topics
            border_color = "#C62828"
            border_width = 2
            size = 35
            node_type = "prerequisites"  # Track node type for popup
            
        # Determine if this color needs dark text
        use_dark_text = is_light_color(color) or color.lower() == "yellow"
        
        # Add node with proper styling
        net.add_node(
            node,  # This is the node ID as the first positional argument
            label=label,
            color=color,
            border_color=border_color,
            border_width=border_width,
            shape="box",
            font={"color": "black" if use_dark_text else "red", 
                  "size": 18, 
                  "face": "Arial", 
                  "bold": True},
            shadow=True,
            size=size,
            title=f"Topic: {node}",  # Show full topic name on hover
            group=node_type,  # Use group to track node type for popup
            fixed=True,  # Fix the node position
            x=positions[node][0],  # Set x coordinate from our positions
            y=positions[node][1]   # Set y coordinate from our positions
        )
    
    # Add edges
    for edge in edges_to_display:
        net.add_edge(
            edge[0], 
            edge[1], 
            color="#999999", 
            width=2, 
            smooth={"enabled": True, "type": "curvedCW"},
            arrows={"to": {"enabled": True}}
        )
        
        # Generate HTML file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
            path = Path(temp_file.name)
            net.save_graph(str(path))
        
        # Display the graph
        with open(path, 'r', encoding='utf-8') as f:
            html_data = f.read()
        
    # Update the JavaScript for proper Streamlit communication
    custom_js = """
    <script type="text/javascript">
      // Define a function to handle node clicks
      function handleNodeClick(nodeId, nodeLabel, nodeTitle) {
        // Get the topic name from node title or label
        var topicName = nodeTitle ? nodeTitle.replace("Topic: ", "") : nodeLabel;
        
        // Format a question about this topic
        var question = "Explain " + topicName + " in C++ and also provide code examples";
        
        // Use window.parent to reach the Streamlit app frame
        window.parent.postMessage({
          type: "streamlit:setComponentValue",
          value: {
            type: "redirect_to_chatbot",
            topic: topicName,
            question: question
          }
        }, "*");
      }
      
      // Wait for the document and vis.js to load
      document.addEventListener("DOMContentLoaded", function() {
        setTimeout(function() {
          try {
            // Look for network container
            var networkContainer = document.querySelector(".vis-network");
            if (!networkContainer) {
              console.error("Network container not found");
              return;
            }
            
            // Find the network instance - this is tricky, it might be in different places
            // Try window.network first
            var networkInstance = null;
            
            // Option 1: Direct window.network reference (sometimes available)
            if (window.network) {
              networkInstance = window.network;
              console.log("Found network in window.network");
            } 
            // Option 2: Look for vis.Network instance attached to the container
            else {
              // This is a fallback approach if the first one doesn't work
              networkInstance = networkContainer.__vis_network__;
              console.log("Looking for network in container");
            }
            
            if (!networkInstance) {
              console.error("Could not find network instance");
              return;
            }
            
            console.log("Network instance found, attaching click handler");
            
            // Add click handler for nodes
            networkInstance.on("click", function(params) {
              if (params.nodes && params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                console.log("Clicked node ID:", nodeId);
                
                // Get node data
                var node = networkInstance.body.data.nodes.get(nodeId);
                if (!node) {
                  console.error("Could not find node data");
                  return;
                }
                
                console.log("Node data:", node);
                
                // Call our handler function
                handleNodeClick(nodeId, node.label, node.title);
              }
            });
            
            console.log("Click handler attached successfully");
          } catch (e) {
            console.error("Error setting up network click handler:", e);
          }
        }, 1000);  // Wait for network to be fully initialized
      });
    </script>
    """
    
    # Add custom CSS for better appearance
    custom_css = """
    <style>
        .vis-network {
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            background-color: #f9f9f9;
            position: relative;
        }
        /* Force yellow nodes to be red */
        .vis-network .vis-node {
            background-color: #E53935 !important;
            border-color: #C62828 !important;
        }
        /* Override specific network colors - make yellows red */
        [style*="fill: yellow"] {
            fill: #E53935 !important;
        }
        [style*="stroke: yellow"] {
            stroke: #C62828 !important;
        }
        [style*="background-color: yellow"] {
            background-color: #E53935 !important;
        }
        [style*="border-color: yellow"] {
            border-color: #C62828 !important;
        }
        .node-popup {
            font-family: Arial, sans-serif;
        }
        .node-popup h3 {
            color: #333;
            margin-bottom: 10px;
        }
        .node-popup p {
            margin-bottom: 15px;
        }
        .node-popup button:hover {
            opacity: 0.9;
        }
    </style>
    """
    
    # Add a JavaScript snippet to force color refresh
    color_reset_js = """
    <script>
    // Function to force color refresh
    function forceColorRefresh() {
        // Find all yellow nodes and convert them to red
        const yellowNodes = document.querySelectorAll('[style*="fill: yellow"], [style*="stroke: yellow"], [style*="background-color: yellow"], [style*="border-color: yellow"]');
        yellowNodes.forEach(node => {
            let style = node.getAttribute('style');
            if (style) {
                // Replace yellow with red
                style = style.replace(/yellow/g, '#E53935');
                style = style.replace(/#FFFF00/gi, '#E53935');
                style = style.replace(/#FF0/gi, '#E53935');
                node.setAttribute('style', style);
            }
        });
    }
    
    // Run color refresh after page loads and after any updates
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(forceColorRefresh, 1000);
        // Also try refreshing repeatedly for a few seconds to catch any late-rendered elements
        for (let i = 2; i < 10; i++) {
            setTimeout(forceColorRefresh, i * 1000);
        }
    });
    </script>
    """
    
    # Make sure our network div has an ID for the JavaScript to reference
    html_data = html_data.replace('<div id="mynetwork"></div>', 
                                 '<div id="mynetwork" style="width:100%; height:800px;"></div>')
    
    # Add more CSS styles for the topic selection area
    topic_selection_css = """
    <style>
        /* Topic Selection Card */
        .topic-selection-card {
            background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
            border-radius: 15px;
            padding: 20px 25px;
            margin: 25px 0 15px 0;
            box-shadow: 0 6px 18px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.3);
            transition: all 0.3s ease;
        }
        
        .topic-selection-card:hover {
            box-shadow: 0 8px 25px rgba(33, 150, 243, 0.15);
            transform: translateY(-2px);
        }
        
        /* Card Title */
        .selection-title {
            font-size: 1.2rem;
            font-weight: 700;
            background: linear-gradient(90deg, #1565C0, #64B5F6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-fill-color: transparent;
            margin-bottom: 15px;
            text-align: center;
            letter-spacing: 0.5px;
        }
        
        /* Select Box Styling */
        .stSelectbox > div > div {
            background-color: white !important;
            border-radius: 10px !important;
            border: 2px solid #E0E0E0 !important;
            padding: 5px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
            transition: all 0.3s ease !important;
        }
        
        .stSelectbox > div > div:hover {
            border-color: #2196F3 !important;
            box-shadow: 0 4px 12px rgba(33, 150, 243, 0.1) !important;
        }
        
        /* Button Styling */
        .topic-btn {
            background: linear-gradient(135deg, #1976D2, #42A5F5) !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 10px 16px !important;
            border-radius: 10px !important;
            border: none !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
            transition: all 0.3s ease !important;
            height: 3em !important;
            margin-top: 10px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        .topic-btn:hover {
            background: linear-gradient(135deg, #1565C0, #1976D2) !important;
            box-shadow: 0 8px 15px rgba(33, 150, 243, 0.3) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }
        
        /* Icon styling */
        .icon-text {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .topic-selection-card {
                padding: 15px;
            }
            
            .selection-title {
                font-size: 1rem;
            }
        }
    </style>
    """
    
    # Combine all CSS and JavaScript
    combined_css = custom_css + topic_selection_css + color_reset_js
    
    # Display with custom CSS and JS
    from streamlit.components.v1 import html as st_html
    html_component = st_html(combined_css + html_data + custom_js, height=850, scrolling=True)
    
    # Clean up the temporary file
    try:
        os.unlink(path)
    except:
        pass
    
    # After displaying the visualization, add beautiful topic selection card
    st.markdown("""
    <div class="topic-selection-card">
        <div class="selection-title">🔍 Explore Programming Topics</div>
        <p style="text-align: center; color: #1976D2; margin-bottom: 15px; font-size: 0.9rem;">
           Select any topic to get detailed explanations with code examples
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create columns for topic selection with better spacing
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get all topics
        all_topics = list(prerequisites.keys())
        
        # Filter topics based on sub-graph and learning status
        topics_to_show = []
        
        # If we're showing a sub-graph, only show topics from that sub-graph
        if topic_found:
            # Filter to show only topics in the current sub-graph that haven't been learned
            for topic in nodes_to_display:
                if topic not in learned_topics:
                    topics_to_show.append(topic)
        else:
            # If showing full graph, show all not learned topics
            for topic in all_topics:
                if topic not in learned_topics:
                    topics_to_show.append(topic)
        
        # If all filtered topics are learned or no topics match, show all topics from the current view
        if not topics_to_show:
            if topic_found:
                topics_to_show = nodes_to_display
            else:
                topics_to_show = all_topics
        
        # Sort the topics alphabetically for easier navigation
        topics_to_show.sort()
        
        # Try to set a reasonable default index
        default_index = 0
        # Look for basic topics first
        for basic_topic in ["Basic Syntax", "Variables", "Data Types", "Constants"]:
            if basic_topic in topics_to_show:
                default_index = topics_to_show.index(basic_topic)
                break
        
        selected_topic = st.selectbox(
            "Choose a topic to learn next:", 
            topics_to_show,
            index=default_index,
            key="enhanced_topic_selector"
        )
    
    with col2:
        # Create a modern button with icon
        ask_button = st.button(
            "🚀 Explore This Topic", 
            key="ask_topic_btn", 
            use_container_width=True
        )
        
        # Add custom styling to the button
        st.markdown("""
        <style>
            [data-testid="stButton"] > button {
                background: linear-gradient(135deg, #1976D2, #42A5F5) !important;
                color: white !important;
                font-weight: 600 !important;
                padding: 0.6rem 1rem !important;
                border-radius: 10px !important;
                border: none !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
                transition: all 0.3s ease !important;
            }
            
            [data-testid="stButton"] > button:hover {
                background: linear-gradient(135deg, #1565C0, #1976D2) !important;
                box-shadow: 0 8px 15px rgba(33, 150, 243, 0.3) !important;
                transform: translateY(-3px) scale(1.02) !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        if ask_button:
            # Generate question
            question = f"What is {selected_topic} in C++ and explain with code"
            
            # Store data for chatbot page
            st.session_state.current_page = "chatbot"
            st.session_state.pending_topic = selected_topic
            st.session_state.pending_question = question
            
            # Add to chat history
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Only add if it's not already the last message
            if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != question:
                st.session_state.chat_history.append({"role": "user", "content": question})
            
            # Get response from chatbot API immediately
            try:
                response = ask_chatbot(question)
                
                # Add bot response to chat history
                st.session_state.chat_history.append({"role": "bot", "content": response})
            except Exception as e:
                st.error(f"Error getting chatbot response: {e}")
            
            # Force navigation to chatbot page
            st.rerun()
    
    # Return the component value from the visualization (even though we're not using it)
    return html_component

def handle_node_click(value):
    """Handle node click events from the visualization."""
    if not value:
        return
        
    # New handler for direct chatbot redirect
    if value.get("type") == "redirect_to_chatbot":
        topic = value.get("topic")
        question = value.get("question")
        
        # Store the question in session state for the chatbot
        if topic and question:
            st.session_state.current_page = "chatbot"
            
            # Initialize chat_message if not present
            if "chat_message" not in st.session_state:
                st.session_state.chat_message = question
            else:
                # Set up for clearing on next rerun
                st.session_state.clear_input = True
                st.session_state.pending_question = question
                
            # Add to chat history immediately so it's ready when page loads
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
                
            # Add the question to chat history
            st.session_state.chat_history.append({"role": "user", "content": question})
            
            # Force a rerun to navigate to the chatbot page
            st.rerun()

def visualize_prerequisites():
    """
    Visualize topic prerequisites as a network graph
    """
    # Get data from session state if available
    highlight_topic = st.session_state.get('highlight_topic', None)
    highlight_hard_correct = st.session_state.get('highlight_hard_correct', False)
    
    # Load prerequisites
    try:
        with open('cpp-prerequisites-json.json', 'r') as f:
            prerequisites = json.load(f)
    except Exception as e:
        st.error(f"Error loading prerequisites: {e}")
        return
    
    # Add a callback to capture component events
    if "component_value" not in st.session_state:
        st.session_state.component_value = None
    
    # Create the visualization
    create_tree_visualization(prerequisites, highlight_topic, highlight_hard_correct)
    
    # Check if we have a component value from a previous interaction
    if st.session_state.component_value:
        component_value = st.session_state.component_value
        # Clear it to avoid processing twice
        st.session_state.component_value = None
        
        st.write(f"Debug - Component value received: {component_value}")
        
        if isinstance(component_value, dict) and component_value.get("type") == "redirect_to_chatbot":
            topic = component_value.get("topic")
            question = component_value.get("question")
            
            st.write(f"Debug - Redirecting to chatbot with topic: {topic}")
            st.write(f"Debug - Question: {question}")
            
            # Store data for the chatbot page
            st.session_state.current_page = "chatbot"
            st.session_state.pending_topic = topic
            st.session_state.pending_question = question
            
            # Add to chat history
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # Only add if it's not already the last message
            if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != question:
                st.session_state.chat_history.append({"role": "user", "content": question})
            
            # Get response from chatbot API immediately
            response = ask_chatbot(question)
            
            # Add bot response to chat history
            st.session_state.chat_history.append({"role": "bot", "content": response})
            
            # Force navigation to chatbot page
            st.rerun()

if __name__ == "__main__":
    visualize_prerequisites()
