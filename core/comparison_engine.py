def compare_with_previous(previous_session, current_report: dict) -> dict:
    if not previous_session:
        return {
            "has_previous": False,
            "message": "No previous interview found for comparison.",
            "previous_score": None,
            "current_score": current_report.get("average_score", 0),
            "score_change": None,
            "verdict": "First tracked interview"
        }

    previous_score = float(previous_session.get("average_score", 0) or 0)
    current_score = float(current_report.get("average_score", 0) or 0)
    delta = round(current_score - previous_score, 2)

    if delta >= 5:
        verdict = "Improved significantly"
    elif delta >= 1:
        verdict = "Improved slightly"
    elif delta <= -5:
        verdict = "Declined significantly"
    elif delta <= -1:
        verdict = "Declined slightly"
    else:
        verdict = "No major change"

    return {
        "has_previous": True,
        "previous_score": previous_score,
        "current_score": current_score,
        "score_change": delta,
        "verdict": verdict,
        "message": (
            f"Previous Score: {previous_score}\n"
            f"Current Score: {current_score}\n"
            f"Change: {delta}\n"
            f"Verdict: {verdict}"
        )
    }


def format_comparison_text(comparison: dict) -> str:
    if not comparison.get("has_previous"):
        return comparison.get("message", "No previous session found.")

    sign = "+" if comparison.get("score_change", 0) > 0 else ""
    return (
        f"Previous Score: {comparison['previous_score']}\n"
        f"Current Score: {comparison['current_score']}\n"
        f"Change: {sign}{comparison['score_change']}\n"
        f"Verdict: {comparison['verdict']}"
    )
