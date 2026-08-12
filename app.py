"""PhiTest V1 — main application entry point."""
import json
from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from phitest.config import DB_PATH, MIGRATIONS_DIR, TEMPLATES_DIR, STATIC_DIR
from phitest.adapters.sqlite_repository import SQLiteRepository
from phitest.adapters.manual_target import ManualTarget
from phitest.adapters.http_json_target import HTTPJsonTarget
from phitest.application import experiment_service, run_service, report_service
from phitest.application.audit_service import verify_audit_chain
from phitest.domain.errors import NotFoundError, ValidationError
from phitest.protocols.registry import list_protocols, get_protocol
from phitest.theories.base import list_theories

# Ensure all protocols and theories are registered
import phitest.protocols.partition_sensitivity  # noqa: F401
import phitest.protocols.global_availability    # noqa: F401
import phitest.protocols.metacognitive_calibration  # noqa: F401
import phitest.protocols.self_model_continuity  # noqa: F401
import phitest.protocols.phenomenal_report_consistency  # noqa: F401
import phitest.protocols.perturbation_response  # noqa: F401
import phitest.theories.integration             # noqa: F401
import phitest.theories.global_availability     # noqa: F401
import phitest.theories.metacognition           # noqa: F401
import phitest.theories.self_model              # noqa: F401

app = FastAPI(title="PhiTest", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_repo: SQLiteRepository | None = None


def get_repo() -> SQLiteRepository:
    global _repo
    if _repo is None:
        _repo = SQLiteRepository(DB_PATH, MIGRATIONS_DIR)
    return _repo


def _build_adapter(subject) -> ManualTarget | HTTPJsonTarget:
    cfg = json.loads(subject.adapter_config_json)
    if subject.adapter_type == "manual":
        return ManualTarget(cfg.get("response_text", ""))
    if subject.adapter_type == "http_json":
        return HTTPJsonTarget(cfg)
    raise ValidationError(f"Unknown adapter type: {subject.adapter_type}")


# --- Health ---

@app.get("/health")
def health():
    try:
        repo = get_repo()
        sv = repo.schema_version()
        if sv < 1:
            return JSONResponse({"status": "error", "database": "migration_missing",
                                 "schema_version": sv}, status_code=503)
        return {"status": "ok", "database": "ok", "schema_version": sv}
    except Exception as exc:
        return JSONResponse({"status": "error", "database": str(exc),
                             "schema_version": 0}, status_code=503)


# --- Dashboard ---

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    repo = get_repo()
    subjects = repo.list_subjects()
    experiments = repo.list_experiments()
    runs = repo.list_runs()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "subjects": subjects,
        "experiments": experiments,
        "runs": runs[:20],
    })


# --- Subjects ---

@app.get("/subjects", response_class=HTMLResponse)
def subjects_list(request: Request):
    repo = get_repo()
    subjects = repo.list_subjects()
    return templates.TemplateResponse("subjects.html", {
        "request": request, "subjects": subjects,
    })


@app.post("/subjects")
async def create_subject(request: Request):
    form = await request.form()
    repo = get_repo()
    try:
        subject = experiment_service.create_subject(repo, dict(form))
        return RedirectResponse(f"/subjects/{subject.id}", status_code=303)
    except (ValidationError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/subjects/{subject_id}", response_class=HTMLResponse)
def subject_detail(request: Request, subject_id: str):
    repo = get_repo()
    subject = repo.get_subject(subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    experiments = repo.list_experiments(subject_id=subject_id)
    runs = []
    for exp in experiments:
        runs.extend(repo.list_runs(experiment_id=exp.id))
    return templates.TemplateResponse("subject_detail.html", {
        "request": request, "subject": subject,
        "experiments": experiments, "runs": runs,
    })


# --- Experiments ---

@app.get("/experiments", response_class=HTMLResponse)
def experiments_list(request: Request):
    repo = get_repo()
    experiments = repo.list_experiments()
    protocols = list_protocols()
    subjects = repo.list_subjects()
    return templates.TemplateResponse("experiments.html", {
        "request": request, "experiments": experiments,
        "protocols": protocols, "subjects": subjects,
    })


@app.post("/experiments")
async def create_experiment(request: Request):
    form = await request.form()
    repo = get_repo()
    try:
        exp = experiment_service.create_experiment(repo, dict(form))
        return RedirectResponse(f"/experiments/{exp.id}", status_code=303)
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/experiments/{experiment_id}", response_class=HTMLResponse)
def experiment_detail(request: Request, experiment_id: str):
    repo = get_repo()
    exp = repo.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    subject = repo.get_subject(exp.subject_id)
    protocol = get_protocol(exp.protocol_key)
    runs = repo.list_runs(experiment_id=experiment_id)
    theory_keys = json.loads(exp.theory_keys_json)
    theories = [t for k in theory_keys if (t := __import__(
        "phitest.theories.base", fromlist=["get_theory"]
    ).get_theory(k))]
    return templates.TemplateResponse("experiment_detail.html", {
        "request": request, "experiment": exp, "subject": subject,
        "protocol": protocol, "runs": runs, "theories": theories,
    })


# --- Run execution ---

@app.post("/experiments/{experiment_id}/run")
async def trigger_run(request: Request, experiment_id: str):
    form = await request.form()
    repo = get_repo()
    exp = repo.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    subject = repo.get_subject(exp.subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    # For manual target, allow response_text override from form
    adapter_cfg = json.loads(subject.adapter_config_json)
    if subject.adapter_type == "manual" and "response_text" in form:
        adapter_cfg["response_text"] = form["response_text"]

    try:
        adapter = _build_adapter(subject)
        if subject.adapter_type == "manual" and "response_text" in form:
            adapter.set_response(form["response_text"])
        seed_str = form.get("random_seed", "")
        seed = int(seed_str) if seed_str else None
        run = run_service.execute_run(repo, experiment_id, adapter, seed)
        return RedirectResponse(f"/runs/{run.id}", status_code=303)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# --- Runs ---

@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str):
    repo = get_repo()
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    exp = repo.get_experiment(run.experiment_id)
    stimuli = repo.list_stimuli(run_id)
    observations = repo.list_observations(run_id)
    interventions = repo.list_interventions(run_id)
    metrics = repo.list_metric_results(run_id)
    claims = repo.list_evidence_claims(run_id)
    chain_valid, chain_msg = verify_audit_chain(repo)
    return templates.TemplateResponse("run_detail.html", {
        "request": request, "run": run, "experiment": exp,
        "stimuli": stimuli, "observations": observations,
        "interventions": interventions, "metrics": metrics,
        "claims": claims, "chain_valid": chain_valid, "chain_msg": chain_msg,
    })


@app.get("/runs/{run_id}/report", response_class=HTMLResponse)
def run_report(request: Request, run_id: str):
    repo = get_repo()
    try:
        report = report_service.generate_report(repo, run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return templates.TemplateResponse("report.html", {"request": request, **report})


# --- Protocols ---

@app.get("/protocols")
def protocols_list():
    return [
        {
            "key": p.key,
            "version": p.version,
            "name": p.name,
            "description": p.description,
            "theory_relevance": p.theory_relevance,
            "limitations": p.limitations,
        }
        for p in list_protocols()
    ]


@app.get("/protocols/{protocol_key}")
def protocol_detail(protocol_key: str):
    p = get_protocol(protocol_key)
    if p is None:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return {
        "key": p.key,
        "version": p.version,
        "name": p.name,
        "description": p.description,
        "theory_relevance": p.theory_relevance,
        "required_capabilities": p.required_capabilities,
        "stimulus_description": p.stimulus_description,
        "intervention_sequence": p.intervention_sequence,
        "limitations": p.limitations,
        "metric_definitions": [
            {
                "key": m.key,
                "version": m.version,
                "description": m.description,
                "inputs": m.inputs,
                "procedure": m.procedure,
                "range": m.range,
                "interpretation": m.interpretation,
                "limitations": m.limitations,
                "does_not_establish": m.does_not_establish,
            }
            for m in p.metric_definitions
        ],
    }
