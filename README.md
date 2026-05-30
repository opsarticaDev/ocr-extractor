# OCR Extractor

Extract text from images and PDFs using OCR (Optical Character Recognition).

---

## Quick Start

1. **Install Tesseract** (see Installation below)
2. **Double-click** `Launch OCR Extractor.bat`
3. **Add** images or PDFs
4. **Select** language
5. **Click** "Extract Text"

---

## Features

| Feature | Description |
|---------|-------------|
| **Multiple Engines** | Tesseract (default) or EasyOCR (deep learning) |
| **100+ Languages** | Full language support via Tesseract |
| **PDF Support** | Digital PDFs (text extraction) + Scanned PDFs (OCR) |
| **Batch Processing** | Process entire folders |
| **Multiple Outputs** | TXT, JSON, DOCX formats |
| **Image Preprocessing** | Automatic enhancement for better OCR |

---

## Installation

### Step 1: Install Tesseract OCR Engine

**Windows (recommended):**
```
winget install UB-Mannheim.TesseractOCR
```

Or download installer from:
https://github.com/UB-Mannheim/tesseract/wiki

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt install tesseract-ocr
```

### Step 2: Install Python Dependencies

Run `Install.bat` or manually:

```bash
# Core (required)
pip install Pillow numpy pymupdf pytesseract

# Optional: Deep learning OCR
pip install easyocr

# Optional: DOCX export
pip install python-docx
```

### Step 3: Additional Languages (Tesseract)

Download language data from:
https://github.com/tesseract-ocr/tessdata

Place `.traineddata` files in Tesseract's `tessdata` folder.

---

## OCR Engines

### Tesseract (Default)

| Pros | Cons |
|------|------|
| Fast | Requires clean images |
| 100+ languages | Struggles with handwriting |
| Well-documented | Needs preprocessing for best results |
| Small footprint | |

**Best for**: Printed documents, scanned books, forms

### EasyOCR (Optional)

| Pros | Cons |
|------|------|
| Better accuracy | Larger model downloads |
| Handles scene text | Slower on CPU |
| Less preprocessing needed | Fewer languages |
| Modern deep learning | |

**Best for**: Photos with text, screenshots, varied fonts

---

## Supported Formats

### Input
- **Images**: JPG, JPEG, PNG, TIFF, TIF, BMP, WebP, GIF
- **Documents**: PDF (digital and scanned)

### Output
- **TXT**: Plain text file
- **JSON**: Structured data with metadata (confidence, word count, etc.)
- **DOCX**: Formatted Word document

---

## Language Support

Common languages (Tesseract codes):

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | eng | Chinese (Simp) | chi_sim |
| Spanish | spa | Chinese (Trad) | chi_tra |
| French | fra | Japanese | jpn |
| German | deu | Korean | kor |
| Italian | ita | Arabic | ara |
| Portuguese | por | Hindi | hin |
| Russian | rus | Vietnamese | vie |

For full list: https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html

---

## Settings

### Preprocessing
Enhances images before OCR:
- Converts to grayscale
- Increases contrast
- Light sharpening

Enable for scanned documents, disable for clean digital images.

### Preserve Layout
Attempts to maintain original text positioning.
- Slower processing
- Better for forms, tables
- May not work perfectly for all layouts

### DPI (PDF Processing)
Resolution for converting PDF pages to images:
- 150 DPI: Fast, lower quality
- 300 DPI: Balanced (default)
- 600 DPI: High quality, slower

---

## Tips for Best Results

### Image Quality
- Higher resolution = better OCR
- Minimum 300 DPI for documents
- Avoid heavy JPEG compression

### Preprocessing
- Enable for scanned documents
- Disable for screenshots/clean images
- Manual preprocessing can help difficult images

### Language Selection
- Always select correct language
- Some languages need additional data files
- Mixed-language documents may need multiple passes

### PDF Handling
- Digital PDFs: Text extracted directly (fastest)
- Scanned PDFs: OCR applied per page
- Tool auto-detects which method to use

---

## Use Cases

### Document Digitization
```
1. Scan documents at 300+ DPI
2. Add to OCR Extractor
3. Select appropriate language
4. Export as DOCX for editing
```

### Receipt/Invoice Processing
```
1. Photo receipts with phone
2. Add images to OCR Extractor
3. Export as JSON for data extraction
4. Parse JSON for specific fields
```

### Book Scanning
```
1. Scan book pages
2. Batch process entire folder
3. Enable layout preservation
4. Export as TXT for e-reader
```

### Screenshot Text Extraction
```
1. Take screenshots
2. Disable preprocessing (clean images)
3. Extract text quickly
```

---

## Performance

### Processing Times (per page)

| Content Type | Tesseract | EasyOCR |
|--------------|-----------|---------|
| Clean text | 1-2 sec | 3-5 sec |
| Scanned document | 2-5 sec | 5-10 sec |
| Complex layout | 3-8 sec | 8-15 sec |

### Accuracy Expectations

| Content Type | Expected Accuracy |
|--------------|-------------------|
| Typed text, clean | 95-99% |
| Scanned documents | 90-98% |
| Low quality scans | 70-90% |
| Handwriting | 40-70% |
| Scene text (signs) | 80-95% (EasyOCR better) |

---

## Integration with AI Toolkit

### Workflow: Document Processing
```
1. OCR Extractor → Extract text from scans
2. Content Repurpose → Summarize documents
3. Semantic Search → Index extracted text
```

### Workflow: Data Entry Automation
```
1. OCR Extractor → Extract from forms
2. Export as JSON
3. Process with custom scripts
```

---

## Troubleshooting

### "Tesseract not found"
- Install Tesseract OCR engine
- Check it's in your PATH
- Or set path in Python:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

### Poor OCR quality
- Increase image resolution
- Enable preprocessing
- Try EasyOCR for difficult images
- Check language selection

### "Language not found"
- Download language data file
- Place in Tesseract's tessdata folder

### PDF extraction fails
- Install PyMuPDF: `pip install pymupdf`
- Check PDF isn't corrupted
- Try opening in PDF viewer first

### Out of memory (EasyOCR)
- Use Tesseract instead
- Process fewer files at once
- Close other applications

---

## Research Applications

OCR Extractor serves as a text extraction layer in academic research data pipelines. Scanned documents, archival materials, and image-based datasets can be converted to machine-readable text for downstream analysis. Batch processing supports large-scale corpus construction from document scans, and JSON output provides structured metadata (confidence scores, word counts) suitable for quality filtering in research workflows.

Typical research pipeline integration:

1. Acquire scanned source documents (archival, legal, medical records)
2. Batch extract via OCR Extractor with language-appropriate models
3. Export as JSON for programmatic quality assessment
4. Feed cleaned text into NLP, classification, or search pipelines

---

## Folder Structure

```
OCRExtractor/
├── Launch OCR Extractor.bat  ← Start here
├── OCRExtractor.py           ← Main application
├── Install.bat               ← Run first
├── README.md                 ← This file
├── inputs/                   ← Place files here
└── outputs/                  ← Extracted text saved here
```

---

## Version

OCR Extractor v1.0
Built: January 2025

Part of AI Toolkit
