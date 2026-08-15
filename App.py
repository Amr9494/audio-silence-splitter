import io
import zipfile
import streamlit as st
from pydub import AudioSegment
from pydub.silence import split_on_silence

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Audio Silence Splitter", page_icon="✂️", layout="centered")

st.title("✂️ Audio Silence Splitter & Cutter")
st.markdown("Upload your audio file, adjust the silence detection parameters, and export indexed MP3 chunks.")

# --- Sidebar / Settings ---
with st.sidebar:
    st.header("⚙️ Slicing Parameters")
    
    page_num = st.number_input("Page / Section Number", min_value=1, value=14, step=1)
    
    min_silence_len = st.slider(
        "Min Silence Length (ms)",
        min_value=200,
        max_value=4000,
        value=1500,
        step=100,
        help="Silence must be at least this long (in milliseconds) to trigger a cut."
    )
    
    thresh_offset = st.slider(
        "Silence Threshold Offset (dB relative to avg)",
        min_value=5,
        max_value=40,
        value=16,
        step=1,
        help="Higher values make it stricter (cuts quieter pauses). Calculated as `dBFS - offset`."
    )
    
    keep_silence = st.slider(
        "Keep Silence Buffer (ms)",
        min_value=0,
        max_value=1000,
        value=250,
        step=50,
        help="Amount of silence padding kept at the start and end of each chunk."
    )

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload Audio File", type=["m4a", "mp3", "wav", "ogg", "flac"])

if uploaded_file is not None:
    st.audio(uploaded_file, format=uploaded_file.type)
    
    if st.button("🚀 Process & Split Audio", type="primary", use_container_width=True):
        with st.spinner("Analyzing silence and slicing audio..."):
            try:
                # Load audio from memory buffer
                file_extension = uploaded_file.name.split(".")[-1].lower()
                sound = AudioSegment.from_file(uploaded_file, format=file_extension)
                
                # Dynamic silence threshold calculation
                silence_thresh = sound.dBFS - thresh_offset
                
                # Split audio
                chunks = split_on_silence(
                    sound,
                    min_silence_len=min_silence_len,
                    silence_thresh=silence_thresh,
                    keep_silence=keep_silence
                )
                
                if not chunks:
                    st.warning("⚠️ No silence detected with the current parameters. Try decreasing the minimum silence duration or adjusting the threshold offset.")
                else:
                    st.success(f"✅ Found **{len(chunks)}** chunks!")
                    
                    # Prepare in-memory ZIP archive
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        
                        tabs = st.tabs([f"Chunk {i+1}" for i in range(min(len(chunks), 10))] + (["Remaining Chunks"] if len(chunks) > 10 else []))
                        
                        for i, chunk in enumerate(chunks):
                            filename = f"{page_num}_{i + 1}.mp3"
                            
                            # Export chunk to byte buffer
                            chunk_buffer = io.BytesIO()
                            chunk.export(chunk_buffer, format="mp3")
                            chunk_bytes = chunk_buffer.getvalue()
                            
                            # Add to ZIP archive
                            zip_file.writestr(f"page_{page_num}_words/{filename}", chunk_bytes)
                            
                            # Audio player previews for the first 10 chunks
                            if i < 10:
                                with tabs[i]:
                                    st.write(f"**Filename:** `{filename}`")
                                    st.audio(chunk_bytes, format="audio/mp3")
                        
                        if len(chunks) > 10:
                            with tabs[-1]:
                                st.info(f"Showing preview for first 10 chunks only. All {len(chunks)} chunks are included in the download ZIP.")
                    
                    zip_buffer.seek(0)
                    
                    # Download Button
                    st.divider()
                    st.download_button(
                        label=f"📦 Download All Chunks as ZIP (page_{page_num}_words.zip)",
                        data=zip_buffer,
                        file_name=f"page_{page_num}_words.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
            except Exception as e:
                st.error(f"Error processing audio: {e}")
