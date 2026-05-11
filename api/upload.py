from pathlib import Path
from uuid import uuid4
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.utils.file_extractors import extract_documents_from_path

router = APIRouter()

UPLOAD_DIR = Path("tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="ファイルがありません。")

    uploaded_files = []
    documents = []

    for file in files:
        if not file.filename:
            continue

        safe_name = Path(file.filename).name
        unique_name = f"{uuid4().hex}_{safe_name}"
        save_path = UPLOAD_DIR / unique_name

        content = await file.read()
        save_path.write_bytes(content)

        uploaded_files.append({
            "original_name": safe_name,
            "saved_name": unique_name,
            "path": str(save_path),
            "size": len(content),
        })

        extracted_docs = extract_documents_from_path(str(save_path))
        documents.extend(extracted_docs)

    return {
        "message": "uploaded",
        "count": len(uploaded_files),
        "filenames": [f["original_name"] for f in uploaded_files],
        "documents": documents,
    }

# from typing import List
# from fastapi import APIRouter, File, UploadFile

# router = APIRouter()

# @router.post("/upload")
# async def upload_files(files: List[UploadFile] = File(...)):
#     return {"filenames": [file.filename for file in files]}