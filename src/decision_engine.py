from __future__ import annotations


class DecisionEngine:
    """Evaluate whether a current price should trigger an alert."""

    def evaluate(
        self,
        route: str,
        current_price: float,
        previous_price: float | None = None,
        historical_min: float | None = None,
        target_price: float | None = None,
    ) -> dict:
        if historical_min is None:
            historical_min = current_price

        alert = False
        reason = "no_alert"

        if current_price < historical_min:
            alert = True
            reason = "new_all_time_low"
        elif target_price is not None and current_price <= target_price:
            alert = True
            reason = "target_hit"
        elif previous_price is not None and current_price <= previous_price * 0.90:
            alert = True
            reason = "significant_drop"
        elif previous_price is not None and current_price >= previous_price * 1.15:
            alert = True
            reason = "price_spike"

        return {
            "route": route,
            "alert": alert,
            "reason": reason,
            "current_price": current_price,
            "previous_price": previous_price,
            "historical_min": historical_min,
            "target_price": target_price,
        }
