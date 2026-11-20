import tempfile
import time
from pathlib import Path
import streamlit as st
from src.chat_graph import ask
from src.pipeline.ingest import ingest_file, ingest_text
from src.pipeline.ocr import extract_text
from src.pipeline.loaders import SourceError
from src.pipeline.store import count_chunks, delete_source, list_sources
from streamlit_mic_recorder import mic_recorder
from src.voice import transcribe_audio

st.set_page_config(page_title="Chat with your documents", layout="wide")

def upload_files(files):

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        for file in files:
            path = Path(folder) / file.name
            path.write_bytes(file.getvalue())

            try:
                with st.spinner(f"Reading {file.name}..."):

                    extension = path.suffix.lower()

                    if extension in [".png", ".jpg", ".jpeg"]:

                        text = extract_text(path)

                        chunk_count = ingest_text(
                            text,
                            file.name,
                            source_type="image"
                        )

                    else:
                        chunk_count = ingest_file(path)

                st.success(f"{file.name}: {chunk_count} chunks")

            except (SourceError, ValueError) as error:
                st.error(f"{file.name}: {error}")



def show_sidebar():
    st.sidebar.header("Knowledge")

    files = st.sidebar.file_uploader("Upload PDF, DOCX or TXT or Images", 
                                     type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
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
    # sources go in the expander below, so drop the list the answer agent adds
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

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.button("New conversation"):
        st.session_state.messages = []
        st.rerun()

    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                show_answer(message)

    # Voice input
    st.subheader("Ask using your voice")

    audio = mic_recorder(
        start_prompt="Start recording",
        stop_prompt="Stop recording",
        key="voice_recorder"
    )

    voice_question = None

    if audio:
        st.audio(audio["bytes"], format="audio/wav")

        if st.button("Transcribe and ask", key="transcribe_audio"):
            try:
                with st.spinner("Converting your voice to text..."):
                    voice_question = transcribe_audio(audio["bytes"])

                st.success("Transcription completed!")
                st.write("Recognized question:", voice_question)

            except Exception as error:
                st.error(f"Transcription failed: {error}")

    # Text input
    question = st.chat_input("Ask a question about your documents")

    # Use the voice question if available
    if voice_question:
        question = voice_question

    # Process both typed and spoken questions
    if question:
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            start = time.perf_counter()

            with st.spinner("Searching and analyzing..."):
                reply = ask(question, st.session_state.messages)

            answer = {
                "role": "assistant",
                "content": reply["answer"],
                "sources": reply["sources"],
                "from_cache": reply["from_cache"],
                "seconds": round(time.perf_counter() - start, 2)
            }

            show_answer(answer)

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        st.session_state.messages.append(answer)


main()

