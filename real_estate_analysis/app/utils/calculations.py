def mortgage_payment(principal: float, annual_rate_pct: float, years: int) -> float:
    """Standard amortization. annual_rate_pct e.g. 4.0 for 4 %."""
    if annual_rate_pct == 0:
        return principal / (years * 12)
    r = annual_rate_pct / 100 / 12
    n = years * 12
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def mortgage_burden_pct(monthly_payment: float, monthly_salary: float) -> float:
    """Return mortgage payment as percentage of monthly salary."""
    if monthly_salary <= 0:
        return float("inf")
    return (monthly_payment / monthly_salary) * 100


def affordability_verdict(burden_pct: float) -> tuple:
    """Return (label, color) based on mortgage burden percentage."""
    if burden_pct < 30:
        return ("Dostopno", "#27AE60")
    elif burden_pct < 40:
        return ("Obremenjujoče", "#F39C12")
    else:
        return ("Nevzdržno", "#E74C3C")


def price_growth_decomposition(
    price_2015: float,
    price_2024: float,
    rate_2015: float,
    rate_2024: float,
    years: int = 20,
    polog_pct: float = 0.20,
) -> dict:
    """Decompose mortgage payment growth into price-driven vs rate-driven components."""
    principal_2015 = price_2015 * (1 - polog_pct)
    principal_2024 = price_2024 * (1 - polog_pct)

    pay_2015 = mortgage_payment(principal_2015, rate_2015, years)
    pay_2024 = mortgage_payment(principal_2024, rate_2024, years)

    # Counterfactual: 2024 price at 2015 rate (isolates price effect)
    pay_price_effect = mortgage_payment(principal_2024, rate_2015, years)

    # Counterfactual: 2015 price at 2024 rate (isolates rate effect)
    pay_rate_effect = mortgage_payment(principal_2015, rate_2024, years)

    total_change = pay_2024 - pay_2015
    price_contribution = pay_price_effect - pay_2015
    rate_contribution = pay_rate_effect - pay_2015
    interaction = total_change - price_contribution - rate_contribution

    return {
        "pay_2015": pay_2015,
        "pay_2024": pay_2024,
        "total_change": total_change,
        "price_contribution": price_contribution,
        "rate_contribution": rate_contribution,
        "interaction": interaction,
        "price_pct": price_contribution / total_change * 100 if total_change else 0,
        "rate_pct": rate_contribution / total_change * 100 if total_change else 0,
    }


def pir_score(median_price_m2: float, area_m2: float, annual_salary: float) -> float:
    """Price-to-Income Ratio: years of gross income to buy the apartment."""
    if annual_salary <= 0:
        return float("inf")
    return (median_price_m2 * area_m2) / annual_salary


def years_to_pay_salary_fraction(
    median_price_m2: float,
    area_m2: float,
    monthly_salary: float,
    fraction: float,
) -> float:
    """Years to fully pay apartment using `fraction` of monthly salary."""
    if monthly_salary <= 0 or fraction <= 0:
        return float("inf")
    total_price = median_price_m2 * area_m2
    monthly_contribution = monthly_salary * fraction
    return total_price / (monthly_contribution * 12)
