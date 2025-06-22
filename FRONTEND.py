# USING CONDA ENV

import streamlit as st
from pdf_toc_extractor import PDFTOCExtractor
from read_toc_file_AND_make_df import read_toc_file
import tempfile
import os
import re
import json
from KG_Frontend import main as display_knowledge_graph
from chatbot_api import ask_chatbot  # Import just the chatbot function
from hierarchy_frontend import visualize_prerequisites
from quiz_generation import get_quiz_on_topic
import time
import random
import pymongo
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def parse_quiz_questions(cleaned_text, last_learned_topic):
    """
    Parse quiz questions from cleaned text with multiple strategies.
    
    Args:
        cleaned_text (str): Text to parse questions from
        last_learned_topic (str): Topic being quizzed on
        
    Returns:
        list: List of parsed questions with format [(difficulty, question_data), ...]
    """
    # Initialize questions list
    parsed_questions = []
    
    # Get topic-specific keywords for better matching
    topic_keywords = [last_learned_topic.lower()]
    # Add common variations based on the topic name - fully generic approach
    topic_keywords.extend([
        t.strip() for t in last_learned_topic.lower().split() 
        if len(t.strip()) > 2  # Only add meaningful words
    ])
    
    # Add plural form if not already present
    if topic_keywords[0][-1] != 's':
        topic_keywords.append(topic_keywords[0] + 's')
    
    # Extract questions from formats commonly returned by LLMs
    # First, look for the exact format seen in the API response with numbered questions
    # Common format: "1. Easy question: Which of the following..."
    numbered_format = re.findall(r'(\d+)\.\s*(Easy|Medium|Hard)?\s*question:?\s*\n*\s*(.*?)\n+\s*A\)(.*?)\n+\s*B\)(.*?)\n+\s*C\)(.*?)\n+\s*D\)(.*?)(?=\d+\.|Correct answer:|$)', cleaned_text, re.DOTALL | re.IGNORECASE)
    
    if numbered_format:
        for match in numbered_format:
            question_num = match[0]
            difficulty_hint = match[1].title() if match[1] else None
            question_text = match[2].strip()
            
            # Skip questions that are too short
            if len(question_text) < 5:
                continue
                
            options = [
                ('A', match[3].strip()),
                ('B', match[4].strip()),
                ('C', match[5].strip()),
                ('D', match[6].strip())
            ]
            
            # Determine difficulty
            if difficulty_hint:
                difficulty = difficulty_hint
            elif question_num == "1":
                difficulty = "Easy"
            elif question_num == "2":
                difficulty = "Medium"
            elif question_num == "3":
                difficulty = "Hard"
            else:
                # Assign based on current assignments
                difficulties_found = [diff for diff, _ in parsed_questions]
                if "Hard" not in difficulties_found:
                    difficulty = "Hard"
                elif "Medium" not in difficulties_found:
                    difficulty = "Medium"
                else:
                    difficulty = "Easy"
            
            # Find correct answer
            correct_answer = "A"  # Default
            answer_search = re.search(rf'\d+\.\s*(?:Easy|Medium|Hard)?\s*question:?\s*\n*\s*{re.escape(question_text)}.*?Correct answer:\s*([A-D])', cleaned_text, re.DOTALL | re.IGNORECASE)
            if answer_search:
                correct_answer = answer_search.group(1).upper()
            
            # Add only if we don't already have this difficulty
            if difficulty not in [diff for diff, _ in parsed_questions]:
                parsed_questions.append((difficulty, {
                    'question': question_text,
                    'options': options,
                    'correct': correct_answer
                }))
    
    # Try another common format based on the examples: "Which of the following..."
    if not parsed_questions or len(parsed_questions) < 3:
        direct_questions = re.findall(r'(Which|What|How|Why|When|Where).*?\?(.*?A\).*?B\).*?C\).*?D\).*?)(?=\n\d+\.|Correct answer:|$)', cleaned_text, re.DOTALL | re.IGNORECASE)
        
        for i, match in enumerate(direct_questions[:3]):  # Process up to 3 questions
            full_text = match[0] + match[1]
            question_text = re.search(r'(.*?\?)', full_text, re.DOTALL)
            if not question_text:
                continue
                
            question_text = question_text.group(1).strip()
            
            # Check if this question is already captured
            already_exists = False
            for _, q_data in parsed_questions:
                if q_data['question'] == question_text:
                    already_exists = True
                    break
                    
            if already_exists:
                continue
                
            # Extract options from the matched text
            opt_a = re.search(r'A\)(.*?)(?=B\))', full_text, re.DOTALL)
            opt_b = re.search(r'B\)(.*?)(?=C\))', full_text, re.DOTALL)  
            opt_c = re.search(r'C\)(.*?)(?=D\))', full_text, re.DOTALL)
            opt_d = re.search(r'D\)(.*?)(?=Correct answer:|$)', full_text, re.DOTALL)
            
            if not (opt_a and opt_b and opt_c and opt_d):
                continue
                
            options = [
                ('A', opt_a.group(1).strip()),
                ('B', opt_b.group(1).strip()),
                ('C', opt_c.group(1).strip()),
                ('D', opt_d.group(1).strip())
            ]
            
            # Determine difficulty based on position and existing questions
            difficulties = ["Easy", "Medium", "Hard"]
            difficulty = difficulties[min(i, 2)]  # Default based on position
            
            # Check if this difficulty is already assigned
            difficulties_found = [diff for diff, _ in parsed_questions]
            if difficulty in difficulties_found:
                # Find an unassigned difficulty
                for alt_diff in difficulties:
                    if alt_diff not in difficulties_found:
                        difficulty = alt_diff
                        break
            
            # Find correct answer
            correct_answer = "A"  # Default
            answer_search = re.search(r'Correct answer:?\s*([A-D])', full_text, re.DOTALL | re.IGNORECASE)
            if answer_search:
                correct_answer = answer_search.group(1).upper()
            
            parsed_questions.append((difficulty, {
                'question': question_text,
                'options': options,
                'correct': correct_answer
            }))
    
    # STRATEGY 1: Standard formatted quiz questions
    # Look for a pattern like "Here are three multiple-choice questions about X"
    standard_quiz_pattern = r'Here are (?:three |some |a few )?multiple-choice questions about'
    if re.search(standard_quiz_pattern, cleaned_text, re.IGNORECASE):
        # Try to find questions for each difficulty level
        for difficulty in ["Hard", "Medium", "Easy"]:
            # Pattern to find the full question with its options
            question_pattern = fr'{difficulty}:\s*\n*\s*\d*\.*\s*(.*?)\n*\s*A\)(.*?)\n*\s*B\)(.*?)\n*\s*C\)(.*?)\n*\s*D\)(.*?)(?:Correct answer:|correct answer:|answer:|\n\n|$)'
            question_match = re.search(question_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
            
            if question_match:
                question_text = question_match.group(1).strip()
                options = [
                    ('A', question_match.group(2).strip()),
                    ('B', question_match.group(3).strip()),
                    ('C', question_match.group(4).strip()),
                    ('D', question_match.group(5).strip())
                ]
                
                # Find correct answer
                correct_answer = "A"  # Default
                correct_pattern = fr'{difficulty}:.*?(?:Correct answer:|correct answer:|answer:)\s*([A-D])'
                correct_match = re.search(correct_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
                if correct_match:
                    correct_answer = correct_match.group(1).upper()
                
                parsed_questions.append((difficulty, {
                    'question': question_text,
                    'options': options,
                    'correct': correct_answer
                }))
            else:
                # If we can't find the question, create a generic one
                generic_questions = {
                    "Hard": f"What is the most challenging aspect of {last_learned_topic}?",
                    "Medium": f"How would you implement {last_learned_topic} in a practical application?",
                    "Easy": f"What is the basic purpose of {last_learned_topic}?"
                }
                
                parsed_questions.append((difficulty, {
                    'question': generic_questions[difficulty],
                    'options': [
                        ('A', f"It allows for efficient data organization and access"),
                        ('B', f"It provides control over program execution flow"),
                        ('C', f"It enables memory management and optimization"),
                        ('D', f"It facilitates code reusability and modularity")
                    ],
                    'correct': 'A'
                }))
    
    # Look for numbered questions if the standard format wasn't found or is incomplete
    if not parsed_questions or len(parsed_questions) < 3:
        # This pattern finds numbered questions with their options
        numbered_question_pattern = r'(\d+)\.\s+(Easy|Medium|Hard)?\s*\n*\s*question:?\s*\n*\s*(.*?)\n+\s*A\)(.*?)\n+\s*B\)(.*?)\n+\s*C\)(.*?)\n+\s*D\)(.*?)(?:Correct answer:|correct answer:|answer:|\n\n|$)'
        numbered_questions = re.finditer(numbered_question_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
        
        for match in numbered_questions:
            question_num = match.group(1)
            difficulty_hint = match.group(2).title() if match.group(2) else None
            question_text = match.group(3).strip()
            options = [
                ('A', match.group(4).strip()),
                ('B', match.group(5).strip()),
                ('C', match.group(6).strip()),
                ('D', match.group(7).strip())
            ]
            
            # Determine difficulty based on question number or hint
            if difficulty_hint:
                difficulty = difficulty_hint
            elif question_num == "1":
                difficulty = "Easy"
            elif question_num == "2":
                difficulty = "Medium"
            elif question_num == "3":
                difficulty = "Hard"
            else:
                # Default difficulty based on existing questions
                difficulties_found = [diff for diff, _ in parsed_questions]
                if "Hard" not in difficulties_found:
                    difficulty = "Hard"
                elif "Medium" not in difficulties_found:
                    difficulty = "Medium"
                else:
                    difficulty = "Easy"
            
            # Find correct answer in the vicinity of this question
            correct_answer = "A"  # Default
            correct_pattern = r'Correct answer:?\s*([A-D])'
            correct_part = cleaned_text[match.start():match.start() + 1000]  # Look in a reasonable window
            correct_match = re.search(correct_pattern, correct_part, re.IGNORECASE)
            if correct_match:
                correct_answer = correct_match.group(1).upper()
            
            # Check if we already have this difficulty
            if difficulty not in [diff for diff, _ in parsed_questions]:
                parsed_questions.append((difficulty, {
                    'question': question_text,
                    'options': options,
                    'correct': correct_answer
                }))
    
    # Try a more flexible pattern if we still need questions
    if not parsed_questions or len(parsed_questions) < 3:
        # This pattern finds any questions with A), B), C), D) options
        flexible_pattern = r'(.*?\?)\s*\n*\s*A\)(.*?)\n*\s*B\)(.*?)\n*\s*C\)(.*?)\n*\s*D\)(.*?)(?:Correct answer:|correct answer:|answer:|\n\n|$)'
        flexible_matches = re.finditer(flexible_pattern, cleaned_text, re.DOTALL)
        
        for match in flexible_matches:
            question_text = match.group(1).strip()
            
            # Skip if this question is already captured
            already_exists = False
            for _, q_data in parsed_questions:
                if q_data['question'] == question_text:
                    already_exists = True
                    break
            
            if already_exists:
                continue
                
            options = [
                ('A', match.group(2).strip()),
                ('B', match.group(3).strip()),
                ('C', match.group(4).strip()),
                ('D', match.group(5).strip())
            ]
            
            # Determine difficulty based on existing questions
            difficulties_found = [diff for diff, _ in parsed_questions]
            if "Hard" not in difficulties_found:
                difficulty = "Hard"
            elif "Medium" not in difficulties_found:
                difficulty = "Medium"
            else:
                difficulty = "Easy"
            
            # Find correct answer
            correct_answer = "A"  # Default
            correct_pattern = r'Correct answer:?\s*([A-D])'
            correct_part = cleaned_text[match.start():match.start() + 1000]  # Look in a reasonable window
            correct_match = re.search(correct_pattern, correct_part, re.IGNORECASE)
            if correct_match:
                correct_answer = correct_match.group(1).upper()
            
            parsed_questions.append((difficulty, {
                'question': question_text,
                'options': options,
                'correct': correct_answer
            }))
            
            # If we have 3 questions, break
            if len(parsed_questions) >= 3:
                break
    
    # STRATEGY 2: Look for parentheses difficulty markers (Easy), (Medium), (Hard)
    if not parsed_questions:
        difficulty_markers_found = False
        easy_match = re.search(r'\(Easy\)(.*?)(?=\(Medium\)|\(Hard\)|$)', cleaned_text, re.DOTALL)
        medium_match = re.search(r'\(Medium\)(.*?)(?=\(Easy\)|\(Hard\)|$)', cleaned_text, re.DOTALL)
        hard_match = re.search(r'\(Hard\)(.*?)(?=\(Easy\)|\(Medium\)|$)', cleaned_text, re.DOTALL)
        
        if easy_match or medium_match or hard_match:
            difficulty_markers_found = True
            
            # Process each section
            difficulty_sections = []
            if easy_match:
                difficulty_sections.append(("Easy", easy_match.group(1).strip()))
            if medium_match:
                difficulty_sections.append(("Medium", medium_match.group(1).strip()))
            if hard_match:
                difficulty_sections.append(("Hard", hard_match.group(1).strip()))
            
            for difficulty, section_text in difficulty_sections:
                # Extract question - everything before first option or all text if no options found
                q_match = re.search(r'(.*?)(?=A\)|a\))', section_text, re.DOTALL)
                question_text = q_match.group(1).strip() if q_match else section_text.strip()
                
                # If the question text is just whitespace or very short, try to find a question with a question mark
                if len(question_text) < 10:
                    q_match = re.search(r'(.*?\?)', section_text, re.DOTALL)
                    question_text = q_match.group(1).strip() if q_match else section_text.strip()
                
                # Find correct answer
                correct_answer = "A"  # Default
                for pattern in [r'Correct answer:\s*([A-D])', r'correct answer is\s*([A-D])', r'answer:\s*([A-D])']:
                    correct_match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
                    if correct_match:
                        correct_answer = correct_match.group(1).upper()
                        break
                
                # Extract options
                options = []
                for letter in ['A', 'B', 'C', 'D']:
                    # Try both uppercase and lowercase option markers
                    for opt_pattern in [fr'{letter}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)', fr'{letter.lower()}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)']:
                        opt_match = re.search(opt_pattern, section_text, re.DOTALL)
                        if opt_match and len(opt_match.group(1).strip()) > 0:
                            options.append((letter, opt_match.group(1).strip()))
                            break
                    # If still no match, add a placeholder
                    if len(options) < (ord(letter) - ord('A') + 1):
                        options.append((letter, f"Option {letter} for {last_learned_topic}"))
                
                # Add the parsed question
                parsed_questions.append((difficulty, {
                    'question': question_text,
                    'options': options,
                    'correct': correct_answer
                }))
    
    # STRATEGY 3: Look for "Easy:", "Medium:", "Hard:" patterns
    if not parsed_questions:
        colon_markers_found = False
        easy_match = re.search(r'Easy\s*:(.*?)(?=Medium\s*:|Hard\s*:|$)', cleaned_text, re.DOTALL | re.IGNORECASE)
        medium_match = re.search(r'Medium\s*:(.*?)(?=Easy\s*:|Hard\s*:|$)', cleaned_text, re.DOTALL | re.IGNORECASE)
        hard_match = re.search(r'Hard\s*:(.*?)(?=Easy\s*:|Medium\s*:|$)', cleaned_text, re.DOTALL | re.IGNORECASE)
        
        if easy_match or medium_match or hard_match:
            colon_markers_found = True
            
            # Process each section
            difficulty_sections = []
            if easy_match:
                difficulty_sections.append(("Easy", easy_match.group(1).strip()))
            if medium_match:
                difficulty_sections.append(("Medium", medium_match.group(1).strip()))
            if hard_match:
                difficulty_sections.append(("Hard", hard_match.group(1).strip()))
            
            for difficulty, section_text in difficulty_sections:
                # Extract question - everything before first option or all text if no options found
                q_match = re.search(r'(.*?)(?=A\)|a\))', section_text, re.DOTALL)
                question_text = q_match.group(1).strip() if q_match else section_text.strip()
                
                # If the question text is just whitespace or very short, try to find a question with a question mark
                if len(question_text) < 10:
                    q_match = re.search(r'(.*?\?)', section_text, re.DOTALL)
                    question_text = q_match.group(1).strip() if q_match else section_text.strip()
                
                # Find correct answer
                correct_answer = "A"  # Default
                for pattern in [r'Correct answer:\s*([A-D])', r'correct answer is\s*([A-D])', r'answer:\s*([A-D])']:
                    correct_match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
                    if correct_match:
                        correct_answer = correct_match.group(1).upper()
                        break
                
                # Extract options
                options = []
                for letter in ['A', 'B', 'C', 'D']:
                    # Try both uppercase and lowercase option markers
                    for opt_pattern in [fr'{letter}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)', fr'{letter.lower()}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)']:
                        opt_match = re.search(opt_pattern, section_text, re.DOTALL)
                        if opt_match and len(opt_match.group(1).strip()) > 0:
                            options.append((letter, opt_match.group(1).strip()))
                            break
                    # If still no match, add a placeholder
                    if len(options) < (ord(letter) - ord('A') + 1):
                        options.append((letter, f"Option {letter} for {last_learned_topic}"))
                
                # Add the parsed question
                parsed_questions.append((difficulty, {
                    'question': question_text,
                    'options': options,
                    'correct': correct_answer
                }))
    
    # STRATEGY 4: Fallback - extract any questions followed by options
    if not parsed_questions:
        # Find any questions with question marks followed by options
        question_blocks = re.findall(r'(\d+\.|Q\d+:?|Question \d+:?)\s*(.*?\?)\s*(?:[^\n]*\n)+\s*(?:[A-Da-d]\).*(?:\n|$))+', cleaned_text, re.DOTALL)
        
        if question_blocks:
            # Extract up to 3 questions
            for i, (_, question_text) in enumerate(question_blocks[:3]):
                # Assign difficulty based on position
                difficulty = ["Hard", "Medium", "Easy"][min(i, 2)]
                
                # Extract options for this question
                options = []
                question_block_text = ''.join([block[0] + ' ' + block[1] for block in question_blocks if block[1] == question_text])
                
                for letter in ['A', 'B', 'C', 'D']:
                    # Try both uppercase and lowercase option markers
                    for opt_pattern in [fr'{letter}\)(.*?)(?=[A-Da-d]\)|$)', fr'{letter.lower()}\)(.*?)(?=[A-Da-d]\)|$)']:
                        opt_match = re.search(opt_pattern, question_block_text, re.DOTALL)
                        if opt_match and len(opt_match.group(1).strip()) > 0:
                            options.append((letter, opt_match.group(1).strip()))
                            break
                    # If still no match, add a placeholder
                    if len(options) < (ord(letter) - ord('A') + 1):
                        options.append((letter, f"Option {letter} for {last_learned_topic}"))
                
                # Find correct answer
                correct_answer = "A"  # Default
                for pattern in [r'Correct answer:\s*([A-D])', r'correct answer is\s*([A-D])', r'answer:\s*([A-D])']:
                    correct_match = re.search(pattern, question_block_text, re.IGNORECASE | re.DOTALL)
                    if correct_match:
                        correct_answer = correct_match.group(1).upper()
                        break
                
                # Add the parsed question
                parsed_questions.append((difficulty, {
                    'question': question_text.strip(),
                    'options': options,
                    'correct': correct_answer
                }))
    
    # STRATEGY 5: Last resort - search for any relevant questions with keywords
    if not parsed_questions:
        # Build a regex pattern that includes the topic keywords
        topic_pattern = "|".join(re.escape(keyword) for keyword in topic_keywords)
        question_pattern = fr'((?:What|How|Why|Which|When).*?(?:{topic_pattern}).*?\?)'
        
        topic_questions = re.findall(question_pattern, cleaned_text, re.DOTALL | re.IGNORECASE)
        if topic_questions:
            # Process up to 3 questions
            for i, question_text in enumerate(topic_questions[:3]):
                # Determine difficulty - first is Hard, second is Medium, third is Easy
                difficulty = ["Hard", "Medium", "Easy"][min(i, 2)]
                
                # Find position of question in cleaned_text
                question_pos = cleaned_text.find(question_text)
                after_question = cleaned_text[question_pos + len(question_text):] if question_pos >= 0 else ""
                
                # Find next question to limit search area
                next_q_pos = len(after_question)
                for next_q in topic_questions:
                    if next_q != question_text:
                        pos = after_question.find(next_q)
                        if 0 <= pos < next_q_pos:
                            next_q_pos = pos
                
                search_area = after_question[:next_q_pos]
                
                # Look for options in the limited search area
                options = []
                for letter in ['A', 'B', 'C', 'D']:
                    # Try both uppercase and lowercase option markers
                    for opt_pattern in [fr'{letter}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)', fr'{letter.lower()}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)']:
                        opt_match = re.search(opt_pattern, search_area, re.DOTALL)
                        if opt_match and len(opt_match.group(1).strip()) > 0:
                            options.append((letter, opt_match.group(1).strip()))
                            break
                    
                    # If still no match, try the wider area
                    if len(options) < (ord(letter) - ord('A') + 1):
                        for opt_pattern in [fr'{letter}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)', fr'{letter.lower()}\)(.*?)(?=[A-Da-d]\)|Correct answer:|$)']:
                            opt_match = re.search(opt_pattern, after_question, re.DOTALL)
                            if opt_match and len(opt_match.group(1).strip()) > 0:
                                options.append((letter, opt_match.group(1).strip()))
                                break
                    
                    # If still no match, check for numbered options
                    if len(options) < (ord(letter) - ord('A') + 1):
                        num = ord(letter) - ord('A') + 1
                        num_pattern = fr'{num}\.\s+(.*?)(?=\d+\.\s+|Correct answer:|$)'
                        num_match = re.search(num_pattern, search_area, re.DOTALL)
                        if num_match and len(num_match.group(1).strip()) > 0:
                            options.append((letter, num_match.group(1).strip()))
                        else:
                            # Create generic options related to the topic
                            generic_options = [
                                (letter, f"It's a key concept in {last_learned_topic} that helps with memory management"),
                                (letter, f"It's a technique used in {last_learned_topic} for optimizing performance"),
                                (letter, f"It's a fundamental principle of {last_learned_topic}"),
                                (letter, f"It's an advanced feature of {last_learned_topic}")
                            ]
                            options.append(generic_options[ord(letter) - ord('A')])
                
                # Look for correct answer
                correct_answer = "A"  # Default
                for pattern in [r'Correct answer:\s*([A-D])', r'correct answer is\s*([A-D])', r'answer:\s*([A-D])']:
                    correct_match = re.search(pattern, search_area, re.IGNORECASE | re.DOTALL)
                    if correct_match:
                        correct_answer = correct_match.group(1).upper()
                        break
                
                # Add the parsed question
                parsed_questions.append((difficulty, {
                    'question': question_text.strip(),
                    'options': options,
                    'correct': correct_answer
                }))
    
    # FINAL STRATEGY: If no questions found, create generic ones
    if not parsed_questions:
        # Create generic questions for all difficulty levels
        for difficulty in ["Hard", "Medium", "Easy"]:
            # Create question text based on difficulty
            if difficulty == "Hard":
                question_text = f"What is the most advanced concept in {last_learned_topic}?"
            elif difficulty == "Medium":
                question_text = f"How would you implement {last_learned_topic} in a practical scenario?"
            else:  # Easy
                question_text = f"What is the basic purpose of {last_learned_topic}?"
                
            # Create generic options
            options = [
                ('A', f"It's a way to organize data efficiently"),
                ('B', f"It's a technique for controlling program flow"),
                ('C', f"It's a method for optimizing memory usage"),
                ('D', f"It's an approach for enhancing code reusability")
            ]
            
            # Add the generic question
            parsed_questions.append((difficulty, {
                'question': question_text,
                'options': options,
                'correct': 'A'  # Default correct answer
            }))
    
    # Ensure we have exactly 3 questions (Hard, Medium, Easy)
    difficulties_found = [diff for diff, _ in parsed_questions]
    
    for difficulty in ['Hard', 'Medium', 'Easy']:
        if difficulty not in difficulties_found:
            # Create a generic question for this difficulty
            if difficulty == "Hard":
                question_text = f"What is the most challenging aspect of {last_learned_topic}?"
            elif difficulty == "Medium":
                question_text = f"How would you implement {last_learned_topic} in a real-world application?"
            else:  # Easy
                question_text = f"What is the basic purpose of {last_learned_topic}?"
            
            # Create generic options
            options = [
                ('A', f"It provides a way to organize and access data efficiently"),
                ('B', f"It enables control over program execution flow"),
                ('C', f"It helps with memory management and resource allocation"),
                ('D', f"It facilitates code reusability and abstraction")
            ]
            
            parsed_questions.append((difficulty, {
                'question': question_text,
                'options': options,
                'correct': 'A'  # Default correct answer
            }))
    
    # Ensure we only have 3 questions max
    if len(parsed_questions) > 3:
        # Make sure we have one of each difficulty if possible
        difficulties_to_keep = []
        for diff in ["Hard", "Medium", "Easy"]:
            for question_diff, _ in parsed_questions:
                if question_diff == diff and diff not in difficulties_to_keep:
                    difficulties_to_keep.append(diff)
                    break
        
        # If we couldn't find all difficulties, just take the first 3
        if len(difficulties_to_keep) < 3:
            parsed_questions = parsed_questions[:3]
        else:
            # Keep questions that match our desired difficulties
            filtered_questions = []
            for diff in ["Hard", "Medium", "Easy"]:
                for question in parsed_questions:
                    if question[0] == diff and len(filtered_questions) < 3:
                        filtered_questions.append(question)
                        break
            parsed_questions = filtered_questions

    # Make sure all questions have meaningful content
    for i, (difficulty, question) in enumerate(parsed_questions):
        # Check if question text is meaningful
        if not question['question'] or len(question['question'].strip()) < 10:
            # Create a generic question based on the topic and difficulty
            generic_questions = {
                "Hard": f"What is the most complex concept in {last_learned_topic}?",
                "Medium": f"How would you implement {last_learned_topic} efficiently?",
                "Easy": f"What is the primary purpose of {last_learned_topic}?"
            }
            question['question'] = generic_questions[difficulty]
        
        # Check if options are meaningful or just placeholders
        has_meaningful_options = all(len(opt[1].strip()) > 10 for opt in question['options'])
        
        # Only check for meaningful options if not from question bank
        if not question.get('from_bank') and (not has_meaningful_options or len(question['options']) < 4):
            # Replace with generic options
            generic_options = [
                ('A', f"It helps organize program logic and improves readability"),
                ('B', f"It enables efficient memory management and resource allocation"),
                ('C', f"It provides mechanisms for handling errors and exceptions"),
                ('D', f"It facilitates code reuse and enhances modularity")
            ]
            question['options'] = generic_options
            question['correct'] = 'A'  # Set a default correct answer
        
        # Ensure options are in A, B, C, D order
        sorted_options = sorted(question['options'], key=lambda x: x[0])
        question['options'] = sorted_options
        
        # Update the question in the list
        parsed_questions[i] = (difficulty, question)
    
    # Sort by difficulty
    difficulty_order = {"Hard": 0, "Medium": 1, "Easy": 2}
    parsed_questions.sort(key=lambda x: difficulty_order.get(x[0], 999))
    
    return parsed_questions

def get_questions_from_bank(topic):
    """
    Get one random question from each difficulty (hard, medium, basic) for a given topic.
    Returns a list of (Difficulty, question_dict) tuples in the order Hard, Medium, Easy.
    """
    try:
        with open('questionbank.json', 'r') as f:
            question_bank = json.load(f)

        # Find the closest matching topic
        best_match = None
        for bank_topic in question_bank.keys():
            if topic.lower() in bank_topic.lower() or bank_topic.lower() in topic.lower():
                best_match = bank_topic
                break

        if not best_match:
            return []

        # Map to your display order
        difficulty_map = [("Hard", "hard"), ("Medium", "medium"), ("Easy", "basic")]
        questions = []
        for display_diff, bank_diff in difficulty_map:
            qlist = question_bank[best_match].get(bank_diff, [])
            if qlist:
                random_q = random.choice(qlist)
                parsed_q = {
                    'question': random_q['question'],
                    'options': [(opt[0], opt[3:]) for opt in random_q['options']],
                    'correct': random_q['answer'][0],  # Get just the letter
                    'from_bank': True
                }
                questions.append((display_diff, parsed_q))
        return questions
    except Exception as e:
        print(f"Error reading question bank: {e}")
        return []

def show_topic_selection():
    import json
    import re
    from quiz_generation import get_quiz_on_topic
    import pymongo
    import os
    
    # Get database connection (same as in login_signup.py)
    def get_database_connection():
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        client = pymongo.MongoClient(mongo_uri)
        db = client["auth_app_db"]
        return db
    
    # Update user progress in database
    def update_user_progress():
        if 'username' in st.session_state and st.session_state.username:
            try:
                db = get_database_connection()
                users_collection = db["users"]
                result = users_collection.update_one(
                    {"username": st.session_state.username},
                    {"$set": {
                        "learned_topics": st.session_state.learned_topics,
                        "last_quiz_topic": st.session_state.get('last_quiz_topic', None)
                    }}
                )
                # Debug info (can be removed later)
                if result.modified_count > 0:
                    print(f"✅ Database updated for user {st.session_state.username}: {len(st.session_state.learned_topics)} topics")
                else:
                    print(f"⚠️ No database changes for user {st.session_state.username}")
            except Exception as e:
                st.error(f"Error updating progress: {e}")
                print(f"❌ Database error: {e}")
    
    st.title('🚀 Programming Learning Path Builder')
    st.markdown("""
    <div class="card">
    <p>Welcome to the Programming Learning Path Builder! This tool helps you create a personalized learning path based on what you already know.</p>
    <p>Simply check the topics you've already learned, and we'll help you visualize your progress and suggest what to learn next.</p>
    </div>
    """, unsafe_allow_html=True)
    try:
        with open('cpp-prerequisites-json.json', 'r') as f:
            cpp_prerequisites = json.load(f)
        all_topics = list(cpp_prerequisites.keys())
        foundation_topics = []
        advanced_topics = []
        intermediate_topics = []
        for topic in all_topics:
            if not cpp_prerequisites[topic]:
                foundation_topics.append(topic)
            elif not any(topic in prereqs for prereqs in cpp_prerequisites.values()):
                advanced_topics.append(topic)
            else:
                intermediate_topics.append(topic)
        st.header("📋 Select the topics you've already learned")
        st.info("This will help us customize your learning path.")
        selected_count = len(st.session_state.learned_topics)
        total_count = len(all_topics)
        progress = int((selected_count / total_count) * 100) if total_count > 0 else 0
        st.progress(progress)
        st.markdown(f"<p style='text-align: center; color: #1976D2;'><strong>{selected_count}</strong> of {total_count} topics selected ({progress}%)</p>", unsafe_allow_html=True)
        all_ordered_topics = foundation_topics + intermediate_topics + advanced_topics
        col1, col2, col3, col4 = st.columns(4)
        columns = [col1, col2, col3, col4]
        for i, topic in enumerate(all_ordered_topics):
            column_index = i % 4
            with columns[column_index]:
                if st.checkbox(topic, key=f"topic_{topic}_{i}", value=topic in st.session_state.learned_topics):
                    if topic not in st.session_state.learned_topics:
                        st.session_state.learned_topics.append(topic)
                        def add_prerequisites_recursively(topic_to_add):
                            prereqs = cpp_prerequisites.get(topic_to_add, [])
                            for prereq in prereqs:
                                if prereq not in st.session_state.learned_topics:
                                    st.session_state.learned_topics.append(prereq)
                                    add_prerequisites_recursively(prereq)
                        add_prerequisites_recursively(topic)
                        # Update database with new progress
                        update_user_progress()
                        st.success("✅ Progress saved!")
                        st.rerun()
                elif topic in st.session_state.learned_topics:
                    st.session_state.learned_topics.remove(topic)
                    # Update database with new progress
                    update_user_progress()
                    st.success("✅ Progress saved!")
                    st.rerun()
        if st.session_state.learned_topics:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader("🎯 Your Learning Progress")
            st.markdown("<div style='margin-bottom: 20px;'>", unsafe_allow_html=True)
            for topic in sorted(st.session_state.learned_topics):
                st.markdown(f"<span class='topic-pill'>{topic}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Get the last topic from the learned topics list
            if 'quiz_topic' not in st.session_state:
                st.session_state.quiz_topic = None
                st.session_state.current_quiz = None
            
            # Quiz generation card
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📝 Quiz on Your Recent Topic")
            
            # Use the last topic from the ordered list that is also in learned topics
            last_learned_topic = None
            for topic in reversed(all_ordered_topics):
                if topic in st.session_state.learned_topics:
                    last_learned_topic = topic
                    break
                    
            if last_learned_topic:
                #st.markdown(f"**{last_learned_topic}**")
                
                # Use fixed ngrok URL
                quiz_ngrok_url = "https://3b57-34-32-195-84.ngrok-free.app"
                
                # Initialize quiz-related session state variables
                if 'quiz_topic' not in st.session_state:
                    st.session_state.quiz_topic = None
                if 'current_quiz' not in st.session_state:
                    st.session_state.current_quiz = None
                if 'quiz_step' not in st.session_state:
                    st.session_state.quiz_step = 0  # 0: start, 1: hard, 2: medium, 3: easy, 4: completed
                if 'user_answers' not in st.session_state:
                    st.session_state.user_answers = []
                if 'correct_answers' not in st.session_state:
                    st.session_state.correct_answers = []
                if 'parsed_questions' not in st.session_state:
                    st.session_state.parsed_questions = []
                if 'raw_quiz_text' not in st.session_state:
                    st.session_state.raw_quiz_text = None
                
                # Generate quiz button
                if st.button("Generate Quiz", use_container_width=True):
                    with st.spinner(f"Loading Quiz..."):
                        try:
                            # Get quiz from the API
                            quiz_text = get_quiz_on_topic(last_learned_topic, quiz_ngrok_url)
                            st.session_state.raw_quiz_text = quiz_text
                            
                            # Reset quiz state and ensure quiz_topic is correctly set
                            st.session_state.quiz_topic = last_learned_topic
                            st.session_state.current_quiz = quiz_text
                            st.session_state.quiz_step = 0  # Start over
                            st.session_state.user_answers = []
                            st.session_state.correct_answers = []
                            
                            # Update highlight topic to match current quiz topic
                            st.session_state.highlight_topic = last_learned_topic
                            
                            # Parse the quiz text for the previous topic
                            cleaned_text = re.sub(r'\[INST\].*?\[/INST\]', '', quiz_text, flags=re.DOTALL).strip()
                            
                            # Initialize questions list
                            parsed_questions = parse_quiz_questions(cleaned_text, last_learned_topic)
                            print(f"Questions from API: {len(parsed_questions) if parsed_questions else 0}")
                            
                            # Check if questions are generic (fallback)
                            def is_generic_question(q):
                                return (
                                    "most advanced concept" in q['question'].lower() or
                                    "basic purpose" in q['question'].lower() or
                                    "implement" in q['question'].lower()
                                )

                            if all(is_generic_question(qdata) for _, qdata in parsed_questions):
                                bank_questions = get_questions_from_bank(last_learned_topic)
                                if bank_questions:
                                    parsed_questions = bank_questions
                                    st.info("Using questions from question bank.")
                                else:
                                    st.warning("No questions found in question bank. Using generic questions.")
                            
                            # Log success information
                            st.success(f"Quiz loaded successfully!")
                            
                            # Update session state with parsed questions
                            st.session_state.parsed_questions = parsed_questions
                            st.session_state.quiz_step = 1
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error generating quiz: {str(e)}")
                
                # If we have questions, display the current question
                if st.session_state.quiz_step > 0 and st.session_state.quiz_step <= len(st.session_state.parsed_questions):
                    # Get the question by index, but ensure Hard is first, Medium is second, Easy is third
                    # regardless of how they were parsed
                    all_difficulties = [diff for diff, _ in st.session_state.parsed_questions]
                    
                    # Map step to standard difficulty order
                    if st.session_state.quiz_step == 1:
                        target_difficulty = "Hard"
                    elif st.session_state.quiz_step == 2:
                        target_difficulty = "Medium"
                    else:
                        target_difficulty = "Easy"
                    
                    # Find the index of the target difficulty, or use the current step if not found
                    try:
                        index = all_difficulties.index(target_difficulty)
                    except ValueError:
                        index = st.session_state.quiz_step - 1
                    
                    # Get the question data
                    difficulty, question_data = st.session_state.parsed_questions[index]
                    
                    # Display the question without difficulty label
                    st.subheader("Question:")
                    
                    # Check if question text is empty or just contains difficulty label and add a fallback
                    question_text = question_data['question']
                    if not question_text or question_text.strip() == "" or len(question_text.strip()) < 10:
                        question_text = f"What is the most important aspect of {st.session_state.quiz_topic}?"
                    
                    st.markdown(question_text)
                    
                    # Display options as radio buttons
                    if question_data['options']:
                        # Check if options are meaningful or just placeholders
                        has_meaningful_options = any(len(opt[1].strip()) > 10 for opt in question_data['options'])
                        
                        # Only replace with generic options if NOT from question bank
                        if not question_data.get('from_bank') and not has_meaningful_options:
                            # Create meaningful options based on the topic
                            meaningful_options = [
                                ('A', f"It is a fundamental concept in {st.session_state.quiz_topic}"),
                                ('B', f"It is an advanced feature of {st.session_state.quiz_topic}"),
                                ('C', f"It is not related to {st.session_state.quiz_topic}"),
                                ('D', f"None of the above")
                            ]
                            # Update the question options
                            question_data['options'] = meaningful_options
                            correct_answer = 'A'  # Default correct answer
                        
                        # Sort options by letter to ensure A, B, C, D order
                        sorted_options = sorted(question_data['options'], key=lambda x: x[0])
                        option_labels = [f"{opt[0]}) {opt[1]}" for opt in sorted_options]
                        
                        # Add an empty first option to allow no selection by default
                        selected_option = st.radio(
                            "Select your answer:",
                            option_labels,
                            index=None,  # No option pre-selected
                            key=f"quiz_option_{difficulty}_{st.session_state.quiz_step}"
                        )
                        
                        # Extract the selected option letter
                        selected_letter = selected_option.split(')')[0] if selected_option else None
                        
                        # Submit button
                        submit_button = st.button("Submit Answer", key=f"submit_{difficulty}_{st.session_state.quiz_step}", disabled=selected_option is None)
                        if submit_button:
                            # Store user's answer
                            st.session_state.user_answers.append((difficulty, selected_letter))
                            
                            # Check if answer is correct
                            is_correct = selected_letter == question_data['correct']
                            st.session_state.correct_answers.append(is_correct)
                            
                            # Show feedback
                            if is_correct:
                                st.success("✅ Correct!")
                            else:
                                st.error(f"❌ Incorrect. The correct answer is {question_data['correct']}.")
                            
                            # Move to next question - directly increment step and rerun
                            st.session_state.quiz_step += 1
                            st.rerun()
                    else:
                        st.error("No options found for this question.")
                
                # Quiz completion
                elif st.session_state.quiz_step > len(st.session_state.parsed_questions) and st.session_state.parsed_questions:
                    # Show quiz results
                    st.subheader("Quiz Completed!")
                    
                    if st.session_state.user_answers:
                        correct_count = sum(st.session_state.correct_answers)
                        total_count = len(st.session_state.correct_answers)
                        
                        st.markdown(f"You got **{correct_count}** out of **{total_count}** questions correct.")
                        
                        # Display results for each question in standard order
                        for i, is_correct in enumerate(st.session_state.correct_answers):
                            if is_correct:
                                st.markdown(f"**Question {i+1}**: ✅ Correct")
                            else:
                                st.markdown(f"**Question {i+1}**: ❌ Incorrect")
                        
                        # If at least 2 answers are correct (passing score), show visualization button
                        if correct_count >= 2:
                            # Store the highlight information in session state for visualization
                            st.session_state.highlight_topic = st.session_state.quiz_topic
                            st.session_state.highlight_hard_correct = st.session_state.correct_answers[0]  # Hard is always first
                            
                            # Update last_quiz_topic and save to database
                            st.session_state.last_quiz_topic = st.session_state.quiz_topic
                            update_user_progress()
                            
                            st.success(f"Congratulations! You passed the quiz with {correct_count}/{total_count} correct answers.")
                            
                            if st.button("🌳 View Topic in Visualization", type="primary"):
                                st.session_state.current_page = "hierarchy_tree"
                                highlight_text = "dark blue" if st.session_state.correct_answers[0] else "medium blue"
                                st.success(f"Successfully set '{st.session_state.quiz_topic}' to highlight in {highlight_text} in the visualization!")
                                st.rerun()
                        else:
                            # Less than 2 correct answers - remove topic from learned topics and find previous topic
                            st.error(f"You got fewer than 2 questions correct. You need to review '{st.session_state.quiz_topic}' before proceeding.")
                            
                            # Remove the current quiz topic from learned topics
                            if st.session_state.quiz_topic in st.session_state.learned_topics:
                                st.session_state.learned_topics.remove(st.session_state.quiz_topic)
                            
                            # Update database after removing failed topic
                            update_user_progress()
                            
                            # Find the second-last learned topic
                            previous_topic = None
                            learned_topics_ordered = [topic for topic in all_ordered_topics if topic in st.session_state.learned_topics]
                            
                            if len(learned_topics_ordered) > 1:
                                # Get the second-last topic
                                previous_topic = learned_topics_ordered[-2]
                                
                                # Show info message about previous topic
                                st.info(f"**{previous_topic}**")
                                
                                # Auto-generate the quiz when user clicks the button
                                if st.button("Continue with Previous Topic Quiz", type="primary", key="continue_to_prev"):
                                    with st.spinner(f"Loading {previous_topic}..."):
                                        try:
                                            # Get quiz from API for the previous topic
                                            quiz_text = get_quiz_on_topic(previous_topic, quiz_ngrok_url)
                                            
                                            # Update session state variables
                                            st.session_state.quiz_topic = previous_topic
                                            st.session_state.current_quiz = quiz_text
                                            st.session_state.raw_quiz_text = quiz_text
                                            st.session_state.quiz_step = 0
                                            st.session_state.user_answers = []
                                            st.session_state.correct_answers = []
                                            
                                            # Update the highlight topic to the previous topic
                                            st.session_state.highlight_topic = previous_topic
                                            
                                            # Parse the quiz text for the previous topic
                                            cleaned_text = re.sub(r'\[INST\].*?\[/INST\]', '', quiz_text, flags=re.DOTALL).strip()
                                            
                                            # Initialize questions list
                                            parsed_questions = parse_quiz_questions(cleaned_text, previous_topic)
                                            
                                            # Check if questions are generic (fallback)
                                            def is_generic_question(q):
                                                return (
                                                    "most advanced concept" in q['question'].lower() or
                                                    "basic purpose" in q['question'].lower() or
                                                    "implement" in q['question'].lower()
                                                )

                                            if all(is_generic_question(qdata) for _, qdata in parsed_questions):
                                                bank_questions = get_questions_from_bank(previous_topic)
                                                if bank_questions:
                                                    parsed_questions = bank_questions
                                                    st.info("Using questions from question bank.")
                                                else:
                                                    st.warning("No questions found in question bank. Using generic questions.")
                                            
                                            # Log success information
                                            st.success(f"Quiz loaded successfully!")

                                            # Update session state with parsed questions
                                            st.session_state.parsed_questions = parsed_questions
                                            st.session_state.quiz_step = 1
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error generating quiz for previous topic: {str(e)}")
                            else:
                                st.info("Select topics to continue.")
            else:
                st.info("Select topics to continue.")
            
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading Programming prerequisites: {e}")

def create_progress_visualization():
    """
    Create interactive visualizations to show learning progress
    """
    try:
        # Load the prerequisites data
        with open('cpp-prerequisites-json.json', 'r') as f:
            cpp_prerequisites = json.load(f)
        
        all_topics = list(cpp_prerequisites.keys())
        learned_topics = st.session_state.get('learned_topics', [])
        
        # Calculate progress statistics
        total_topics = len(all_topics)
        completed_topics = len(learned_topics)
        remaining_topics = total_topics - completed_topics
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
        
        # Categorize topics
        foundation_topics = []
        intermediate_topics = []
        advanced_topics = []
        
        for topic in all_topics:
            if not cpp_prerequisites[topic]:  # No prerequisites
                foundation_topics.append(topic)
            elif not any(topic in prereqs for prereqs in cpp_prerequisites.values()):  # Not a prerequisite for others
                advanced_topics.append(topic)
            else:
                intermediate_topics.append(topic)
        
        # Calculate progress by category
        foundation_completed = len([t for t in foundation_topics if t in learned_topics])
        intermediate_completed = len([t for t in intermediate_topics if t in learned_topics])
        advanced_completed = len([t for t in advanced_topics if t in learned_topics])
        
        # Create visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Overall Progress Pie Chart
            st.subheader("📊 Overall Progress")
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Completed', 'Remaining'],
                values=[completed_topics, remaining_topics],
                hole=0.4,
                marker_colors=['#4CAF50', '#E0E0E0'],
                textinfo='label+percent',
                textfont_size=12,
                hovertemplate='<b>%{label}</b><br>Topics: %{value}<br>Percentage: %{percent}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                title=f"Progress: {completed_topics}/{total_topics} Topics ({progress_percentage:.1f}%)",
                title_font_size=16,
                showlegend=True,
                height=400,
                margin=dict(t=50, b=50, l=50, r=50)
            )
            
            # Add center text - REMOVED
            # fig_pie.add_annotation(
            #     text=f"{progress_percentage:.1f}%<br>Complete",
            #     x=0.5, y=0.5,
            #     font_size=20,
            #     font_color="#2196F3",
            #     showarrow=False
            # )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Progress by Category Bar Chart
            st.subheader("📈 Progress by Category")
            
            categories = ['Foundation', 'Intermediate', 'Advanced']
            completed_counts = [foundation_completed, intermediate_completed, advanced_completed]
            total_counts = [len(foundation_topics), len(intermediate_topics), len(advanced_topics)]
            percentages = [(comp/total*100) if total > 0 else 0 for comp, total in zip(completed_counts, total_counts)]
            
            fig_bar = go.Figure()
            
            # Add completed bars
            fig_bar.add_trace(go.Bar(
                name='Completed',
                x=categories,
                y=completed_counts,
                marker_color='#4CAF50',
                text=[f'{count}/{total}' for count, total in zip(completed_counts, total_counts)],
                textposition='inside',
                hovertemplate='<b>%{x}</b><br>Completed: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>',
                customdata=percentages
            ))
            
            # Add remaining bars
            remaining_counts = [total - comp for comp, total in zip(completed_counts, total_counts)]
            fig_bar.add_trace(go.Bar(
                name='Remaining',
                x=categories,
                y=remaining_counts,
                marker_color='#E0E0E0',
                hovertemplate='<b>%{x}</b><br>Remaining: %{y}<extra></extra>'
            ))
            
            fig_bar.update_layout(
                title="Topics by Difficulty Level",
                title_font_size=16,
                barmode='stack',
                xaxis_title="Category",
                yaxis_title="Number of Topics",
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                showlegend=True
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Detailed Progress Table
        st.subheader("📋 Detailed Progress Breakdown")
        
        progress_data = {
            'Category': ['Foundation', 'Intermediate', 'Advanced', 'Total'],
            'Completed': [foundation_completed, intermediate_completed, advanced_completed, completed_topics],
            'Total': [len(foundation_topics), len(intermediate_topics), len(advanced_topics), total_topics],
            'Progress (%)': [
                f"{(foundation_completed/len(foundation_topics)*100):.1f}%" if len(foundation_topics) > 0 else "0%",
                f"{(intermediate_completed/len(intermediate_topics)*100):.1f}%" if len(intermediate_topics) > 0 else "0%",
                f"{(advanced_completed/len(advanced_topics)*100):.1f}%" if len(advanced_topics) > 0 else "0%",
                f"{progress_percentage:.1f}%"
            ]
        }
        
        df_progress = pd.DataFrame(progress_data)
        st.dataframe(df_progress, use_container_width=True, hide_index=True)
        
        # Recent Activity Timeline (if quiz data available)
        if 'last_quiz_topic' in st.session_state and st.session_state.last_quiz_topic:
            st.subheader("🎯 Recent Activity")
            st.info(f"Last quiz completed: **{st.session_state.last_quiz_topic}**")
        
        # Learning Path Suggestions
        st.subheader("🚀 Next Steps")
        
        # Find topics that can be learned next (prerequisites met)
        available_topics = []
        for topic in all_topics:
            if topic not in learned_topics:
                prereqs = cpp_prerequisites[topic]
                if all(prereq in learned_topics for prereq in prereqs):
                    available_topics.append(topic)
        
        if available_topics:
            st.success(f"You can now learn: **{', '.join(available_topics[:5])}**")
            if len(available_topics) > 5:
                st.info(f"And {len(available_topics) - 5} more topics are available!")
        else:
            if completed_topics == total_topics:
                st.success("🎉 Congratulations! You've completed all topics!")
            else:
                st.warning("Complete more prerequisite topics to unlock new learning paths.")
        
    except Exception as e:
        st.error(f"Error creating progress visualization: {e}")
        # Fallback simple progress display
        learned_count = len(st.session_state.get('learned_topics', []))
        st.metric("Topics Completed", learned_count)

def main():
    # Enhanced CSS styling with modern design
    st.markdown("""
        <style>
        /* Main Container */
        .main {
            padding: 2rem;
            border-radius: 15px;
            background-color: #f8f9fa;
        }
        
        /* Header Styles */
        h1 {
            color: #2c3e50;
            text-align: center;
            padding: 20px 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 1.5rem;
        }
        
        h2 {
            color: #34495e;
            padding: 15px 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 600;
            letter-spacing: -0.3px;
        }
        
        h3 {
            color: #3498db;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 600;
        }
        
        /* Button Styles */
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3.2em;
            background-color: #2196F3;
            color: white;
            font-weight: bold;
            margin: 10px 0;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background-color: #1976D2;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-2px);
        }
        
        /* Primary Button */
        .stButton[kind="primary"]>button {
            background-color: #4CAF50;
        }
        
        .stButton[kind="primary"]>button:hover {
            background-color: #388E3C;
        }
        
        /* Secondary Button (for back buttons) */
        button.back-button {
            background-color: #78909C !important;
        }
        
        button.back-button:hover {
            background-color: #546E7A !important;
        }
        
        /* Checkbox Styling */
        .stCheckbox {
            background-color: white;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border: 1px solid #e0e0e0;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .stCheckbox:hover {
            border-color: #2196F3;
            box-shadow: 0 2px 5px rgba(33, 150, 243, 0.1);
        }
        
        /* Alert Boxes */
        .stAlert {
            border-radius: 8px;
            border: none !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .stSuccess {
            background-color: #E8F5E9 !important;
            color: #2E7D32 !important;
        }
        
        .stInfo {
            background-color: #E3F2FD !important;
            color: #1565C0 !important;
        }
        
        .stWarning {
            background-color: #FFF8E1 !important;
            color: #F57F17 !important;
        }
        
        .stError {
            background-color: #FFEBEE !important;
            color: #C62828 !important;
        }
        
        /* Navigation Container */
        .nav-container {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            padding: 10px;
            background-color: #ECEFF1;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        /* Card Style Containers */
        .card {
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            background-color: white;
            border-left: 4px solid #2196F3;
        }
        
        /* Chat Container */
        .chat-message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .user-message {
            background-color: #E3F2FD;
            border-left: 4px solid #2196F3;
        }
        
        .bot-message {
            background-color: #F1F8E9;
            border-left: 4px solid #689F38;
        }
        
        /* Search box styling */
        .search-box {
            border-radius: 8px;
            border: 2px solid #E0E0E0;
            padding: 10px 15px;
            transition: all 0.3s ease;
        }
        
        .search-box:focus {
            border-color: #2196F3;
            box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.2);
        }
        
        /* Topic pills in the summary */
        .topic-pill {
            display: inline-block;
            background-color: #E3F2FD;
            color: #1565C0;
            padding: 5px 10px;
            border-radius: 15px;
            margin: 3px;
            font-size: 0.85em;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        /* Footer */
        .footer {
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            font-size: 0.8em;
            color: #78909C;
        }
        
        /* Separator */
        hr {
            margin: 30px 0;
            border: none;
            height: 1px;
            background-color: #ECEFF1;
        }
        </style>
    """, unsafe_allow_html=True)

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

    # Session state initializations
    if 'processed_topics' not in st.session_state:
        st.session_state.processed_topics = []
    if 'show_updated_toc' not in st.session_state:
        st.session_state.show_updated_toc = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "cpp_prerequisites"
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'learned_topics' not in st.session_state:
        st.session_state.learned_topics = []

    # Modern navigation bar with icons and better styling
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊 Dashboard", use_container_width=True):
            # Clear current_page to go back to dashboard
            if 'current_page' in st.session_state:
                del st.session_state.current_page
            st.rerun()
    with col2:
        if st.button("📚 Learning Path", use_container_width=True):
            st.session_state.current_page = "cpp_prerequisites"
            st.rerun()
    with col3:
        if st.button("🌳 Graph Visualization", use_container_width=True):
            st.session_state.current_page = "hierarchy_tree"
            st.rerun()
    with col4:
        if st.button("🤖 AI Chatbot", use_container_width=True):
            st.session_state.current_page = "chatbot"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Display the selected page
    if st.session_state.current_page == "chatbot":
        # Chatbot Page with Improved UI
        st.title("🤖 AI Programming Learning Assistant")
        
        # Check if we have a pending question from graph view
        has_pending_question = False
        if "pending_question" in st.session_state and "pending_topic" in st.session_state:
            has_pending_question = True
            pending_question = st.session_state.pending_question
            pending_topic = st.session_state.pending_topic
            
            # Clear pending state to avoid reprocessing
            del st.session_state.pending_question
            del st.session_state.pending_topic
        
        # If we have a pending question, respond to it automatically
        if has_pending_question:
            with st.spinner(f"Getting information about {pending_topic}..."):
                answer = ask_chatbot(pending_question)
                
                # Add response to chat history
                st.session_state.chat_history.append({"role": "bot", "content": answer})
                st.rerun()  # Refresh to show the new messages
        
        # Chat interface
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Ask me anything about Programming")
        
        # Initialize chat_message key if not present and handle clearing
        if "chat_message" not in st.session_state:
            # Check if we have a pending question from hierarchy view
            if "pending_question" in st.session_state:
                st.session_state.chat_message = st.session_state.pending_question
                # Clear pending question to avoid reusing it
                del st.session_state.pending_question
            else:
                st.session_state.chat_message = ""
        elif "clear_input" in st.session_state and st.session_state.clear_input:
            # Check if we have a pending question
            if "pending_question" in st.session_state:
                st.session_state.chat_message = st.session_state.pending_question
                del st.session_state.pending_question
            else:
                st.session_state.chat_message = ""
            # Reset the flag
            st.session_state.clear_input = False
        
        # Get user input
        user_question = st.text_area(
            "Your question:", 
            height=100, 
            placeholder="Example: How do pointers work in C++?",
            key="chat_message"
        )
        
        # Auto-trigger chatbot response for redirected questions
        if ("pending_question" in st.session_state or 
            ("chat_history" in st.session_state and 
             st.session_state.chat_history and 
             len(st.session_state.chat_history) % 2 == 1)):  # Odd number means last message was from user
            
            # Only trigger if we haven't already processed this message
            last_question = st.session_state.chat_history[-1]["content"] if st.session_state.chat_history else None
            
            # Only get response if we don't already have a bot response to this question
            should_respond = True
            if len(st.session_state.chat_history) >= 2:
                if st.session_state.chat_history[-2]["role"] == "user" and st.session_state.chat_history[-2]["content"] == last_question:
                    should_respond = False
            
            if should_respond and last_question:
                with st.spinner("Getting response..."):
                    answer = ask_chatbot(last_question)
                
                # Add bot response to chat history
                st.session_state.chat_history.append({"role": "bot", "content": answer})
                
                # Clear any pending question flag
                if "pending_question" in st.session_state:
                    del st.session_state.pending_question
                
                st.rerun()

        # Create two columns for buttons
        col1, col2 = st.columns([1, 4])
        
        # Handle send button click
        with col1:
            if st.button("Send 📤", type="primary", use_container_width=True):
                if user_question:
                    # Add the current question to chat history
                    st.session_state.chat_history.append({"role": "user", "content": user_question})
                    
                    # Get response from chatbot
                    with st.spinner("Getting response..."):
                        answer = ask_chatbot(user_question)
                    
                    # Add bot response to chat history
                    st.session_state.chat_history.append({"role": "bot", "content": answer})

                    # Don't try to modify st.session_state.chat_message directly
                    # Instead, use a flag to indicate we want to clear the input on next rerun
                    if "clear_input" not in st.session_state:
                        st.session_state.clear_input = True
                    else:
                        st.session_state.clear_input = True
                    
                    # Trigger rerun for refresh
                    st.rerun()

        # Clear chat button
        with col2:
            if st.session_state.chat_history and st.button("Clear Chat 🧹", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display chat history with improved styling
        if st.session_state.chat_history:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Conversation")
            
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message bot-message"><strong>AI:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.current_page == "knowledge_graph":
        # Knowledge Graph page (kept for reference)
        st.title('📊 Knowledge Graph Visualization')
        display_knowledge_graph()
        
        # Back button
        if st.button("⬅️ Back to Learning Path", type="primary"):
            st.session_state.current_page = "cpp_prerequisites"
            st.rerun()
        
    elif st.session_state.current_page == "hierarchy_tree":
        # Tree Visualization with improved UI
        st.title('🌳  Topic Relationships')
        
        # Introduction
        st.markdown("""
        <div class="card">
        <p>This visualization shows the relationships between Programming topics. Topics that are prerequisites for others are connected with arrows.</p>
        <p><strong>Tip:</strong> Click on any topic to focus on its direct connections!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display the tree visualization
        try:
            def display_tree_visualization():
                try:
                    with open('cpp-prerequisites-json.json', 'r') as f:
                        prerequisites = json.load(f)
                    visualize_prerequisites()
                except Exception as e:
                    st.error(f"Error displaying visualization: {e}")
                    
            display_tree_visualization()
            
        except Exception as e:
            st.error(f"Error accessing visualization: {e}")
        
        # Back button with styling
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("⬅️ Back to Learning Path", use_container_width=True):
                st.session_state.current_page = "cpp_prerequisites"
                st.rerun()
        
    else:
        # C++ Prerequisites page - call the topic selection function
        show_topic_selection()

    # Add a footer
    st.markdown("""
    <div class="footer">
        <p> Programming Learning Path Builder © 2023 | Built with Streamlit</p>
        <p>An interactive tool to help you master Programming</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
