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
from src.report.report_agent import generate_report

st.set_page_config(page_title="Chat with your documents", page_icon="📚", layout="wide")

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
        if button_column.button("🗑️", key=f"remove {source}", help=f"Remove {source}"):
            delete_source(source)
            st.rerun()

    with st.sidebar.expander("How it works"):
        st.markdown(
            "1. **Cache:** a question that was answered before is answered again at once, with 0 tokens.\n"
            "2. **Retriever agent:** rewrites the question and finds the best passages (hybrid search + reranking).\n"
            "3. **Analyst agent:** studies the passages, calculates, compares, and asks for more evidence if needed.\n"
            "4. **Answer agent:** writes the answer and cites every source.\n"
            "5. **Report agent:** turns an answer into a PDF report, in the style you ask for."
        )
    return sources


def show_step(status, step, details):
    # ask() calls this after each step, so the user can watch the agents work
    if step == "cache":
        if details["found"]:
            st.write("⚡ **Cache:** this question was answered before, so no agent is needed.")
        else:
            st.write("🗂️ **Cache:** no saved answer, so the agents start.")
            status.update(label="The Retriever and Analyst agents are working...")
    elif step == "analyze":
        documents = {item.get("source") for item in details["evidence"]}
        st.write(f"🔎 **Retriever:** searched for *{details['search_query']}* and found "
                 f"{len(details['evidence'])} passages in {len(documents)} document(s).")
        st.write("🧠 **Analyst:** studied the passages and wrote notes for the answer.")
        status.update(label="The Answer agent is writing...")
    elif step == "answer":
        st.write(f"✍️ **Answer agent:** wrote the answer with {len(details['sources'])} source(s).")


def answer_text(message):
    # sources are shown separately, so drop the list the answer agent adds at the end
    answer = message["content"]
    if message["sources"] and "\n\nSources:" in answer:
        answer = answer.rsplit("\n\nSources:", 1)[0]
    return answer


AGENT_CHOOSES = "Let the agent choose"
FONTS = {"Modern (Helvetica)": "Helvetica", "Classic (Times)": "Times-Roman", "Typewriter (Courier)": "Courier"}
COLORS = {"Navy": "#1F3A5F", "Dark green": "#1E5631", "Burgundy": "#7A1F2B", "Teal": "#0F6B6B", "Black": "#000000"}
TITLE_SIZES = {"Small": 18, "Medium": 24, "Large": 30}
ALIGNMENTS = {"Left": "left", "Justified": "justify"}


def pick_design(number):
    # every control starts at "Let the agent choose", and only the ones the user changes are sent
    left, right = st.columns(2)
    font = left.selectbox("Font", [AGENT_CHOOSES, *FONTS], key=f"font {number}")
    color = right.selectbox("Title and headings color", [AGENT_CHOOSES, *COLORS], key=f"color {number}")
    size = left.selectbox("Title size", [AGENT_CHOOSES, *TITLE_SIZES], key=f"size {number}")
    alignment = right.selectbox("Text alignment", [AGENT_CHOOSES, *ALIGNMENTS], key=f"alignment {number}")
    choices = {}
    if font != AGENT_CHOOSES:
        choices.update(heading_font=FONTS[font], body_font=FONTS[font])
    if color != AGENT_CHOOSES:
        choices.update(title_color=COLORS[color], heading_color=COLORS[color])
    if size != AGENT_CHOOSES:
        choices["title_size"] = TITLE_SIZES[size]
    if alignment != AGENT_CHOOSES:
        choices["alignment"] = ALIGNMENTS[alignment]
    return choices


def show_report_section(message, number):
    # any answer can become a PDF report: the user picks settings, describes the style in words, or both
    with st.expander("📄 PDF report"):
        choices = pick_design(number)
        style = st.text_input("Or describe the style in your own words (optional)", key=f"style {number}",
                              placeholder="for example: formal, wide margins, more space between lines")
        if st.button("Create the report", key=f"create {number}"):
            with st.spinner("The Report agent is designing the PDF..."):
                path = generate_report(message["question"], answer_text(message), message.get("analysis", ""),
                                       message["sources"], style or None, choices)
            message["report"] = Path(path).read_bytes()
        if message.get("report"):
            st.download_button("Download report.pdf", message["report"], file_name="report.pdf",
                               mime="application/pdf", key=f"download {number}")


def show_answer(message, number):
    st.markdown(answer_text(message))

    sources = message["sources"]
    count = f"{len(sources)} source{'' if len(sources) == 1 else 's'}"
    if message.get("from_cache"):
        st.caption(f"From the cache · 0 tokens · {count} · {message['seconds']} s")
    else:
        st.caption(f"{count} · {message['seconds']} s")
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for source in sources:
                st.markdown(f"- {source}")
    if message.get("analysis"):
        with st.expander("Analyst notes"):
            st.markdown(message["analysis"])
    # older messages have no question saved, and an answer without sources is not worth a report
    if message.get("question") and sources:
        show_report_section(message, number)


def main():
    st.title("📚 Chat with your documents")
    st.caption("Answers come only from your documents, every answer cites where it came from, "
               "and any answer can become a PDF report.")

    sources = show_sidebar()
    if not sources:
        st.info("There are no documents yet. Upload a file in the sidebar, then ask a question.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.button("New conversation"):
        st.session_state.messages = []
        st.rerun()

    for number, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                show_answer(message, number)

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

            with st.status("Checking the answer cache...", expanded=True) as status:
                # Pass the history before adding the new question
                reply = ask(
                    question,
                    st.session_state.messages,
                    on_step=lambda step, details: show_step(status, step, details)
                )

                seconds = round(time.perf_counter() - start, 2)

                status.update(
                    label=f"Done in {seconds} s",
                    state="complete",
                    expanded=False
                )

            answer = {
                "role": "assistant",
                "content": reply["answer"],
                "sources": reply["sources"],
                "analysis": reply.get("analysis", ""),
                "question": question,
                "from_cache": reply["from_cache"],
                "seconds": seconds
            }

            # Display the answer with its report options
            show_answer(answer, len(st.session_state.messages) + 1)

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })
        st.session_state.messages.append(answer)
        
main()

