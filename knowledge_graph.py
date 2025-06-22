import pandas as pd
import json
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
import torch
from concurrent.futures import ThreadPoolExecutor
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    def __init__(self, model_name: str = "mistral"):
        """Initialize the knowledge graph builder with improved validation"""
        self.llm = Ollama(
            model=model_name,
            temperature=0.0,
        )

        # Updated prompt to focus on immediate prerequisites and technical specificity
        self.prompt_template = PromptTemplate(
            input_variables=["topic", "content", "all_topics"],
            template="""Analyze this programming content and identify the most immediate and specific prerequisites needed to understand this topic.

            Topic: {topic}
            Content: {content}
            Available Topics: {all_topics}

            Rules:
            1. Focus ONLY on the MOST IMMEDIATE prerequisites (2-3 max) that are directly needed for this specific topic
            2. Prerequisites must be:
               - Directly related to understanding this topic
               - At the appropriate complexity level (not too basic, not too advanced)
               - Technical and specific (avoid general concepts)
            3. Consider the natural learning progression:
               - Each prerequisite should be one level below the current topic
               - Focus on technical dependencies, not chapter organization
            4. DO NOT include:
               - Very basic concepts unless absolutely necessary
               - General programming concepts
               - Indirect or distantly related topics
               - Chapter numbers or section references

            Respond ONLY with this JSON format:
            {{"prerequisites": ["specific_prerequisite_1", "specific_prerequisite_2", "specific_prerequisite_3"]}}
            """)

        # Initialize the chain
        self.chain = self.prompt_template | self.llm

        # Expanded invalid patterns for general technical books
        self.invalid_patterns = [
            r'^chapter\s+\d+$',
            r'^section\s+\d+',
            r'^unit\s+\d+',
            r'^introduction$',
            r'^overview$',
            r'^review$',
            r'^summary$',
            r'^exercises?$',
            r'^quiz(zes)?$',
            r'^appendix',
            r'^glossary',
            r'^index$',
            r'^references?$',
            r'^bibliography$',
            r'^\d+(\.\d+)*\s',
            r'^table of contents$',
        ]

        # Updated technical keywords to be more specific
        self.technical_keywords = {
            'programming': [
                # Core OOP concepts
                'class', 'inheritance', 'polymorphism', 'encapsulation',
                # Data Structures
                'array', 'linked list', 'stack', 'queue', 'tree', 'graph',
                # Algorithms
                'sorting', 'searching', 'recursion', 'iteration',
                # Advanced concepts
                'template', 'exception', 'pointer', 'reference'
            ]
        }

        # Further refined topic categories and dependencies
        self.topic_hierarchy = {
            'fundamentals': {
                'level': 0,
                'topics': ['data types', 'variables', 'operators', 'control flow']
            },
            'functions': {
                'level': 1,
                'topics': ['functions', 'parameters', 'return values', 'scope']
            },
            'data_structures': {
                'level': 2,
                'topics': ['arrays', 'strings', 'pointers', 'structs', 'linked lists']
            },
            'oop_basics': {
                'level': 3,
                'topics': ['classes', 'objects', 'methods', 'encapsulation']
            },
            'oop_advanced': {
                'level': 4,
                'topics': ['inheritance', 'polymorphism', 'virtual functions', 'templates']
            },
            'advanced_concepts': {
                'level': 5,
                'topics': ['exception handling', 'stl', 'smart pointers', 'templates']
            }
        }

        # Additional filters for better prerequisite selection
        self.generic_topics = {
            'processing', 'basic elements', 'structured programming',
            'problem analysis', 'programming with', 'elements of',
            'software', 'language of'
        }

    def set_domain(self, domain: str):
        """Set the technical domain for keyword validation"""
        if domain in self.technical_keywords:
            self.current_domain = domain
        else:
            raise ValueError(f"Unsupported domain: {domain}. Available domains: {list(self.technical_keywords.keys())}")

    def is_valid_topic(self, topic: str) -> bool:
        """Validate if a topic is legitimate for the current domain"""
        # Check against invalid patterns
        if any(re.match(pattern, topic.lower()) for pattern in self.invalid_patterns):
            return False

        # Check for domain-specific keywords if domain is set
        if hasattr(self, 'current_domain'):
            topic_lower = topic.lower()
            domain_keywords = self.technical_keywords[self.current_domain]
            return any(keyword in topic_lower for keyword in domain_keywords)

        # If no domain is set, accept any non-generic topic
        return True

    def process_topic(self, topic: str, content: str, all_topics: list) -> dict:
        """Process a single topic with enhanced response parsing"""
        try:
            if not self.is_valid_topic(topic):
                logger.info(f"Skipping invalid topic: {topic}")
                return {"prerequisites": []}

            logger.info(f"Processing topic: {topic}")

            response = self.chain.invoke({
                "topic": topic,
                "content": content,
                "all_topics": str(all_topics)[:1000]
            })

            # Enhanced response parsing
            try:
                # First attempt: Find JSON pattern
                json_pattern = r'\{[^{}]*\}'
                matches = re.findall(json_pattern, response)
                
                if matches:
                    for match in matches:
                        try:
                            result = json.loads(match)
                            if isinstance(result, dict) and "prerequisites" in result:
                                filtered_prereqs = self.validate_prerequisites(topic, result["prerequisites"])
                                return {"prerequisites": filtered_prereqs}
                        except json.JSONDecodeError:
                            continue

                # Second attempt: Extract prerequisites from text response
                prereq_pattern = r'prerequisites"?\s*:?\s*\[(.*?)\]'
                matches = re.findall(prereq_pattern, response, re.IGNORECASE)
                
                if matches:
                    for match in matches:
                        try:
                            # Clean and parse the prerequisites
                            prereqs = [
                                p.strip(' "\'') 
                                for p in match.split(',')
                                if p.strip(' "\'')
                            ]
                            filtered_prereqs = self.validate_prerequisites(topic, prereqs)
                            return {"prerequisites": filtered_prereqs}
                        except Exception:
                            continue

                # If no valid response found
                logger.warning(f"Could not parse response for topic: {topic}")
                return {"prerequisites": []}

            except Exception as e:
                logger.warning(f"Error parsing response for topic {topic}: {str(e)}")
                return {"prerequisites": []}

        except Exception as e:
            logger.error(f"Error processing topic {topic}: {str(e)}")
            return {"prerequisites": []}

    def clean_topic_name(self, topic: str) -> str:
        """Remove numbers and dots from the start of topic names."""
        # Remove pattern like "2.4 " or "16. " from start of string
        cleaned = re.sub(r'^\d+\.?\d*\s*', '', topic)
        return cleaned.strip()

    def build_knowledge_graph(self, df: pd.DataFrame, batch_size: int = 4) -> pd.DataFrame:
        """Build knowledge graph with GPU-optimized batch processing"""
        relationships = []
        total_topics = len(df)
        processed_topics = 0
        
        # Clean all topics before creating the list
        logger.info("Cleaning topic names...")
        all_topics = [self.clean_topic_name(title) for title in df['Title'].tolist()]

        # Process in batches using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                batch_size_actual = len(batch)
                processed_topics += batch_size_actual
                
                # Calculate and display progress
                progress = (processed_topics / total_topics) * 100
                logger.info(f"Progress: {progress:.1f}% ({processed_topics}/{total_topics} topics) - "
                           f"Batch {i//batch_size + 1}/{(len(df) + batch_size - 1)//batch_size}")

                # Submit batch of topics for processing
                future_to_topic = {
                    executor.submit(
                        self.process_topic,
                        self.clean_topic_name(row['Title']),
                        row['Content'],
                        all_topics
                    ): self.clean_topic_name(row['Title'])
                    for _, row in batch.iterrows()
                }

                # Collect results
                for future in future_to_topic:
                    topic = future_to_topic[future]
                    try:
                        result = future.result()
                        if result["prerequisites"]:
                            for prereq in result["prerequisites"]:
                                if prereq in all_topics and prereq != topic:
                                    relationships.append({
                                        "prerequisite": prereq,
                                        "topic": topic
                                    })
                    except Exception as e:
                        logger.error(f"Error processing topic {topic}: {str(e)}")

        return pd.DataFrame(relationships)

    def validate_prerequisites(self, topic: str, prerequisites: list) -> list:
        """Enhanced prerequisite validation with better filtering and consistency checks"""
        try:
            # Enhanced skip patterns
            skip_patterns = [
                r'^chapter\s+\d+',
                r'introduction to',
                r'overview of',
                r'basics of',
                r'fundamentals of',
                r'getting started',
                r'introduction$',
                r'summary$',
                r'review$',
                r'exercises?$'
            ]
            
            # Define topic complexity levels
            complexity_levels = {
                'basic': [
                    'syntax', 'variables', 'data types', 'operators', 'input output',
                    'control flow', 'loops', 'basic statements'
                ],
                'intermediate': [
                    'functions', 'arrays', 'strings', 'structs', 'pointers',
                    'references', 'file handling', 'basic classes'
                ],
                'advanced': [
                    'classes', 'inheritance', 'polymorphism', 'templates',
                    'exceptions', 'stl', 'smart pointers', 'move semantics'
                ],
                'expert': [
                    'design patterns', 'memory management', 'multithreading',
                    'advanced algorithms', 'optimization', 'meta programming'
                ]
            }

            # Determine topic complexity level
            topic_level = None
            topic_lower = topic.lower()
            for level, keywords in complexity_levels.items():
                if any(keyword in topic_lower for keyword in keywords):
                    topic_level = level
                    break

            cleaned_prereqs = []
            
            # Skip if topic matches skip patterns
            if any(re.search(pattern, topic, re.IGNORECASE) for pattern in skip_patterns):
                return []
            
            for prereq in prerequisites:
                if not prereq or any(re.search(pattern, prereq, re.IGNORECASE) for pattern in skip_patterns):
                    continue

                prereq_lower = prereq.lower()
                
                # Determine prerequisite complexity level
                prereq_level = None
                for level, keywords in complexity_levels.items():
                    if any(keyword in prereq_lower for keyword in keywords):
                        prereq_level = level
                        break

                # Validate complexity level relationship
                if topic_level and prereq_level:
                    levels = ['basic', 'intermediate', 'advanced', 'expert']
                    topic_idx = levels.index(topic_level)
                    prereq_idx = levels.index(prereq_level)
                    
                    # Only accept prerequisites that are 1-2 levels below current topic
                    if 0 <= topic_idx - prereq_idx <= 2:
                        cleaned_prereqs.append(prereq)
                else:
                    # If levels can't be determined, use basic validation
                    if prereq != topic:
                        cleaned_prereqs.append(prereq)

            # Remove duplicates and limit to 3 most relevant prerequisites
            return list(dict.fromkeys(cleaned_prereqs))[:3]
            
        except Exception as e:
            logger.error(f"Error validating prerequisites: {str(e)}")
            return []

def main():
    try:
        # Read and prepare data
        logger.info("Reading input file...")

        # Support multiple file formats
        file_path = 'PF and DS.csv'  # or .xlsx, .json
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path)
        else:
            raise ValueError("Unsupported file format")
        #df=df.head(300)
        logger.info(f"Loaded {len(df)} topics")
        # Verify required columns
        required_columns = ['Title', 'Content']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Input file must contain columns: {required_columns}")

        # Initialize builder with specific domain
        kg_builder = KnowledgeGraphBuilder()
        kg_builder.set_domain('programming')  # or 'database', 'networking', etc.

        # Build knowledge graph
        relationships_df = kg_builder.build_knowledge_graph(df)

        # Save and display results
        if not relationships_df.empty:
            relationships_df.to_csv('FULLprerequisites_graph1.csv', index=False)
            logger.info("Results saved to prerequisites_graph.csv")

            print("\nPrerequisites Relationships:")
            print("-" * 80)
            print(f"{'Prerequisite':<40} | {'Topic':<40}")
            print("-" * 80)
            for _, row in relationships_df.iterrows():
                print(f"{row['prerequisite']:<40} | {row['topic']:<40}")
            print("-" * 80)
        else:
            logger.warning("No relationships found")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()


