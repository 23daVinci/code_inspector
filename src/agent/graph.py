import asyncio
from langgraph.graph import StateGraph, START, END

from models import AgentState
from nodes import fetch_pr


def create_agent():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_pr", fetch_pr)

    graph.add_edge(START, "fetch_pr")
    graph.add_edge("fetch_pr", END)

    return graph.compile()


async def run_agent(pr_url: str):
    compiled = create_agent()
    result = await compiled.ainvoke({"pr_url": pr_url})
    print(result)


if __name__ == "__main__":
    asyncio.run(run_agent("https://github.com/23daVinci/ANLI-Classifier/pull/13"))

