import io
import os
import tempfile
import zipfile
import streamlit as st
from pydub import AudioSegment
from pydub.silence import split_on_silence

# --- Page Configuration ---
st.set_page_config(
    page_title="Audio Silence Splitter",
    page_icon="✂️",
    layout="wide"
)

# Custom CSS for an enhanced Drag-and-Drop zone
st.markdown("""
<style>
    [data-testid="stFileUploader"] {
        border: 2px dashed #4E8DF5;
        border-radius: 12px;
        padding: 1.5rem;
        background-color: rgba(78, 141, 245, 0.04);
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #1E60D5;
        background-color: rgba(78, 141, 245, 0.08);
    }
</style>
""", unsafe_allow_html=True)

st.title("✂️ Audio Silence Splitter")
st.write("Drag and drop your audio file(s) below, adjust parameters, and export your segmented MP3 chunks.")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Split Settings")

page_number = st.sidebar.number_input("Starting Page / Prefix Number", min_value=1, value=14, step=1)
min_silence_len = st.sidebar.slider(
    "Minimum Silence Length (ms)",
    min_value=200,
    max_value=4000,
    value=1500,
    step=50,
    help="Duration of silence (in ms) required to create a split."
)
silence_thresh_offset = st.sidebar.slider(
    "Silence Threshold Offset (dB below avg)",
    min_value=5,
    max_value=40,
    value=16,
    step=1,
    help="How many dB below the track's average volume qualifies as silence."
)
keep_silence = st.sidebar.slider(
    "Keep Padding Silence (ms)",
    min_value=0,
    max_value=1000,
    value=250,
    step=50,
    help="Padding kept at the start and end of each slice to prevent clipped speech."
)

# --- Drag & Drop File Uploader ---
uploaded_files = st.file_uploader(
    "📂 Drag and drop audio files here (or click to browse)", 
    type=["m4a", "mp3", "wav", "ogg", "flac"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"Loaded **{len(uploaded_files)}** file(s) for processing.")
    
    if st.button("🚀 Process & Split Audio", type="primary", use_container_width=True):
        zip_buffer = io.BytesIO()
        total_extracted_chunks = 0
        
        with st.spinner("Processing audio files and analyzing silence..."):
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                
                for file_idx, uploaded_file in enumerate(uploaded_files):
                    current_page = page_number + file_idx
                    file_suffix = "." + uploaded_file.name.split(".")[-1].lower()
                    
                    # Write to a clean temporary file on disk
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
                        tmp_file.write(uploaded_file.getbuffer())
                        tmp_path = tmp_file.name

                    try:
                        # Load and process audio
                        sound = AudioSegment.from_file(tmp_path)
                        silence_thresh = sound.dBFS - silence_thresh_offset
                        
                        chunks = split_on_silence(
                            sound,
                            min_silence_len=min_silence_len,
                            silence_thresh=silence_thresh,
                            keep_silence=keep_silence
                        )
                        
                        if len(chunks) == 0:
                            st.warning(f"⚠️ No silence cuts detected for **{uploaded_file.name}**.")
                            continue

                        total_extracted_chunks += len(chunks)
                        
                        # Store chunks in the ZIP archive
                        for chunk_idx, chunk in enumerate(chunks, start=1):
                            chunk_name = f"{current_page}_{chunk_idx}.mp3"
                            chunk_buffer = io.BytesIO()
                            chunk.export(chunk_buffer, format="mp3")
                            zip_file.writestr(f"page_{current_page}_words/{chunk_name}", chunk_buffer.getvalue())

                    except Exception as err:
                        st.error(f"Error processing {uploaded_file.name}: {err}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

        if total_extracted_chunks > 0:
            zip_buffer.seek(0)
            st.success(f"🎉 Successfully split into **{total_extracted_chunks}** total audio segments!")
            
            st.download_button(
                label=f"📥 Download All Split Audio as ZIP",
                data=zip_buffer,
                file_name="split_audio_words.zip",
                mime="application/zip",
                use_container_width=True
            )