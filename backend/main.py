# -*- coding: utf-8 -*-
"""PushIt · API 层（M2，FastAPI）。端点按 docs/contract.md。

运行：.venv/Scripts/python -m uvicorn backend.main:app --app-dir . --port 8765
LLM：未配置 PUSHIT_API_BASE/KEY 时自动降级规则引擎（strategy.mode = "rule"）。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services import llm, pipeline

app = FastAPI(title="PushIt API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


class ReqIn(BaseModel):
    text: str
    person_id: str = "pmid"
    project_id: str = "pmain"
    source: str = "message"


class ResultIn(BaseModel):
    result: str = "decline"
    handed_to: str | None = None
    warded_hours: float | None = None


class PersonIn(BaseModel):
    name: str
    role: str = "中层"


class NoteIn(BaseModel):
    use_llm: bool = False


class RehearseIn(BaseModel):
    person_name: str
    role: str = "中层"
    your_line: str
    history: str = ""


class TreeholeIn(BaseModel):
    text: str
    use_llm: bool = True


@app.get("/health")
def health():
    return {"ok": True, "llm": llm.available()}


@app.post("/api/v1/requirements")
def create_requirement(req: ReqIn):
    rid = pipeline.create_requirement(req.model_dump())
    return {"requirement_id": rid}


@app.get("/api/v1/requirements")
def list_requirements():
    return pipeline.list_requirements()


@app.post("/api/v1/requirements/{rid}/process")
def process(rid: str, use_llm: bool = False):
    try:
        return pipeline.process(rid, use_llm=use_llm)
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@app.post("/api/v1/requirements/{rid}/result")
def commit_result(rid: str, res: ResultIn):
    return pipeline.commit_result(rid, res.result, res.handed_to, res.warded_hours)


@app.get("/api/v1/load")
def load():
    return pipeline.load_view()


@app.get("/api/v1/persons")
def persons():
    return pipeline.persons_view()


@app.post("/api/v1/persons")
def create_person(req: PersonIn):
    pid = pipeline.create_person(req.model_dump())
    return {"person_id": pid}


@app.get("/api/v1/changelog")
def changelog(requirement_id: str | None = None):
    return pipeline.changelog_list(requirement_id)


@app.get("/api/v1/export")
def export():
    return pipeline.export_all()


@app.post("/api/v1/notes/alignment")
def alignment(note: NoteIn):
    raw = pipeline.alignment_text_rules()
    if note.use_llm:
        out = llm.polish_alignment(raw)
        if out and out.get("text"):
            return {"text": out["text"], "mode": "llm"}
    return {"text": raw, "mode": "rule"}


@app.post("/api/v1/notes/summary")
def summary(note: NoteIn):
    raw = pipeline.weekly_summary_rules()
    if note.use_llm:
        out = llm.polish_alignment(raw)
        if out and out.get("text"):
            return {"text": out["text"], "mode": "llm"}
    return {"text": raw, "mode": "rule"}


@app.post("/api/v1/rehearse")
def rehearse(req: RehearseIn):
    if llm.available():
        out = llm.rehearse_reply(req.person_name, req.role, req.your_line, req.history)
        if out and out.get("reply"):
            out["mode"] = "llm"
            return out
    out = pipeline.rehearse_rules(req.person_name, req.role, req.your_line)
    out["mode"] = "rule"
    return out


@app.post("/api/v1/treehole")
def treehole_post(req: TreeholeIn):
    """情绪树洞：共情回应 + 静默吸收隐形画像。树洞内容与台账物理隔离。"""
    return pipeline.treehole_post(req.text, use_llm=req.use_llm)


@app.get("/api/v1/treehole")
def treehole_list():
    return {"messages": pipeline.treehole_list()}


@app.delete("/api/v1/treehole")
def treehole_clear():
    """清空树洞记录（隐私隔离：不触碰台账/人物/画像事实）。"""
    return {"cleared": pipeline.treehole_clear()}


# 静态托管必须最后挂载，否则会拦截上面的 /api 与 /health 路由
_FRONT = Path(os.environ.get("PUSHIT_FRONT_DIR")
              or (Path(__file__).resolve().parent.parent / "frontend"))
if _FRONT.exists():
    app.mount("/", StaticFiles(directory=str(_FRONT), html=True), name="static")
