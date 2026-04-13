def format_analytics_text(analytics: dict) -> str:
    summary = analytics.get("summary", {})
    dimensions = analytics.get("dimensions", {})

    if not summary or not summary.get("total_interviews"):
        return "No analytics available yet."

    return (
        f"Total Interviews: {summary.get('total_interviews', 0)}\n"
        f"Average Score: {summary.get('avg_score', 0)}\n"
        f"Best Score: {summary.get('best_score', 0)}\n"
        f"Lowest Score: {summary.get('lowest_score', 0)}\n\n"
        f"Average Dimension Scores:\n"
        f"- Relevance: {dimensions.get('avg_relevance', 0)}\n"
        f"- Clarity: {dimensions.get('avg_clarity', 0)}\n"
        f"- Depth: {dimensions.get('avg_depth', 0)}\n"
        f"- Communication: {dimensions.get('avg_communication', 0)}\n"
        f"- Role Alignment: {dimensions.get('avg_role_alignment', 0)}"
    )
