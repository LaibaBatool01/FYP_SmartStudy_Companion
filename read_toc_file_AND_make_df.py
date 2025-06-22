import pandas as pd
import re
import fitz  # PyMuPDF
from difflib import SequenceMatcher

def clean_text(text):
    """Clean text by removing special characters and normalizing whitespace"""
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split()).lower()
    return text

def text_similarity(text1, text2):
    """Calculate similarity ratio between two texts"""
    return SequenceMatcher(None, clean_text(text1), clean_text(text2)).ratio()

def find_title_in_text(title, lines, similarity_threshold=0.8):
    """Find the most likely match for a title in text lines"""
    clean_title = clean_text(title)
    title_words = clean_title.split()
    
    best_match_idx = -1
    best_match_score = 0
    
    for idx, line in enumerate(lines):
        clean_line = clean_text(line)
        
        # Try exact match first
        if clean_title in clean_line:
            return idx
        
        # Check if all words from title appear in the line
        if all(word in clean_line for word in title_words):
            similarity = text_similarity(clean_title, clean_line)
            if similarity > similarity_threshold and similarity > best_match_score:
                best_match_score = similarity
                best_match_idx = idx
    
    return best_match_idx

def extract_section_content(page_text, current_title, next_title=None, min_similarity=0.6):
    """
    Extract content for a specific section from page text with improved matching
    """
    lines = page_text.split('\n')
    content = []
    found_start = False
    
    # Clean titles for comparison
    current_title_clean = clean_text(current_title)
    next_title_clean = clean_text(next_title) if next_title else None
    
    # Try to find an exact match first, then fall back to fuzzy matching
    for idx, line in enumerate(lines):
        line_clean = clean_text(line)
        
        if not found_start:
            # Try exact match first
            if current_title_clean in line_clean:
                found_start = True
                content.append(line)
                continue
            
            # Try fuzzy matching if exact match fails
            similarity = text_similarity(current_title_clean, line_clean)
            if similarity > min_similarity:
                found_start = True
                content.append(line)
        else:
            # Check if we've reached the next title
            if next_title_clean:
                if next_title_clean in line_clean or text_similarity(next_title_clean, line_clean) > min_similarity:
                    break
            content.append(line)
    
    # If no content found, try a more lenient approach
    if not content and found_start == False:
        for idx, line in enumerate(lines):
            if any(word in line.lower() for word in current_title_clean.split()):
                found_start = True
                content.append(line)
                continue
            if found_start:
                if next_title_clean and any(word in line.lower() for word in next_title_clean.split()):
                    break
                content.append(line)
    
    return '\n'.join(content).strip() if content else ""

def read_toc_file(file_path, book_path):
    """
    Read a TOC text file and convert it to a pandas DataFrame with start page, end page and content
    """
    try:
        # Read the text file
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Initialize lists to store TOC data
        titles = []
        start_pages = []
        contents = []
        
        # Common patterns to exclude (can be extended)
        exclude_patterns = [
            'cover', 'title page', 'copyright', 'contents', 'index',
            'credits', 'about', 'preface', 'acknowledgments',
            'appendix', 'glossary', 'references', 'bibliography'
        ]
        
        valid_entries = []
        # First pass: collect all valid entries
        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                # Try different page number patterns
                match = re.search(r'(.+?)\s*[\.\-]?\s*(\d+)\s*$', line)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'\s*\.+\s*$', '', title)  # Remove trailing dots
                    
                    title_lower = title.lower()
                    should_exclude = any(pattern in title_lower for pattern in exclude_patterns)
                    is_single_letter = len(title_lower.strip()) <= 1
                    
                    if not should_exclude and not is_single_letter:
                        page = int(match.group(2))
                        valid_entries.append((title, page))
        
        # Open PDF document
        doc = fitz.open(book_path)
        
        # Process entries and extract content
        for i, (title, start_page) in enumerate(valid_entries):
            content_text = ""
            current_page = start_page - 1  # 0-based page numbering
            
            # Determine the end page
            if i < len(valid_entries) - 1:
                next_entry = valid_entries[i + 1]
                end_page = next_entry[1] - 1
            else:
                end_page = current_page + 1  # At least include the next page for the last entry
            
            # Get all entries that start on the current page
            same_page_entries = [
                (t, p) for t, p in valid_entries 
                if p == start_page
            ]
            
            # Extract content
            if len(same_page_entries) > 1:
                # Multiple sections on the same page
                current_idx = same_page_entries.index((title, start_page))
                next_title = same_page_entries[current_idx + 1][0] if current_idx + 1 < len(same_page_entries) else None
                
                page = doc[current_page]
                page_text = page.get_text()
                content_text = extract_section_content(page_text, title, next_title)
            else:
                # Single section or spans multiple pages
                for page_num in range(current_page, min(end_page, len(doc))):
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_num == current_page:
                        # First page - extract from title onwards
                        content_text += extract_section_content(page_text, title) + "\n"
                    elif page_num == end_page - 1 and i < len(valid_entries) - 1:
                        # Last page - extract until next title
                        content_text += extract_section_content(page_text, "", valid_entries[i + 1][0]) + "\n"
                    else:
                        # Middle pages - include all content
                        content_text += page_text + "\n"
            
            # Clean up content
            content_text = re.sub(r'\s+', ' ', content_text).strip()
            if len(content_text) > 1000:
                content_text = content_text[:997] + "..."
            
            titles.append(title)
            start_pages.append(start_page)
            contents.append(content_text)
        
        doc.close()
        
        # Create DataFrame
        df = pd.DataFrame({
            'Title': titles,
            'Start_Page': start_pages,
            'Content': contents
        })
        
        return df
    
    except Exception as e:
        print(f"Error processing file: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    file_path = "PF and DS_toc.txt"
    book_path = "PF and DS.pdf"

    file_path1="Starting Out With C++ 8th Edition - Gaddis_toc.txt"
    book_path1="Starting Out With C++ 8th Edition - Gaddis.pdf"


    toc_df = read_toc_file(file_path, book_path)
    toc_df1 = read_toc_file(file_path1, book_path1)
    if toc_df is not None:
        # Remove rows with content less than 50 words
        toc_df = toc_df[toc_df['Content'].str.split().str.len() >= 50]
        print(toc_df)
        toc_df.to_csv('PF and DS.csv', index=False)
    if toc_df1 is not None:
        # Remove rows with content less than 50 words
        toc_df1 = toc_df1[toc_df1['Content'].str.split().str.len() >= 50]
        print(toc_df1)
        toc_df1.to_csv('Starting Out.csv', index=False)    