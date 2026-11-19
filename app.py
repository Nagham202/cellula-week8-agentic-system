# run with: python -m streamlit run app.py

import tempfile
import time
from pathlib import Path

import streamlit as st

from src.chat_graph import ask
from src.pipeline.ingest import ingest_file
from src.pipeline.loaders import SourceError
from src.pipeline.store import count_chunks, delete_source, list_sources

st.set_page_config(page_title="Chat with your documents", layout="wide")


def upload_files(files):
    # each file is saved with its real name, because the name becomes the source in the citations
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        for file in files:
            path = Path(folder) / file.name
            path.write_bytes(file.getvalue())
            try:
                with st.spinner(f"Reading {file.name}..."):
                    chunk_count = ingest_file(path)
                st.success(f"{file.name}: {chunk_count} chunks")
            except SourceError as error:
                st.error(f"{file.name}: {error}")


def show_sidebar():
    st.sidebar.header("Knowledge")

    files = st.sidebar.file_uploader("Upload PDF, DOCX or TXT files", type=["pdf", "docx", "txt"],
                                     accept_multiple_files=True)
    if files and st.sidebar.button("Add to the knowledge base"):
        upload_files(files)

    sources = list_sources()
    st.sidebar.subheader(f"Sources ({len(sources)})")
    st.sidebar.caption(f"{count_chunks() if sources else 0} chunks in Qdrant")
    for source in sources:
        name_column, button_column = st.sidebar.columns([4, 1])
        name_column.write(f"{source} ({count_chunks(source)} chunks)")
        if button_column.button("Remove", key=f"remove {source}"):
            delete_source(source)
            st.rerun()
    return sources


def show_answer(message):
    answer, sources = message["content"], message["sources"]
    # the answer agent adds a "Sources:" list at the end, it is shown in its own section instead
    if sources and "\n\nSources:" in answer:
        answer = answer.rsplit("\n\nSources:", 1)[0]
    st.markdown(answer)

    count = f"{len(sources)} source{'' if len(sources) == 1 else 's'}"
    if message.get("from_cache"):
        st.caption(f"From the cache · 0 tokens · {count} · {message['seconds']} s")
    else:
        st.caption(f"{count} · {message['seconds']} s")
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for source in sources:
                st.markdown(f"- {source}")


def main():
    st.title("Chat with your documents")
    st.caption("Answers come only from your documents, and every answer cites where it came from.")

    sources = show_sidebar()
    if not sources:
        st.info("There are no documents yet. Upload a file in the sidebar, then ask a question.")

    # the chat is kept here between reruns, oldest message first
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.button("New conversation"):
        st.session_state.messages = []
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                show_answer(message)

    question = st.chat_input("Ask a question about your documents")
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            start = time.perf_counter()
            with st.spinner("Searching and analyzing..."):
                # the history is passed before the new question is added to it
                reply = ask(question, st.session_state.messages)
            answer = {"role": "assistant", "content": reply["answer"], "sources": reply["sources"],
                      "from_cache": reply["from_cache"], "seconds": round(time.perf_counter() - start, 2)}
            show_answer(answer)
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.messages.append(answer)


main()
