"""
REST endpoint for document ingestion (replaces the old Gradio Ingest tab).
Uploaded files are saved to data/raw, then run through ingestion.pipeline.run_ingestion.
"""

import os

from fastapi import APIRouter, UploadFile, File

from ingestion.pipeline import run_ingestion
from config import RAW_DATA_DIR

router = APIRouter()


@router.post("/ingest")
async def ingest_files(files: list[UploadFile] = File(...)) -> dict:
    for file in files:
        destination = os.path.join(RAW_DATA_DIR, file.filename)
        with open(destination, "wb") as f:
            f.write(await file.read())

    await run_ingestion(RAW_DATA_DIR)
    return {"status": "Ingestion complete."}
