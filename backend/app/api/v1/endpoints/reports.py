"""
Reports API Router — Milestone 4 Step 5
Provides endpoints to export PDF and Excel analytics reports.
Strict team isolation & authentication enforced.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api import deps
from app.db.mongo import get_mongo_db
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/pdf")
async def export_pdf_report(
    team_id: int = Query(..., description="ID of the team workspace"),
    days: int = Query(30, ge=1, le=365, description="Date range in days (1 to 365)"),
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """
    Generate and download a PDF analytics report for the specified team workspace.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days parameter must be between 1 and 365")

    # Gather data (raises 403/404 if user lacks team access)
    data = await ReportService.gather_report_data(db, mongo_db, current_user, team_id, days)

    # Generate PDF bytes
    pdf_bytes = ReportService.generate_pdf_report(data)

    filename = f"socialpilot_report_team_{team_id}_{days}d.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/excel")
async def export_excel_report(
    team_id: int = Query(..., description="ID of the team workspace"),
    days: int = Query(30, ge=1, le=365, description="Date range in days (1 to 365)"),
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """
    Generate and download an Excel (.xlsx) analytics report for the specified team workspace.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days parameter must be between 1 and 365")

    # Gather data (raises 403/404 if user lacks team access)
    data = await ReportService.gather_report_data(db, mongo_db, current_user, team_id, days)

    # Generate Excel bytes
    excel_bytes = ReportService.generate_excel_report(data)

    filename = f"socialpilot_report_team_{team_id}_{days}d.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
