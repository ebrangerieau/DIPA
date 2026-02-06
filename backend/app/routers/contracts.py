"""
Router pour la gestion des contrats (CRUD).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.contract import Contract


# Schémas Pydantic pour les requêtes/réponses
class ContractCreate(BaseModel):
    """Schéma pour la création d'un contrat."""
    name: str = Field(..., min_length=1, max_length=255)
    supplier: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    start_date: date
    end_date: date
    notice_period_days: int = Field(..., ge=0)
    sharepoint_file_url: str | None = None


class ContractUpdate(BaseModel):
    """Schéma pour la mise à jour d'un contrat."""
    name: str | None = None
    supplier: str | None = None
    amount: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    notice_period_days: int | None = None
    sharepoint_file_url: str | None = None
    status: str | None = None


class ContractResponse(BaseModel):
    """Schéma de réponse pour un contrat."""
    id: UUID
    name: str
    supplier: str
    amount: float
    start_date: date
    end_date: date
    notice_period_days: int
    sharepoint_file_url: str | None
    status: str
    notice_start_date: date
    days_until_end: int
    is_in_notice_period: bool
    is_expired: bool
    computed_status: str
    timeline_color: str
    
    class Config:
        from_attributes = True


class TimelineItem(BaseModel):
    """Élément pour la timeline."""
    id: str
    type: str  # "contract" ou "ticket"
    title: str
    start: str  # ISO format
    end: str | None  # ISO format
    color: str
    group: int = 0  # Pour le smart stacking
    metadata: dict = {}


# Router
router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("/", response_model=List[ContractResponse])
async def list_contracts(
    skip: int = 0,
    limit: int = 100,
    status_filter: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Liste tous les contrats avec pagination optionnelle.
    
    Args:
        skip: Nombre d'éléments à sauter
        limit: Nombre maximum d'éléments à retourner
        status_filter: Filtre optionnel par statut
        db: Session de base de données
    
    Returns:
        List[ContractResponse]: Liste des contrats
    """
    query = db.query(Contract)
    
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    
    contracts = query.offset(skip).limit(limit).all()
    return contracts


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: UUID, db: Session = Depends(get_db)):
    """
    Récupère un contrat spécifique par son ID.
    
    Args:
        contract_id: UUID du contrat
        db: Session de base de données
    
    Returns:
        ContractResponse: Détails du contrat
    
    Raises:
        HTTPException: 404 si le contrat n'existe pas
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contrat {contract_id} non trouvé"
        )
    
    return contract


@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(contract_data: ContractCreate, db: Session = Depends(get_db)):
    """
    Crée un nouveau contrat.
    
    Args:
        contract_data: Données du contrat
        db: Session de base de données
    
    Returns:
        ContractResponse: Contrat créé
    """
    # Validation : end_date doit être après start_date
    if contract_data.end_date <= contract_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de fin doit être postérieure à la date de début"
        )
    
    contract = Contract(**contract_data.model_dump())
    db.add(contract)
    db.commit()
    db.refresh(contract)
    
    return contract


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: UUID,
    contract_data: ContractUpdate,
    db: Session = Depends(get_db)
):
    """
    Met à jour un contrat existant.
    
    Args:
        contract_id: UUID du contrat
        contract_data: Données à mettre à jour
        db: Session de base de données
    
    Returns:
        ContractResponse: Contrat mis à jour
    
    Raises:
        HTTPException: 404 si le contrat n'existe pas
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contrat {contract_id} non trouvé"
        )
    
    # Mise à jour des champs non-null
    update_data = contract_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    
    db.commit()
    db.refresh(contract)
    
    return contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(contract_id: UUID, db: Session = Depends(get_db)):
    """
    Supprime un contrat.
    
    Args:
        contract_id: UUID du contrat
        db: Session de base de données
    
    Raises:
        HTTPException: 404 si le contrat n'existe pas
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contrat {contract_id} non trouvé"
        )
    
    db.delete(contract)
    db.commit()


@router.get("/timeline/data", response_model=List[TimelineItem])
async def get_timeline_data(db: Session = Depends(get_db)):
    """
    Récupère les données formatées pour la timeline.
    Inclut les contrats avec leur période de préavis.
    
    Args:
        db: Session de base de données
    
    Returns:
        List[TimelineItem]: Éléments de la timeline
    """
    contracts = db.query(Contract).all()
    timeline_items = []
    
    for contract in contracts:
        # Jalon (point) pour la date de fin
        milestone = TimelineItem(
            id=f"contract-milestone-{contract.id}",
            type="contract-milestone",
            title=f"{contract.name} - Échéance",
            start=contract.end_date.isoformat(),
            end=None,
            color=contract.timeline_color,
            metadata={
                "contract_id": str(contract.id),
                "supplier": contract.supplier,
                "amount": float(contract.amount),
                "sharepoint_url": contract.sharepoint_file_url
            }
        )
        timeline_items.append(milestone)
        
        # Barre pour la période de préavis (si applicable)
        if contract.is_in_notice_period or contract.notice_start_date >= date.today():
            notice_bar = TimelineItem(
                id=f"contract-notice-{contract.id}",
                type="contract-notice",
                title=f"{contract.name} - Préavis",
                start=contract.notice_start_date.isoformat(),
                end=contract.end_date.isoformat(),
                color=contract.timeline_color,
                metadata={
                    "contract_id": str(contract.id),
                    "supplier": contract.supplier,
                    "notice_days": contract.notice_period_days
                }
            )
            timeline_items.append(notice_bar)
    
    return timeline_items
