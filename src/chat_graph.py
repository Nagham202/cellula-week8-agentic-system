from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src import cache
from src.answer.answer_agent import generate_answer
from src.orchestrator import run_analysis


class ChatState(TypedDict):
    question: str
    chat_history: list
    search_query: str
    evidence: list
    analysis: str
    answer: str
    sources: list


def analyze_node(state):
    # Sara's orchestrator: the retriever finds the evidence, then the analyst studies it
    result = run_analysis(state["question"], state["chat_history"])
    return {
        "search_query": result["retrieval_details"].get("search_query", state["question"]),
        "evidence": result["all_evidence"],
        "analysis": result["analysis"],
    }


def answer_node(state):
    # the search query is the question written in full, so a follow-up like
    # "How do I fix it?" reaches the answer agent as "How do I fix error E31?"
    reply = generate_answer(state["search_query"], state["analysis"], state["evidence"])
    return {"answer": reply["answer"], "sources": reply["sources"]}


def build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("analyze", analyze_node)
    graph.add_node("answer", answer_node)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


chat_graph = build_graph()


def tell(on_step, step, details):
    # on_step is optional: the streamlit app gives a function that shows each step to the user
    if on_step is not None:
        on_step(step, details)


def ask(question, chat_history=None, on_step=None):
    # the one function the streamlit app and the api call
    cache_key = cache.answer_cache_key(question, chat_history)
    cached = cache.get_answer(cache_key)
    if cached is not None:
        tell(on_step, "cache", {"found": True})
        return {**cached, "from_cache": True}
    tell(on_step, "cache", {"found": False})

    inputs = {"question": question, "chat_history": chat_history or []}
    if on_step is None:
        state = chat_graph.invoke(inputs)
    else:
        # stream() runs the same graph, but gives what each node returned as soon as it finishes
        state = {}
        for update in chat_graph.stream(inputs, stream_mode="updates"):
            for node, output in update.items():
                state.update(output)
                tell(on_step, node, output)
    reply = {"answer": state["answer"], "sources": state["sources"], "analysis": state["analysis"]}
    # errors and "not found" have no sources, don't cache those
    if reply["sources"]:
        cache.save_answer(cache_key, reply)
    return {**reply, "from_cache": False}


# quick test: python -m src.chat_graph  (needs the database, makes a few LLM calls)
if __name__ == "__main__":
    history = []
    for question in ["What does error E31 mean?", "How do I fix it?"]:
        reply = ask(question, history)
        print(f"=== {question}\n{reply['answer']}\n")
        # the history is kept oldest first, the same way the app will keep it
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": reply["answer"]})
