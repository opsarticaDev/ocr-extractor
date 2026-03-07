#!/usr/bin/env python3
"""
OCR Extractor - Text Extraction from Images & PDFs
Part of AI Toolkit

Features:
- Extract text from images (JPG, PNG, TIFF, etc.)
- Extract text from scanned PDFs
- Extract text from digital PDFs (no OCR needed)
- Multiple OCR engines (Tesseract, EasyOCR)
- Batch processing
- Multiple output formats (TXT, DOCX, JSON)
- Language support (100+ languages)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, asdict
import tempfile
import shutil

# Core
try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# PDF handling
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Tesseract OCR
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# EasyOCR (deep learning)
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

# PDF to image conversion
try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

# DOCX output
try:
    from docx import Document
    from docx.shared import Pt, Inches
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CONFIG = {
    "ocr_engine": "tesseract",  # tesseract, easyocr
    "language": "eng",
    "dpi": 300,  # For PDF to image conversion
    "preprocess": True,
    "output_format": "txt",  # txt, docx, json
    "preserve_layout": False,
    "confidence_threshold": 0.5,
}

SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp', '.gif'}
SUPPORTED_PDFS = {'.pdf'}

# Common language codes for Tesseract
LANGUAGES = {
    "English": "eng",
    "Spanish": "spa",
    "French": "fra",
    "German": "deu",
    "Italian": "ita",
    "Portuguese": "por",
    "Russian": "rus",
    "Chinese (Simplified)": "chi_sim",
    "Chinese (Traditional)": "chi_tra",
    "Japanese": "jpn",
    "Korean": "kor",
    "Arabic": "ara",
    "Hindi": "hin",
    "Dutch": "nld",
    "Polish": "pol",
    "Turkish": "tur",
    "Vietnamese": "vie",
    "Thai": "tha",
    "Greek": "ell",
    "Hebrew": "heb",
}

# EasyOCR language codes (subset)
EASYOCR_LANGS = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese (Simplified)": "ch_sim",
    "Chinese (Traditional)": "ch_tra",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Vietnamese": "vi",
    "Thai": "th",
}


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class OCRResult:
    """Result of OCR extraction"""
    filename: str
    text: str
    confidence: float
    language: str
    engine: str
    page_count: int
    word_count: int
    processing_time: float
    pages: List[Dict] = None  # Per-page results
    
    def __post_init__(self):
        if self.pages is None:
            self.pages = []


# =============================================================================
# Image Preprocessor
# =============================================================================

class ImagePreprocessor:
    """Preprocess images for better OCR results"""
    
    @staticmethod
    def preprocess(image: Image.Image) -> Image.Image:
        """Apply preprocessing pipeline"""
        import cv2
        
        # Convert PIL to OpenCV
        img = np.array(image)
        
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Binarization (adaptive threshold)
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Deskew (simple approach)
        # For production, consider more sophisticated deskewing
        
        # Convert back to PIL
        return Image.fromarray(binary)
    
    @staticmethod
    def enhance_for_ocr(image: Image.Image) -> Image.Image:
        """Light enhancement without heavy processing"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Increase contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Sharpen slightly
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image


# =============================================================================
# OCR Engines
# =============================================================================

class TesseractEngine:
    """Tesseract OCR engine wrapper"""
    
    def __init__(self, language: str = "eng"):
        if not HAS_TESSERACT:
            raise ImportError("pytesseract not installed")
        
        self.language = language
        
        # Try to find Tesseract executable
        if sys.platform == 'win32':
            import string
            script_dir = Path(__file__).parent
            possible_paths = [
                # Bundled binary in bin/windows/
                str(script_dir.parent / 'bin' / 'windows' / 'tesseract.exe'),
                # Local folder
                os.path.join(os.path.dirname(__file__), 'tesseract', 'tesseract.exe'),
            ]

            # Check standard install locations on all drives
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    possible_paths.extend([
                        os.path.join(drive_path, 'Program Files', 'Tesseract-OCR', 'tesseract.exe'),
                        os.path.join(drive_path, 'Program Files (x86)', 'Tesseract-OCR', 'tesseract.exe'),
                    ])

            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
    
    def extract_text(self, image: Image.Image, preserve_layout: bool = False) -> Tuple[str, float]:
        """
        Extract text from image
        Returns (text, confidence)
        """
        config = ''
        if preserve_layout:
            config = '--psm 6'  # Assume uniform block of text
        
        # Get text
        text = pytesseract.image_to_string(image, lang=self.language, config=config)
        
        # Get confidence
        try:
            data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
        except:
            avg_confidence = 0.0
        
        return text.strip(), avg_confidence
    
    def extract_with_boxes(self, image: Image.Image) -> List[Dict]:
        """Extract text with bounding boxes"""
        data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
        
        results = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:
                results.append({
                    'text': data['text'][i],
                    'confidence': int(data['conf'][i]) / 100,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                })
        
        return results


class EasyOCREngine:
    """EasyOCR engine wrapper"""
    
    def __init__(self, language: str = "en"):
        if not HAS_EASYOCR:
            raise ImportError("easyocr not installed")
        
        self.language = language
        self.reader = None
    
    def _ensure_reader(self):
        """Lazy initialization of reader"""
        if self.reader is None:
            self.reader = easyocr.Reader([self.language], gpu=True)
    
    def extract_text(self, image: Image.Image, preserve_layout: bool = False) -> Tuple[str, float]:
        """Extract text from image"""
        self._ensure_reader()
        
        # Convert PIL to numpy
        img_array = np.array(image)
        
        # Run OCR
        results = self.reader.readtext(img_array)
        
        if not results:
            return "", 0.0
        
        # Extract text and confidence
        texts = []
        confidences = []
        
        for bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)
        
        # Join text (simple approach)
        if preserve_layout:
            # Sort by y-coordinate, then x
            sorted_results = sorted(results, key=lambda x: (x[0][0][1], x[0][0][0]))
            full_text = '\n'.join([r[1] for r in sorted_results])
        else:
            full_text = ' '.join(texts)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return full_text, avg_confidence
    
    def extract_with_boxes(self, image: Image.Image) -> List[Dict]:
        """Extract text with bounding boxes"""
        self._ensure_reader()
        
        img_array = np.array(image)
        results = self.reader.readtext(img_array)
        
        output = []
        for bbox, text, conf in results:
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            
            output.append({
                'text': text,
                'confidence': conf,
                'x': min(x_coords),
                'y': min(y_coords),
                'width': max(x_coords) - min(x_coords),
                'height': max(y_coords) - min(y_coords),
            })
        
        return output


# =============================================================================
# PDF Processor
# =============================================================================

class PDFProcessor:
    """Handle PDF text extraction"""
    
    def __init__(self, ocr_engine, dpi: int = 300):
        self.ocr_engine = ocr_engine
        self.dpi = dpi
    
    def extract_text(self, pdf_path: str, callback=None) -> Tuple[str, List[Dict]]:
        """
        Extract text from PDF
        Returns (full_text, page_results)
        """
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF not installed")
        
        doc = fitz.open(pdf_path)
        full_text = []
        page_results = []
        
        for page_num in range(len(doc)):
            if callback:
                callback(f"Processing page {page_num + 1}/{len(doc)}")
            
            page = doc[page_num]
            
            # First try to extract embedded text (digital PDF)
            text = page.get_text()
            
            if text.strip():
                # Digital PDF with embedded text
                page_results.append({
                    'page': page_num + 1,
                    'text': text.strip(),
                    'method': 'embedded',
                    'confidence': 1.0
                })
                full_text.append(text)
            else:
                # Scanned PDF - need OCR
                # Render page to image
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Run OCR
                text, confidence = self.ocr_engine.extract_text(img)
                
                page_results.append({
                    'page': page_num + 1,
                    'text': text,
                    'method': 'ocr',
                    'confidence': confidence
                })
                full_text.append(text)
        
        doc.close()
        return '\n\n'.join(full_text), page_results
    
    def is_scanned(self, pdf_path: str) -> bool:
        """Check if PDF is scanned (no embedded text)"""
        if not HAS_PYMUPDF:
            return True
        
        doc = fitz.open(pdf_path)
        
        # Check first few pages
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                doc.close()
                return False
        
        doc.close()
        return True


# =============================================================================
# Main OCR Extractor
# =============================================================================

class OCRExtractor:
    """Main OCR extraction class"""
    
    def __init__(self, config: dict = None):
        self.config = config or DEFAULT_CONFIG.copy()
        self.engine = None
        self.pdf_processor = None
    
    def initialize(self, callback=None):
        """Initialize OCR engine"""
        engine_type = self.config.get('ocr_engine', 'tesseract')
        language = self.config.get('language', 'eng')
        
        if callback:
            callback(f"Initializing {engine_type} engine...")
        
        if engine_type == 'tesseract':
            self.engine = TesseractEngine(language)
        elif engine_type == 'easyocr':
            # Convert language code
            lang_code = EASYOCR_LANGS.get(language, language)
            if lang_code in LANGUAGES.values():
                # It's a Tesseract code, try to find EasyOCR equivalent
                for name, code in LANGUAGES.items():
                    if code == lang_code and name in EASYOCR_LANGS:
                        lang_code = EASYOCR_LANGS[name]
                        break
            self.engine = EasyOCREngine(lang_code if len(lang_code) <= 3 else 'en')
        else:
            raise ValueError(f"Unknown OCR engine: {engine_type}")
        
        self.pdf_processor = PDFProcessor(self.engine, self.config.get('dpi', 300))
        
        if callback:
            callback(f"{engine_type} engine ready!")
    
    def extract_from_image(self, image_path: str, callback=None) -> OCRResult:
        """Extract text from image file"""
        import time
        start_time = time.time()
        
        if callback:
            callback(f"Processing: {os.path.basename(image_path)}")
        
        # Load image
        image = Image.open(image_path)
        
        # Preprocess if enabled
        if self.config.get('preprocess', True):
            try:
                image = ImagePreprocessor.enhance_for_ocr(image)
            except:
                pass  # Use original if preprocessing fails
        
        # Extract text
        text, confidence = self.engine.extract_text(
            image, 
            preserve_layout=self.config.get('preserve_layout', False)
        )
        
        processing_time = time.time() - start_time
        
        return OCRResult(
            filename=os.path.basename(image_path),
            text=text,
            confidence=confidence,
            language=self.config.get('language', 'eng'),
            engine=self.config.get('ocr_engine', 'tesseract'),
            page_count=1,
            word_count=len(text.split()),
            processing_time=processing_time,
            pages=[{'page': 1, 'text': text, 'confidence': confidence}]
        )
    
    def extract_from_pdf(self, pdf_path: str, callback=None) -> OCRResult:
        """Extract text from PDF file"""
        import time
        start_time = time.time()
        
        if callback:
            callback(f"Processing PDF: {os.path.basename(pdf_path)}")
        
        text, page_results = self.pdf_processor.extract_text(pdf_path, callback)
        
        # Calculate average confidence
        confidences = [p['confidence'] for p in page_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        processing_time = time.time() - start_time
        
        return OCRResult(
            filename=os.path.basename(pdf_path),
            text=text,
            confidence=avg_confidence,
            language=self.config.get('language', 'eng'),
            engine=self.config.get('ocr_engine', 'tesseract'),
            page_count=len(page_results),
            word_count=len(text.split()),
            processing_time=processing_time,
            pages=page_results
        )
    
    def extract(self, file_path: str, callback=None) -> OCRResult:
        """Extract text from any supported file"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in SUPPORTED_IMAGES:
            return self.extract_from_image(file_path, callback)
        elif ext in SUPPORTED_PDFS:
            return self.extract_from_pdf(file_path, callback)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def save_result(self, result: OCRResult, output_path: str, format: str = None):
        """Save extraction result to file"""
        format = format or self.config.get('output_format', 'txt')
        
        if format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.text)
        
        elif format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, indent=2, ensure_ascii=False)
        
        elif format == 'docx':
            if not HAS_DOCX:
                raise ImportError("python-docx not installed")
            
            doc = Document()
            
            # Add title
            doc.add_heading(f"OCR Extract: {result.filename}", 0)
            
            # Add metadata
            doc.add_paragraph(f"Engine: {result.engine}")
            doc.add_paragraph(f"Language: {result.language}")
            doc.add_paragraph(f"Confidence: {result.confidence:.1%}")
            doc.add_paragraph(f"Word Count: {result.word_count}")
            doc.add_paragraph("")
            
            # Add extracted text
            doc.add_heading("Extracted Text", level=1)
            
            for page in result.pages:
                if len(result.pages) > 1:
                    doc.add_heading(f"Page {page['page']}", level=2)
                doc.add_paragraph(page['text'])
            
            doc.save(output_path)
        
        else:
            raise ValueError(f"Unknown output format: {format}")
    
    def process_batch(self, file_paths: List[str], output_dir: str, callback=None) -> Dict:
        """Process multiple files"""
        os.makedirs(output_dir, exist_ok=True)
        
        stats = {
            'total': len(file_paths),
            'success': 0,
            'failed': 0,
            'total_words': 0,
            'results': []
        }
        
        output_format = self.config.get('output_format', 'txt')
        
        for i, file_path in enumerate(file_paths):
            if callback:
                callback(f"[{i+1}/{len(file_paths)}] Processing...")
            
            try:
                result = self.extract(file_path, callback)
                
                # Determine output path
                base = os.path.splitext(os.path.basename(file_path))[0]
                ext = {'txt': '.txt', 'json': '.json', 'docx': '.docx'}[output_format]
                output_path = os.path.join(output_dir, f"{base}_ocr{ext}")
                
                self.save_result(result, output_path, output_format)
                
                stats['success'] += 1
                stats['total_words'] += result.word_count
                stats['results'].append({
                    'input': file_path,
                    'output': output_path,
                    'words': result.word_count,
                    'confidence': result.confidence,
                    'status': 'success'
                })
                
                if callback:
                    callback(f"✓ {result.filename}: {result.word_count} words ({result.confidence:.1%} confidence)")
                
            except Exception as e:
                stats['failed'] += 1
                stats['results'].append({
                    'input': file_path,
                    'error': str(e),
                    'status': 'failed'
                })
                
                if callback:
                    callback(f"✗ {os.path.basename(file_path)}: {e}")
        
        return stats


# =============================================================================
# GUI Application
# =============================================================================

class OCRExtractorApp:
    """Main application window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Extractor - Text from Images & PDFs")
        self.root.geometry("900x700")
        
        # State
        self.config = DEFAULT_CONFIG.copy()
        self.input_files = []
        self.log_queue = queue.Queue()
        self.running = False
        self.extractor = None
        
        # Build UI
        self._build_ui()
        self._process_log_queue()
        self._check_engines()
    
    def _build_ui(self):
        """Build the user interface"""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # === Left Panel ===
        left = ttk.Frame(main, width=350)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)
        
        # Input Section
        input_frame = ttk.LabelFrame(left, text="Input Files", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="📄 Add Files", command=self._add_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="📂 Add Folder", command=self._add_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="🗑️ Clear", command=self._clear_files).pack(side=tk.LEFT)
        
        self.file_listbox = tk.Listbox(input_frame, height=6, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill=tk.X, pady=(10, 0))
        
        self.file_count_label = ttk.Label(input_frame, text="0 files selected")
        self.file_count_label.pack(anchor=tk.W)
        
        # Engine Section
        engine_frame = ttk.LabelFrame(left, text="OCR Engine", padding=10)
        engine_frame.pack(fill=tk.X, pady=(0, 10))
        
        engine_row = ttk.Frame(engine_frame)
        engine_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(engine_row, text="Engine:").pack(side=tk.LEFT)
        self.engine_var = tk.StringVar(value="tesseract")
        engines = ["tesseract"]
        if HAS_EASYOCR:
            engines.append("easyocr")
        self.engine_combo = ttk.Combobox(engine_row, textvariable=self.engine_var,
                                          values=engines, state="readonly", width=15)
        self.engine_combo.pack(side=tk.LEFT, padx=5)
        
        lang_row = ttk.Frame(engine_frame)
        lang_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(lang_row, text="Language:").pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="English")
        self.lang_combo = ttk.Combobox(lang_row, textvariable=self.lang_var,
                                        values=list(LANGUAGES.keys()), state="readonly", width=20)
        self.lang_combo.pack(side=tk.LEFT, padx=5)
        
        # Options
        self.preprocess_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(engine_frame, text="Preprocess images (enhance contrast)",
                       variable=self.preprocess_var).pack(anchor=tk.W)
        
        self.layout_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(engine_frame, text="Preserve layout (slower)",
                       variable=self.layout_var).pack(anchor=tk.W)
        
        # Output Section
        output_frame = ttk.LabelFrame(left, text="Output", padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        dir_row = ttk.Frame(output_frame)
        dir_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(dir_row, text="Folder:").pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value="./outputs")
        ttk.Entry(dir_row, textvariable=self.output_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(dir_row, text="📁", command=self._browse_output, width=3).pack(side=tk.LEFT)
        
        format_row = ttk.Frame(output_frame)
        format_row.pack(fill=tk.X)
        ttk.Label(format_row, text="Format:").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="txt")
        formats = ["txt", "json"]
        if HAS_DOCX:
            formats.append("docx")
        ttk.Combobox(format_row, textvariable=self.format_var,
                     values=formats, state="readonly", width=10).pack(side=tk.LEFT, padx=5)
        
        # Process Button
        self.process_btn = ttk.Button(left, text="📝 Extract Text", command=self._start_processing)
        self.process_btn.pack(fill=tk.X, pady=(10, 0))
        
        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(left, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(left, textvariable=self.status_var).pack(anchor=tk.W, pady=(5, 0))
        
        # Engine status
        self.engine_status = ttk.Label(left, text="", foreground="gray")
        self.engine_status.pack(anchor=tk.W, pady=(10, 0))
        
        # === Right Panel: Preview/Results ===
        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Results text
        results_frame = ttk.LabelFrame(right, text="Extracted Text Preview", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        from tkinter import scrolledtext
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Log
        log_frame = ttk.LabelFrame(right, text="Log", padding=5)
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.X)
    
    def _check_engines(self):
        """Check available OCR engines"""
        status = []
        
        if HAS_TESSERACT:
            try:
                # Test Tesseract
                pytesseract.get_tesseract_version()
                status.append("✓ Tesseract")
            except:
                status.append("⚠ Tesseract (not configured)")
        else:
            status.append("✗ Tesseract (pip install pytesseract)")
        
        if HAS_EASYOCR:
            status.append("✓ EasyOCR")
        else:
            status.append("○ EasyOCR (optional: pip install easyocr)")
        
        if HAS_PYMUPDF:
            status.append("✓ PDF support")
        else:
            status.append("✗ PDF (pip install pymupdf)")
        
        self.engine_status.config(text="\n".join(status))
        
        # Log
        for s in status:
            self._log(s)
        self._log("")
    
    def _add_files(self):
        """Add files"""
        files = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[
                ("Supported files", "*.jpg *.jpeg *.png *.tiff *.tif *.bmp *.pdf"),
                ("Images", "*.jpg *.jpeg *.png *.tiff *.tif *.bmp"),
                ("PDFs", "*.pdf"),
                ("All files", "*.*")
            ]
        )
        
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))
        
        self._update_file_count()
    
    def _add_folder(self):
        """Add folder"""
        folder = filedialog.askdirectory(title="Select Folder")
        if not folder:
            return
        
        all_exts = SUPPORTED_IMAGES | SUPPORTED_PDFS
        
        for filename in os.listdir(folder):
            ext = os.path.splitext(filename)[1].lower()
            if ext in all_exts:
                filepath = os.path.join(folder, filename)
                if filepath not in self.input_files:
                    self.input_files.append(filepath)
                    self.file_listbox.insert(tk.END, filename)
        
        self._update_file_count()
    
    def _clear_files(self):
        """Clear files"""
        self.input_files.clear()
        self.file_listbox.delete(0, tk.END)
        self._update_file_count()
    
    def _update_file_count(self):
        """Update count"""
        count = len(self.input_files)
        self.file_count_label.config(text=f"{count} file{'s' if count != 1 else ''} selected")
    
    def _browse_output(self):
        """Browse output"""
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_var.set(path)
    
    def _log(self, message: str):
        """Log message"""
        self.log_queue.put(message)
    
    def _process_log_queue(self):
        """Process log"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        self.root.after(100, self._process_log_queue)
    
    def _start_processing(self):
        """Start processing"""
        if self.running:
            messagebox.showwarning("Busy", "Processing is already running")
            return
        
        if not self.input_files:
            messagebox.showwarning("No Input", "Please add files to process")
            return
        
        self.running = True
        self.process_btn.config(state=tk.DISABLED)
        self.results_text.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._processing_thread)
        thread.daemon = True
        thread.start()
    
    def _processing_thread(self):
        """Background processing"""
        try:
            # Build config
            lang_name = self.lang_var.get()
            lang_code = LANGUAGES.get(lang_name, "eng")
            
            config = {
                'ocr_engine': self.engine_var.get(),
                'language': lang_code,
                'preprocess': self.preprocess_var.get(),
                'preserve_layout': self.layout_var.get(),
                'output_format': self.format_var.get(),
                'dpi': 300,
            }
            
            output_dir = self.output_var.get()
            
            # Initialize extractor
            extractor = OCRExtractor(config)
            extractor.initialize(callback=self._log)
            
            # Process files
            stats = extractor.process_batch(
                self.input_files,
                output_dir,
                callback=self._log
            )
            
            # Show results preview
            if stats['results']:
                first_success = next((r for r in stats['results'] if r['status'] == 'success'), None)
                if first_success:
                    with open(first_success['output'], 'r', encoding='utf-8') as f:
                        preview = f.read()[:5000]
                        self.root.after(0, lambda: self.results_text.insert(tk.END, preview))
            
            self.progress_var.set(100)
            self._log(f"\nComplete!")
            self._log(f"Success: {stats['success']}, Failed: {stats['failed']}")
            self._log(f"Total words extracted: {stats['total_words']}")
            self.status_var.set("Complete!")
            
            # Open output folder
            if os.path.exists(output_dir) and sys.platform == 'win32':
                os.startfile(output_dir)
            
        except Exception as e:
            self._log(f"Error: {e}")
            self.status_var.set(f"Error: {e}")
        finally:
            self.running = False
            self.process_btn.config(state=tk.NORMAL)


# =============================================================================
# Main
# =============================================================================

def main():
    if not HAS_PIL:
        print("ERROR: Pillow not installed!")
        print("Run: pip install Pillow")
        sys.exit(1)
    
    root = tk.Tk()
    app = OCRExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
