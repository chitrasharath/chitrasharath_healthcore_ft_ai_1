import csv
import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.domains.reporting.incidents.schemas import IncidentAnalysisResponse
from app.domains.reporting.incidents.service import analyze_incidents_csv
from app.domains.reporting.incidents.store import last_analysis_store

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/analyze", response_model=IncidentAnalysisResponse)
async def analyze_incidents(file: UploadFile = File(...)) -> IncidentAnalysisResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A CSV file is required.")

    content = await file.read()
    try:
        return analyze_incidents_csv(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to analyze incidents file.") from exc


@router.get("/results/export")
async def export_last_analysis() -> StreamingResponse:
    stored = last_analysis_store.get()
    if stored is None:
        raise HTTPException(status_code=404, detail="No analysis available. Upload a CSV first.")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["metric", "value", "percentage"])
    writer.writeheader()
    for row in stored.export_rows:
        writer.writerow(
            {
                "metric": row["metric"],
                "value": row["value"],
                "percentage": "" if row["percentage"] is None else row["percentage"],
            }
        )

    buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="incident-analysis-export.csv"'}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)
