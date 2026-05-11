from pydantic import BaseModel


class TargetConditionRequest(BaseModel):
    orien_outline_text: str
    kickoff_text: str
    subquestions: str
    bunseki: str
    memo: str = ""


class TargetConditionResponse(BaseModel):
    target_condition_text: str