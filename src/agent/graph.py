import asyncio
import json
from langsmith import traceable
from langgraph.graph import StateGraph, START, END

from models import AgentState
from nodes import fetch_pr, analyze, reflect, format_comment, post_comment


def create_agent():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_pr", fetch_pr)
    graph.add_node("analyze", analyze)
    graph.add_node("reflect", reflect)
    graph.add_node("format_comment", format_comment)
    graph.add_node("post_comment", post_comment)

    graph.add_edge(START, "fetch_pr")
    graph.add_edge("fetch_pr", "analyze")
    graph.add_conditional_edges("analyze", lambda state: "reflect" if state["findings"] else "format_comment")
    graph.add_conditional_edges("reflect", 
                                lambda s: (
                                                "analyze"
                                                if s["reflection"]["should_loop"] and s["loop_count"] < 2
                                                else "format_comment"
                                            ),)
    graph.add_edge("format_comment", "post_comment")
    graph.add_edge("post_comment", END)

    return graph.compile()


async def run_agent(pr_url: str):
    compiled = create_agent()
    result = await compiled.ainvoke({"pr_url": pr_url})
    print(json.dumps(result, indent=4))
    


if __name__ == "__main__":
    asyncio.run(run_agent("https://github.com/23daVinci/code_inspector/pull/3"))

