"""Pricing module for an e-commerce system.

Order of operations for final_price:
1. Apply promotions (before tax, per business rules)
2. Calculate tax on the post-promotion amount
3. Apply discount on the post-tax amount
"""

from typing import Optional


def calculate_tax(amount: float, tax_rate: float) -> float:
    """Calculate tax for a given amount and rate."""
    return round(amount * tax_rate, 2)


def calculate_discount(amount: float, discount_pct: float) -> float:
    """Calculate discount amount for a given amount and percentage."""
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount percentage must be between 0 and 100")
    return round(amount * (discount_pct / 100), 2)


def apply_promotion(amount: float, promo_code: Optional[str]) -> float:
    """Apply a promotion to the amount. Returns the reduced amount."""
    if promo_code is None:
        return amount
    promotions = {
        "SAVE10": 0.10,   # 10% off
        "SAVE20": 0.20,   # 20% off
        "VIP50": 0.50,    # 50% off
    }
    if promo_code.upper() in promotions:
        discount_rate = promotions[promo_code.upper()]
        return round(amount * (1 - discount_rate), 2)
    return amount


def final_price(
    amount: float,
    tax_rate: float,
    discount_pct: float = 0.0,
    promo_code: Optional[str] = None,
) -> float:
    """Compute the final price after promotions, tax, and discount.

    Business rules:
    1. Promotions apply to the base amount (before tax)
    2. Tax applies to the post-promotion amount
    3. Discounts apply to the post-tax amount

    Returns the final price the customer pays.
    """
    # Step 1: Apply promotion (before tax)
    after_promo = apply_promotion(amount, promo_code)

    # Step 2: Calculate tax on post-promotion amount
    tax = calculate_tax(after_promo, tax_rate)

    # BUG: The discount is calculated on the ORIGINAL amount instead
    # of the post-tax amount (after_promo + tax). This means:
    # - For orders with promotions: the discount is larger than it should be
    #   because it's calculated on the pre-promotion amount
    # - For orders without promotions: the discount looks correct because
    #   amount == after_promo, but it's still applied to the wrong base
    #   (pre-tax instead of post-tax)
    discount = calculate_discount(amount, discount_pct)  # BUG: should be after_promo + tax

    # Step 4: Final price = post-promo + tax - discount
    total = after_promo + tax - discount
    return round(total, 2)
