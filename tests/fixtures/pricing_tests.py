"""Test suite for the pricing module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pricing import final_price, calculate_tax, calculate_discount, apply_promotion


# ============================================================
# EXISTING TESTS (should all pass after the fix)
# ============================================================

class TestCalculateTax:
    def test_basic_tax(self):
        assert calculate_tax(100.0, 0.08) == 8.00

    def test_zero_tax(self):
        assert calculate_tax(100.0, 0.0) == 0.00

    def test_rounding(self):
        assert calculate_tax(33.33, 0.08) == 2.67


class TestCalculateDiscount:
    def test_basic_discount(self):
        assert calculate_discount(100.0, 10.0) == 10.00

    def test_zero_discount(self):
        assert calculate_discount(100.0, 0.0) == 0.00

    def test_negative_discount_raises(self):
        try:
            calculate_discount(100.0, -5.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_over_100_discount_raises(self):
        try:
            calculate_discount(100.0, 150.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestApplyPromotion:
    def test_no_promo(self):
        assert apply_promotion(100.0, None) == 100.00

    def test_save10(self):
        assert apply_promotion(100.0, "SAVE10") == 90.00

    def test_vip50(self):
        assert apply_promotion(100.0, "VIP50") == 50.00

    def test_unknown_promo(self):
        assert apply_promotion(100.0, "UNKNOWN") == 100.00


class TestFinalPriceNoPromo:
    """Tests without promotions — discount should be on post-tax amount."""

    def test_simple(self):
        # $100 + 8% tax = $108. 10% discount on $108 = $10.80. Final = $97.20
        expected = round(100.0 + 8.0 - 10.80, 2)
        assert final_price(100.0, 0.08, 10.0) == expected

    def test_no_discount(self):
        # $100 + 8% tax = $108. Final = $108
        assert final_price(100.0, 0.08, 0.0) == 108.00

    def test_zero_tax(self):
        # $100 + 0% tax = $100. 10% discount on $100 = $10. Final = $90
        assert final_price(100.0, 0.0, 10.0) == 90.00


class TestFinalPriceWithPromo:
    """Tests with promotions — this is where the bug manifests."""

    def test_promo_no_discount(self):
        # $100 - 10% promo = $90. $90 + 8% tax = $97.20. No discount. Final = $97.20
        assert final_price(100.0, 0.08, 0.0, "SAVE10") == 97.20

    def test_promo_with_discount(self):
        # $100 - 10% promo = $90. $90 + 8% tax = $97.20.
        # 10% discount should be on $97.20 = $9.72. Final = $97.20 - $9.72 = $87.48
        expected = round(97.20 - 9.72, 2)
        assert final_price(100.0, 0.08, 10.0, "SAVE10") == expected


# ============================================================
# REPRODUCTION TEST (this is the new failing test Phase 0 creates)
# ============================================================

class TestReproduceBug:
    """Reproduction test: final_price is wrong when promotion + discount combined."""

    def test_promo_plus_discount_is_correct(self):
        """
        Bug reproduction:
        $100 base, 8% tax, 10% discount, SAVE10 promo.
        
        Expected (per business rules in docstring):
        1. Promo: $100 - 10% = $90.00
        2. Tax: $90 * 8% = $7.20
        3. Post-tax amount: $90.00 + $7.20 = $97.20
        4. Discount (10% of post-tax): $97.20 * 10% = $9.72
        5. Final: $97.20 - $9.72 = $87.48
        
        Bug behavior:
        Discount is calculated on the ORIGINAL $100 instead of $97.20,
        giving $10.00 discount instead of $9.72.
        Final becomes $97.20 - $10.00 = $87.20 (off by $0.28).
        """
        result = final_price(100.0, 0.08, 10.0, "SAVE10")
        expected = 87.48
        assert result == expected, (
            f"BUG REPRODUCED: final_price(100, 0.08, 10%, 'SAVE10') = {result}, "
            f"expected {expected}. "
            f"The discount is being calculated on the wrong base amount."
        )

    def test_vip_promo_plus_discount(self):
        """
        $200 base, 8% tax, 5% discount, VIP50 promo.
        
        Expected:
        1. Promo: $200 - 50% = $100.00
        2. Tax: $100 * 8% = $8.00
        3. Post-tax: $108.00
        4. Discount (5% of post-tax): $108.00 * 5% = $5.40
        5. Final: $108.00 - $5.40 = $102.60
        
        Bug: Discount on $200 = $10.00. Final = $108 - $10 = $98.00
        """
        result = final_price(200.0, 0.08, 5.0, "VIP50")
        expected = 102.60
        assert result == expected, (
            f"BUG REPRODUCED: final_price(200, 0.08, 5%, 'VIP50') = {result}, "
            f"expected {expected}"
        )
