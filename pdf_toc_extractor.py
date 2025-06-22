import PyPDF2
import re
from typing import Dict, List, Tuple

class PDFTOCExtractor:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.pdf_reader = None

    def read_pdf(self) -> None:
        """Open and read the PDF file"""
        try:
            # Directly create PdfReader from the uploaded file
            self.pdf_reader = PyPDF2.PdfReader(self.pdf_file)
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        # No need to close file as we're using Streamlit's UploadedFile
        pass

    def extract_built_in_toc(self) -> List[Dict]:
        """Extract built-in table of contents if available"""
        try:
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
                            # Skip appendix, index, preface etc.
                            skip_titles = ['appendix', 'appendices', 'index', 'preface',
                                         'glossary', 'bibliography', 'references','symbols']
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
        except Exception:
            return []

    def extract_text_toc(self) -> List[Dict]:
        """Extract TOC by analyzing first few pages"""
        toc_patterns = [
            r'^(?:Chapter\s*)?(\d+|[IVXLCDM]+)[.\s]+([^\d]+?)\.{2,}(\d+)$',
            r'^((?:Chapter|Section)\s*(?:\d+|[IVXLCDM]+)(?:\.\d+)*)\s+([^\d]+?)\s+(\d+)$',
            r'^(?:Chapter\s+)?(\d+|[IVXLCDM]+)\.\s+([^0-9]+?)\s*\.{2,}\s*(\d+)$'
        ]

        toc_items = []
        max_pages = min(int(len(self.pdf_reader.pages) * 0.15), 20)

        for page_num in range(max_pages):
            text = self.pdf_reader.pages[page_num].extract_text()
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                if not line or len(line) < 10:  # Skip empty or very short lines
                    continue

                # Skip lines that don't look like TOC entries
                if '.' not in line or not any(char.isdigit() for char in line):
                    continue

                # Skip appendix, index, preface etc.
                skip_titles = ['appendix', 'appendices', 'index', 'preface',
                             'glossary', 'bibliography', 'references']
                if any(x in line.lower() for x in skip_titles):
                    continue

                for pattern in toc_patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        if len(groups) == 3:
                            # Validate page number is reasonable
                            page = int(groups[2])
                            if page > len(self.pdf_reader.pages):
                                continue

                            title = groups[1].strip()
                            # Skip if title looks suspicious
                            if len(title) < 3 or title.isnumeric():
                                continue

                            toc_items.append({
                                'chapter': groups[0],
                                'title': title,
                                'page': page
                            })
                        break

        return toc_items

    def get_all_tocs(self) -> Tuple[List[Dict], List[Dict]]:
        """Get both built-in and text-extracted TOCs"""
        self.read_pdf()
        built_in_toc = self.extract_built_in_toc()
        text_toc = self.extract_text_toc()
        return built_in_toc, text_toc

    def display_toc(self, toc_items: List[Dict], toc_type: str = "") -> None:
        """Display formatted table of contents"""
        if not toc_items:
            return

        print(f"\n{toc_type} Table of Contents:")
        print("-" * 50)

        for item in toc_items:
            if 'chapter' in item:
                print(f"Chapter {item['chapter']}: {item['title']} .... {item['page']}")
            else:
                print(f"{item['title']} .... {item['page']}")

    def save_toc_to_file(self, toc_items: List[Dict], filename: str) -> None:
        """Save TOC to a text file"""
        with open(filename, 'w', encoding='utf-8') as f:
            for item in toc_items:
                if 'chapter' in item:
                    f.write(f"Chapter {item['chapter']}: {item['title']} .... {item['page']}\n")
                else:
                    f.write(f"{item['title']} .... {item['page']}\n")
# def process_book(pdf_path: str) -> None:
#     try:
#         extractor = PDFTOCExtractor(pdf_path)
#         built_in_toc, text_toc = extractor.get_all_tocs()

#         output_filename = pdf_path.rsplit('.', 1)[0] + '_toc.txt'

#         if built_in_toc and text_toc:
#             print("\nFound two types of Table of Contents:")
#             print("\n1. Built-in TOC:")
#             extractor.display_toc(built_in_toc, "Built-in")

#             print("\n2. Extracted TOC:")
#             extractor.display_toc(text_toc, "Extracted")

#             choice = input("\nWhich TOC would you like to save? (1/2): ")

#             if choice == '1':
#                 extractor.save_toc_to_file(built_in_toc, output_filename)
#             elif choice == '2':
#                 extractor.save_toc_to_file(text_toc, output_filename)
#             else:
#                 print("Invalid choice. No TOC saved.")
#                 return

#         elif built_in_toc:
#             extractor.display_toc(built_in_toc, "Built-in")
#             extractor.save_toc_to_file(built_in_toc, output_filename)
#         elif text_toc:
#             extractor.display_toc(text_toc, "Extracted")
#             extractor.save_toc_to_file(text_toc, output_filename)
#         else:
#             print("No table of contents found in the document.")
#             return

#         print(f"\nTOC saved to: {output_filename}")

#     except Exception as e:
#         print(f"Error processing PDF: {str(e)}")


# process_book("PF and DS.pdf")

# print("--------------------------------next book--------------------------------")

# process_book("Starting Out With C++ 8th Edition - Gaddis.pdf")

