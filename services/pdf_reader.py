import fitz # PyMuPDF
import io

def extract_text(pdf_content: bytes) -> str:
    """
    Extracts text from PDF content (bytes).
    """
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise # Re-raise the exception