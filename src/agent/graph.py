import asyncio
import json
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.models import AgentState
from agent.nodes import fetch_pr, analyze, reflect, format_comment, post_comment


class CodeInspectorAgent:


    """
    Private method to create the agent's state graph and compile it with a checkpointer.
     - The graph defines the flow of operations for the agent, starting from fetching the PR to posting the comment.
     - Conditional edges are used to determine the next steps based on the analysis results and reflection outcomes.
     - The compiled graph is returned, ready to be invoked with specific inputs and configurations.
    """
    def _create_agent(self, checkpointer: BaseCheckpointSaver):
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

        return graph.compile(checkpointer)


    """
    Public method to run the agent with a given PR URL and configuration.
     - An asynchronous context is created for the checkpointer to manage state persistence.
    """
    async def run(self, pr_url: str, config: dict):
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
            compiled = self._create_agent(checkpointer)
            result = await compiled.ainvoke({"pr_url": pr_url}, config)




    


if __name__ == "__main__":
    agent = CodeInspectorAgent()

    asyncio.run(agent.run("https://github.com/23daVinci/code_inspector/pull/3",
                          {"configurable": {"thread_id": "1"}}))
                          

