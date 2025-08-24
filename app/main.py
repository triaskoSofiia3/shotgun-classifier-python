from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Tuple
from app.model import classify_text
import os
import tempfile
import mimetypes
from urllib.parse import urlparse
import re
import requests
import logging
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:
    boto3 = None
    BotoCoreError = Exception
    ClientError = Exception

if boto3 is None:
    raise ImportError("boto3 is required for S3 access but is not installed.")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClassifyRequest(BaseModel):
    s3_url: str
    candidate_labels: List[str]

class ClassifyResponse(BaseModel):
    category: str
    confidence: float


def _guess_extension_from_headers(headers: dict) -> Optional[str]:
    content_disposition = headers.get("content-disposition") or headers.get("Content-Disposition")
    if content_disposition:
        filename_match = re.search(r'filename\*=UTF-8\'\'([^;]+)|filename="?([^";]+)"?', content_disposition)
        filename = filename_match.group(1) if filename_match and filename_match.group(1) else (
            filename_match.group(2) if filename_match else None
        )
        if filename:
            ext = os.path.splitext(filename)[1]
            if ext:
                return ext.lower()

    content_type = headers.get("content-type") or headers.get("Content-Type")
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed.lower()
    return None


def _download_to_temp(url: str) -> Tuple[str, Optional[str]]:
    parsed = urlparse(url)
    suffix = os.path.splitext(parsed.path)[1].lower()

    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or "") as tmp:
                s3_client.download_fileobj(bucket, key, tmp)
                return tmp.name, None
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"Failed to download from S3: {exc}")

    if parsed.scheme in {"http", "https"}:
        try:
            with requests.get(url, stream=True, timeout=30) as resp:
                if resp.status_code >= 400:
                    raise HTTPException(status_code=resp.status_code, detail=f"Failed to download file: HTTP {resp.status_code}")
                if not suffix:
                    guessed = _guess_extension_from_headers(resp.headers)
                    if guessed:
                        suffix = guessed
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or "") as tmp:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            tmp.write(chunk)
                    return tmp.name, resp.headers.get("content-type")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to download file: {exc}")

    raise HTTPException(status_code=400, detail="Unsupported URL scheme. Use s3://, http:// or https://")


def _extract_text_from_file(file_path: str, content_type: Optional[str]) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if not ext and content_type:
        guessed_from_ct = mimetypes.guess_extension((content_type or "").split(";")[0].strip())
        if guessed_from_ct:
            ext = guessed_from_ct.lower()

    # TXT / LOG
    if ext in {".txt", ".log"}:
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1", errors="ignore")
            return text[:5000]
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to read text file: {exc}")

    # EPUB
    if ext == ".epub":
        try:
            from ebooklib import epub
            from bs4 import BeautifulSoup

            book = epub.read_epub(file_path)
            texts = []
            for item in book.get_items():
                if item.get_type() == 9:  # DOCUMENT
                    soup = BeautifulSoup(item.get_body_content(), "html.parser")
                    texts.append(soup.get_text())
            return "\n".join(texts).strip()[:5000]
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to extract text from EPUB: {exc}")

    # PDF
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            texts = []
            for i, page in enumerate(doc):
                if i > 5:
                    break
                texts.append(page.get_text("text"))
            return "\n".join(texts).strip()[:5000]
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to extract text from PDF: {exc}")

    # DOCX
    if ext == ".docx":
        try:
            import mammoth
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
            return (result.value or "").strip()[:5000]
        except ImportError:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            return "\n".join(paragraphs).strip()[:5000]
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to extract text from DOCX: {exc}")

    raise HTTPException(status_code=415, detail=f"Unsupported file type: '{ext or 'unknown'}'. Supported: txt, pdf, docx, epub")


@app.post("/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest, request: Request):
    logger.info("Received request from %s", request.client.host)
    logger.info("Request data: %s", req.dict())

    if not req.s3_url or not req.s3_url.strip():
        raise HTTPException(status_code=400, detail="s3_url is required")

    if not req.candidate_labels:
        raise HTTPException(status_code=400, detail="No candidate labels provided")

    file_path = None
    try:
        file_path, content_type = _download_to_temp(req.s3_url.strip())
        extracted_text = _extract_text_from_file(file_path, content_type)
        if not extracted_text.strip():
            logger.error("Extracted text is empty")
            raise HTTPException(status_code=422, detail="Extracted text is empty")

        result = classify_text(extracted_text, req.candidate_labels)
        logger.info("Classification result: %s", result)
        return result

    except HTTPException as e:
        logger.error("HTTPException: %s", e.detail)
        raise
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass