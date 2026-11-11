"""
بناء الـgraph بتاع الـagent (LangGraph) — الفلو الموثّق في PRD قسم 6.

    load_history → decide_category → check_permission ─┬─ denied ───→ END
                                                     └─ allowed → retrieve ─┬─ not_found → END
                                                                           └─ respond → END

المسارين الشرطيين هما مخرجو الـendpoint: الرفض (PRD نقطة 5) والرد الجاهز
"مش لاقي" (نقطة 6). حافة retrieve→respond دي هي المكان اللي هيتحط فيه
node الـself-check لاحقاً (بين الاتنين) من غير إعادة هيكلة — الحافة الشرطية
بترجع label ومش بتشبك الـnodes يدوي.
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    check_permission,
    decide_category,
    load_history,
    respond,
    retrieve,
    route_after_permission,
    route_after_retrieve,
)
from app.agent.state import AgentState


def build_graph():
    """يبني الـgraph المشروط ويُجمّعه — compile() بيتنادى مرة واحدة هنا مش في كل request."""
    graph: StateGraph = StateGraph(AgentState)
    graph.add_node("load_history", load_history)
    graph.add_node("decide_category", decide_category)
    graph.add_node("check_permission", check_permission)
    graph.add_node("retrieve", retrieve)
    graph.add_node("respond", respond)
    graph.add_edge(START, "load_history")
    graph.add_edge("load_history", "decide_category")
    graph.add_edge("decide_category", "check_permission")
    graph.add_conditional_edges("check_permission", route_after_permission, {"denied": END, "retrieve": "retrieve"})
    graph.add_conditional_edges("retrieve", route_after_retrieve, {"respond": "respond", "not_found": END})
    graph.add_edge("respond", END)
    return graph.compile()


@lru_cache
def get_compiled_graph():
    """الـgraph المُجمّع — واحد لكل عملية (البناء فيه wiring بس، مفيش I/O)."""
    return build_graph()
