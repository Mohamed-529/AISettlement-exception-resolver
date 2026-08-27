def compare_tax(amount: float, tax_rate: float, recorded_tax: float):

    expected_tax = amount * (tax_rate / 100)

    difference = expected_tax - recorded_tax

    if abs(difference) < 0.01:
        status = "matched"
    else:
        status = "mismatch"

    return {
        "expected_tax": round(expected_tax, 2),
        "recorded_tax": round(recorded_tax, 2),
        "difference": round(difference, 2),
        "status": status
    }