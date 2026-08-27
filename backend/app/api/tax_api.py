from fastapi import APIRouter

from app.services.tax_comparator import compare_tax


router = APIRouter(prefix="/tax", tags=["Tax"])


@router.get("/check")
def check_tax(
    amount: float,
    tax_rate: float,
    recorded_tax: float
):
    result = compare_tax(
        amount,
        tax_rate,
        recorded_tax
    )

    return result