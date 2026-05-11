from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router
from app.api.orien import router as orien_router
from app.api.problem_reframe import router as problem_reframe_router
from app.api.kickoff import router as kickoff_router
from app.api.subquestions import router as subquestions_router
from app.api.analysis_approach import router as analysis_approach_router
from app.api.workspace import router as workspace_router
from app.api.tutorial import router as tutorial_router
from app.api.target_condition import router as target_condition_router
from app.api.research_items import router as research_items_router

from app.api.ppt_export import router as ppt_export_router
from app.api.excel_export import router as excel_export_router
from app.api import proposal_review

app = FastAPI(title="Research Planning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(orien_router)
app.include_router(problem_reframe_router)
app.include_router(kickoff_router)
app.include_router(subquestions_router)
app.include_router(analysis_approach_router)
app.include_router(workspace_router)
app.include_router(tutorial_router)
app.include_router(target_condition_router)
app.include_router(research_items_router)
app.include_router(ppt_export_router)
app.include_router(excel_export_router)
app.include_router(proposal_review.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Research Planning API is running"}