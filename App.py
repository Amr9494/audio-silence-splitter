import io
import os
import tempfile
import zipfile
import streamlit as st
from pydub import AudioSegment
from pydub.silence import split_on_silence

# --- Page Configuration ---
st.set_page_config(page_title="Audio Silence Splitter", page_icon="✂️", layout="wide")

st.title("✂️ Audio Silence Splitter")
st.write("Upload an audio file, configure the splitting parameters, and export your named chunks.")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Split Settings")

page_number = st.sidebar.number_input("Page / Prefix Number", min_value=1, value=14, step=1)
min_silence_len = st.sidebar.slider(
    "Minimum Silence Length (ms)",
    min_value=200,
    max_value=4000,
    value=1500,
    step=50,
    help="Duration of silence (in ms) needed to trigger a split."
)
silence_thresh_offset = st.sidebar.slider(
    "Silence Threshold Offset (dB below avg)",
    min_value=5,
    max_value=40,
    value=16,
    step=1,
    help="How many dB below the average volume is considered silence."
)
keep_silence = st.sidebar.slider(
    "Keep Padding Silence (ms)",
    min_value=0,
    max_value=1000,
    value=250,
    step=50,
    help="Silence left at the beginning and end of each slice."
)

# --- File Uploader ---
uploaded_file = st.file_uploader(
    "Upload an audio file (.m4a, .mp3, .wav, .ogg)", 
    type=["m4a", "mp3", "wav", "ogg"]
)

if uploaded_file is not None:
    # Tablet Fix: Save uploaded bytes to a robust temporary file on disk
    file_suffix = "." + uploaded_file.name.split(".")[-1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name

    st.audio(uploaded_file)
    
    if st.button("🚀 Process & Split Audio", type="primary", use_container_width=True):
        with st.spinner("Processing audio and detecting silence..."):
            try:
                # Load directly from temporary file path for flawless mobile decoding
                sound = AudioSegment.from_file(tmp_path)
                
                silence_thresh = sound.dBFS - silence_thresh_offset
                
                chunks = split_on_silence(
                    sound,
                    min_silence_len=min_silence_len,
                    silence_thresh=silence_thresh,
                    keep_silence=keep_silence
                )
                
                num_chunks = len(chunks)
                
                if num_chunks == 0:
                    st.warning("⚠️ No audio segments detected. Try lowering the Silence Threshold Offset or Minimum Silence Length.")
                else:
                    st.success(f"🎉 Successfully extracted **{num_chunks}** audio segments!")
                    
                    # Create ZIP in memory
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for idx, chunk in enumerate(chunks, start=1):
                            chunk_name = f"{page_number}_{idx}.mp3"
                            chunk_buffer = io.BytesIO()
                            chunk.export(chunk_buffer, format="mp3")
                            zip_file.writestr(f"page_{page_number}_words/{chunk_name}", chunk_buffer.getvalue())

                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label=f"📥 Download All ({page_number}_1.mp3 to {page_number}_{num_chunks}.mp3) as ZIP",
                        data=zip_buffer,
                        file_name=f"page_{page_number}_words.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
                    st.markdown("---")
                    st.subheader("🔊 Chunk Previews")
                    
                    cols = st.columns(2)
                    for idx, chunk in enumerate(chunks, start=1):
                        col = cols[(idx - 1) % 2]
                        with col:
                            chunk_name = f"{page_number}_{idx}.mp3"
                            chunk_buffer = io.BytesIO()
                            chunk.export(chunk_buffer, format="mp3")
                            st.caption(f"**{chunk_name}** ({len(chunk) / 1000.0:.2f}s)")
                            st.audio(chunk_buffer.getvalue(), format="audio/mp3")

            except Exception as e:
                st.error(f"Error processing audio: {e}")
            finally:
                # Clean up temporary disk file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)