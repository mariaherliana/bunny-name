import re
import io
import zipfile
from collections import defaultdict

import streamlit as st
import pdfplumber

st.set_page_config(page_title="PDF Referensi Renamer", layout="wide")

st.title("PDF Referensi Renamer — batch mode")
st.markdown(
    "Upload one or more PDF files. The app will extract the `Referensi` string (e.g. `Jidoka-2025-11C`) "
    "from the PDF text and provide renamed downloads. If no referensi is found the original filename is kept "
    "with a `NO-REFERENSI` prefix."
)

uploaded_files = st.file_uploader("Upload PDFs (multiple allowed)", type=["pdf"], accept_multiple_files=True)

if not uploaded_files:
    st.info("Upload PDF files to begin.")
    st.stop()

# pattern: find 'Referensi' followed by ':' and capture the following token up to whitespace or a closing parenthesis.
REFERENSI_RE = re.compile(r"Referensi\s*:\s*([^\s\)\]]+)", flags=re.IGNORECASE)

results = []
name_counts = defaultdict(int)

def extract_referensi_from_bytes(pdf_bytes: bytes) -> str | None:
    """Return the first matched referensi string or None."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # read text from each page until we find a match
            for page in pdf.pages:
                text = page.extract_text() or ""
                match = REFERENSI_RE.search(text)
                if match:
                    return match.group(1).strip()
    except Exception as e:
        # return None on extraction errors
        return None
    return None

for uploaded in uploaded_files:
    raw = uploaded.read()
    referensi = extract_referensi_from_bytes(raw)
    if referensi:
        base_name = referensi
        status = "OK"
    else:
        # fallback: try to find something like '(Referensi: ...)' by searching entire filename or mark missing
        base_name = f"NO-REFERENSI-{uploaded.name.rsplit('.',1)[0]}"
        status = "No referensi found"

    # sanitize filename: keep only safe chars (alphanum, -, _, .)
    safe_base = re.sub(r"[^A-Za-z0-9\-\_\.]", "_", base_name)

    # ensure unique names in this batch
    name_counts[safe_base] += 1
    if name_counts[safe_base] == 1:
        new_filename = f"{safe_base}.pdf"
    else:
        new_filename = f"{safe_base}_{name_counts[safe_base] - 1}.pdf"

    results.append({
        "original_name": uploaded.name,
        "new_name": new_filename,
        "status": status,
        "bytes": raw,
    })

# show results table
st.subheader("Preview")
cols = st.columns([3, 3, 2, 2])
cols[0].markdown("**Original filename**")
cols[1].markdown("**New filename (preview)**")
cols[2].markdown("**Status**")
cols[3].markdown("**Download**")

for r in results:
    cols = st.columns([3, 3, 2, 2])
    cols[0].write(r["original_name"])
    cols[1].write(r["new_name"])
    cols[2].write(r["status"])
    # per-file download button
    cols[3].download_button(
        label="Download",
        data=io.BytesIO(r["bytes"]),
        file_name=r["new_name"],
        mime="application/pdf",
        key=f"dl_{r['new_name']}"
    )

# Create a zip with all renamed PDFs
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    for r in results:
        zf.writestr(r["new_name"], r["bytes"])
zip_buffer.seek(0)

st.markdown("---")
st.download_button(
    label="Download all renamed PDFs as ZIP",
    data=zip_buffer,
    file_name="renamed_pdfs.zip",
    mime="application/zip"
)

st.success(f"Processed {len(results)} file(s).")
