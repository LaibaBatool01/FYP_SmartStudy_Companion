import streamlit as st
import PyPDF2
import re
from typing import Dict, List
from pdfminer.high_level import extract_text

class PDFTOCExtractor:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.pdf_reader = PyPDF2.PdfReader(pdf_file)

    def extract_built_in_toc(self) -> List[Dict]:
        """Extract built-in table of contents if available"""
        outline = self.pdf_reader.outline
        if not outline:
            return []

        def process_outline(outline_item) -> List[Dict]:
            result = []
            for item in outline_item:
                if isinstance(item, list):
                    result.extend(process_outline(item))
                else:
                    try:
                        skip_titles = ['appendix', 'appendices', 'index', 'preface', 'glossary', 'bibliography', 'references']
                        if any(x in item.title.lower() for x in skip_titles):
                            continue

                        page_num = self.pdf_reader.get_destination_page_number(item)
                        result.append({
                            'title': item.title,
                            'page': page_num + 1
                        })
                    except:
                        continue
            return result

        return process_outline(outline)

    def extract_text_toc(self) -> List[Dict]:
        """Extract TOC by analyzing first few pages"""
        toc_patterns = [
            r'^(?:Chapter\s*)?(\d+|[IVXLCDM]+)[.\s]+([^\d]+?)\.{2,}(\d+)$',
            r'^((?:Chapter|Section)\s*(?:\d+|[IVXLCDM]+)(?:\.\d+)*)\s+([^\d]+?)\s+(\d+)$',
            r'^(?:Chapter\s+)?(\d+|[IVXLCDM]+)\.\s+([^0-9]+?)\s*\.{2,}\s*(\d+)$'
        ]

        toc_items = []
        text = extract_text(self.pdf_file)
        pages = text.split('\f')  # Split text into pages

        max_pages = min(int(len(pages) * 0.15), 20)

        for page_num in range(max_pages):
            lines = pages[page_num].split('\n')

            for line in lines:
                line = line.strip()
                if not line or len(line) < 10:
                    continue

                if '.' not in line or not any(char.isdigit() for char in line):
                    continue

                skip_titles = ['appendix', 'appendices', 'index', 'preface', 'glossary', 'bibliography', 'references']
                if any(x in line.lower() for x in skip_titles):
                    continue

                for pattern in toc_patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        if len(groups) == 3:
                            page = int(groups[2])
                            if page > len(pages):
                                continue

                            title = groups[1].strip()
                            if len(title) < 3 or title.isnumeric():
                                continue

                            toc_items.append({
                                'chapter': groups[0],
                                'title': title,
                                'page': page
                            })
                        break

        return toc_items


def clean_text(text):
    # Replace sequences of non-ASCII characters with a single space
    return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()


def main():
    st.title("PDF Table of Contents Extractor")

    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    
    if uploaded_file is not None:
        extractor = PDFTOCExtractor(uploaded_file)

        built_in_toc = extractor.extract_built_in_toc()
        text_toc = extractor.extract_text_toc()

        if built_in_toc and text_toc:
            st.write("Found two types of Table of Contents:")
            st.write("1. Built-in TOC")
            st.write("2. Extracted TOC")

            choice = st.selectbox("Select TOC to display:", ["Built-in TOC", "Extracted TOC"])

            if choice == "Built-in TOC":
                st.write("### Built-in Table of Contents")
                for item in built_in_toc:
                    st.write(f"{clean_text(item['title'])} .... Page {item['page']}")
            else:
                st.write("### Extracted Table of Contents")
                for item in text_toc:
                    st.write(f"{clean_text(item['chapter'])}: {clean_text(item['title'])} .... Page {item['page']}")
        
        elif built_in_toc:
            st.write("### Built-in Table of Contents")
            for item in built_in_toc:
                st.write(f"{clean_text(item['title'])} .... Page {item['page']}")
        
        elif text_toc:
            st.write("### Extracted Table of Contents")
            for item in text_toc:
                st.write(f"{clean_text(item['chapter'])}: {clean_text(item['title'])} .... Page {item['page']}")
        
        else:
            st.write("No table of contents found in the document.")

if __name__ == "__main__":
    main()






