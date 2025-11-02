import re
import io
import zipfile
from collections import defaultdict

import streamlit as st
import pdfplumber

st.set_page_config(page_title="PDF Renamer Tools", layout="wide")

tab1, tab2 = st.tabs(["📘 Referensi Renamer", "📗 Unifikasi Renamer"])

# ==============================
# TAB 1 — EXISTING REFERENSI RENAMER
# ==============================
with tab1:
    st.title("PDF Referensi Renamer — batch mode")
    st.markdown(
        "Upload one or more PDF files. The app will extract the `Referensi` string (e.g. `Jidoka-2025-11C`) "
        "from the PDF text and provide renamed downloads. If no referensi is found the original filename is kept "
        "with a `NO-REFERENSI` prefix."
    )

    uploaded_files = st.file_uploader(
        "Upload PDFs (multiple allowed)",
        type=["pdf"],
        accept_multiple_files=True,
        key="referensi_upload"
    )

    if uploaded_files:
        REFERENSI_RE = re.compile(
            r"Referensi\s*:\s*([A-Za-z0-9\-\s\(\)]+?)(?=\s*[\r\n]|$|\))",
            flags=re.IGNORECASE
        )

        results = []
        name_counts = defaultdict(int)

        def extract_referensi_from_bytes(pdf_bytes: bytes) -> str | None:
            """Return the first matched referensi string or None."""
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text() or ""
                        match = REFERENSI_RE.search(text)
                        if match:
                            return match.group(1).strip()
            except Exception:
                return None
            return None

        for uploaded in uploaded_files:
            raw = uploaded.read()
            referensi = extract_referensi_from_bytes(raw)
            if referensi:
                base_name = referensi
                status = "OK"
            else:
                base_name = f"NO-REFERENSI-{uploaded.name.rsplit('.',1)[0]}"
                status = "No referensi found"

            safe_base = re.sub(r"[^A-Za-z0-9\-\_\.\s\(\)]", "_", base_name).strip()

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
            cols[3].download_button(
                label="Download",
                data=io.BytesIO(r["bytes"]),
                file_name=r["new_name"],
                mime="application/pdf",
                key=f"dl_{r['new_name']}"
            )

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
    else:
        st.info("Upload PDF files to begin.")


# ==============================
# TAB 2 — NEW UNIFIKASI RENAMER
# ==============================
with tab2:
    st.title("Unifikasi PDF Renamer")
    st.markdown(
        "Rename files using **Masa Pajak**, **A.2 Nama**, and **Nomor** fields "
        "in the format: `1025 / HIGH QUALITY / 2505ZZCH2.pdf`."
    )

    uploaded_unifikasi = st.file_uploader(
        "Upload Unifikasi PDFs (multiple allowed)",
        type=["pdf"],
        accept_multiple_files=True,
        key="unifikasi_upload"
    )

    if uploaded_unifikasi:
        results_uni = []
        name_counts_uni = defaultdict(int)

        def extract_unifikasi_fields(pdf_bytes: bytes):
            text = ""
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

            masa_match = re.search(r"Masa\s+Pajak\s*([0-9]{1,2}-[0-9]{4})", text, re.IGNORECASE)
            nama_match = re.search(r"A\.2\s+Nama\s*[:\-]?\s*([A-Z0-9\s\.\&\-\(\)]+)", text, re.IGNORECASE)
            nomor_match = re.search(r"\b([A-Z0-9]{8,})\s+\d{2}-\d{4}", text)

            masa = masa_match.group(1).replace("-", "") if masa_match else None
            nama = nama_match.group(1).strip() if nama_match else None
            nomor = nomor_match.group(1) if nomor_match else None

            return masa, nama, nomor

        for uploaded in uploaded_unifikasi:
            raw = uploaded.read()
            masa, nama, nomor = extract_unifikasi_fields(raw)

            if masa and nama and nomor:
                base_name = f"{masa} / {nama} / {nomor}"
                status = "OK"
            else:
                base_name = f"NO-DATA-{uploaded.name.rsplit('.',1)[0]}"
                status = "Incomplete fields"

            safe_base = re.sub(r"[^A-Za-z0-9\-\_\.\s\(\)/]", "_", base_name).strip()

            name_counts_uni[safe_base] += 1
            if name_counts_uni[safe_base] == 1:
                new_filename = f"{safe_base}.pdf"
            else:
                new_filename = f"{safe_base}_{name_counts_uni[safe_base] - 1}.pdf"

            results_uni.append({
                "original_name": uploaded.name,
                "new_name": new_filename,
                "status": status,
                "bytes": raw,
            })

        st.subheader("Preview")
        cols = st.columns([3, 3, 2, 2])
        cols[0].markdown("**Original filename**")
        cols[1].markdown("**New filename**")
        cols[2].markdown("**Status**")
        cols[3].markdown("**Download**")

        for r in results_uni:
            c = st.columns([3, 3, 2, 2])
            c[0].write(r["original_name"])
            c[1].write(r["new_name"])
            c[2].write(r["status"])
            c[3].download_button(
                label="Download",
                data=io.BytesIO(r["bytes"]),
                file_name=r["new_name"],
                mime="application/pdf",
                key=f"uni_dl_{r['new_name']}"
            )

        zip_buffer_uni = io.BytesIO()
        with zipfile.ZipFile(zip_buffer_uni, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in results_uni:
                zf.writestr(r["new_name"], r["bytes"])
        zip_buffer_uni.seek(0)

        st.download_button(
            label="Download all renamed PDFs as ZIP",
            data=zip_buffer_uni,
            file_name="renamed_unifikasi.zip",
            mime="application/zip"
        )

        st.success(f"Processed {len(results_uni)} Unifikasi file(s).")
    else:
        st.info("Upload Unifikasi PDFs to begin.")
