import asyncio
import json
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from typing import Literal

from agent.models import AgentState
from agent.nodes import fetch_pr, analyze, reflect, format_comment, post_comment


class CodeInspectorAgent:


    def _create_agent(self, checkpointer: BaseCheckpointSaver):
        """
        Private method to create the agent's state graph and compile it with the provided checkpointer for state management.
         - The graph defines the flow of operations from fetching the PR to posting the comment, with conditional logic for analysis and reflection.
         - The compiled graph can then be invoked with the initial state and configuration.
        """
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


    async def run(self, pr_url: str, config: dict):
        """
        Public method to run the agent with a given PR URL and configuration.
        - An asynchronous context is created for the checkpointer to manage state persistence.
        """
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
            compiled = self._create_agent(checkpointer)
            return await compiled.ainvoke({"pr_url": pr_url}, config)
        

    _NODE_NAMES = {"fetch_pr", "analyze", "reflect", "format_comment", "post_comment"}

    async def stream_events(self, pr_url: str, config: dict):
        """
        Async generator that yields a slim dict for each node completion.
        Yields: {"node": str, "status": "completed"} for each node,
        then a terminal {"status": "awaiting_approval", "findings": [...], "comment_body": str}.
        """
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
            compiled = self._create_agent(checkpointer)
            async for chunk in compiled.astream({"pr_url": pr_url}, config):
                for node_name in chunk:
                    if node_name in self._NODE_NAMES:
                        yield {"node": node_name, "status": "completed"}
            snapshot = await compiled.aget_state(config)
            values = snapshot.values
            yield {
                "status": "awaiting_approval",
                "findings": values.get("findings", []),
                "comment_body": values.get("comment_body", ""),
            }


    async def resume(self, decision: Literal["approved", "rejected"], config: dict) -> dict | None:
        """
        Resume the agent after an interrupt with the user's decision.
        """
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
            compiled = self._create_agent(checkpointer)
            
            if decision == "approved":
                return await compiled.ainvoke(None, config)
            else:
                return None




    


if __name__ == "__main__":
    agent = CodeInspectorAgent()

    asyncio.run(agent.run("https://github.com/23daVinci/code_inspector/pull/3",
                          {"configurable": {"thread_id": "1"}}))
                          

