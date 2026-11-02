import csv
import io
import re

import pandas as pd
import streamlit as st


st.set_page_config(page_title="LeadQA File Converter", layout="wide")

# Exact headers and order from the confirmed LeadQA Conversion Template.
OUTPUT_HEADERS = [
    "Company Name", "First Name", "Last Name", "Job Title", "Email",
    "Switch", "Direct", "Mobile", "Person Linkedin Url", "Location",
    "Time Zone", "TM Status", "TM Notes", "TM Timestamp", "Question1",
    "Question2", "Question3", "Question4", "Question5", "TM LI Check",
    "TM Name", "Asset_Title1", "Emailed Date", "Reoon Check",
    "Reoon Status", "Engagement Score", "Catchall", "Valid", "Validated",
    "Email Time Stamp", "Timestamp2", "Asset_Title2", "Address1",
    "Address2", "City", "State", "Zipcode", "Country", "Industry",
    "Employees", "Revenue", "Website", "Domain", "Job Level",
    "Job Department", "LI Check", "LI Status", "LI Company Name",
    "LI Company Url", "Linkedin Notes", "Connections",
    "Time in Current Role", "Last Activity", "TAL Company Name",
    "Mapped Job Title", "Campaign ID", "CDL", "Status", "Name",
    "Data Pull", "phone", "contact_country", "id", "company_id",
    "company_confidence", "sub_industry", "address", "address_hq",
    "company_phone", "email_confidence", "email_provider",
    "email_alternates", "contact_city", "contact_state",
    "technologies", "email_status",
]

# Destination header: source header.
# Values are copied unchanged. No category or numeric conversions.
APOLLO_MAPPING = {
    "Company Name": "Company Name",
    "First Name": "First Name",
    "Last Name": "Last Name",
    "Job Title": "Title",
    "Email": "Email",
    "Switch": "Corporate Phone",
    "Direct": "Work Direct Phone",
    "Mobile": "Mobile Phone",
    "Person Linkedin Url": "Person Linkedin Url",
    "Address1": "Company Address",
    "City": "Company City",
    "State": "Company State",
    "Country": "Company Country",
    "Industry": "Industry",
    "Employees": "# Employees",
    "Revenue": "Annual Revenue",
    "Website": "Website",
    "Job Level": "Seniority",
    "Job Department": "Departments",
    "LI Company Url": "Company Linkedin Url",
    "contact_country": "Country",
    "company_phone": "Company Phone",
    "email_confidence": "Email Confidence",
    "contact_city": "City",
    "contact_state": "State",
    "technologies": "Technologies",
    "email_status": "Email Status",
}

ZOOMINFO_MAPPING = {
    "Company Name": "Company Name",
    "First Name": "First Name",
    "Last Name": "Last Name",
    "Job Title": "Job Title",
    "Email": "Email Address",
    "Switch": "Company HQ Phone",
    "Direct": "Direct Phone Number",
    "Mobile": "Mobile phone",
    "Person Linkedin Url": "LinkedIn Contact Profile URL",
    "Address1": "Company Street Address",
    "City": "Company City",
    "State": "Company State",
    "Zipcode": "Company Zip Code",
    "Country": "Company Country",
    "Industry": "Primary Industry",
    "Employees": "Employees",
    "Revenue": "Revenue (in 000s USD)",
    "Website": "Website",
    "Job Level": "Management Level",
    "Job Department": "Department",
    "LI Company Url": "LinkedIn Company Profile URL",
    "contact_country": "Country",
    "sub_industry": "Primary Sub-Industry",
    "company_phone": "Company HQ Phone",
    "contact_city": "Person City",
    "contact_state": "Person State",
}

# These are deliberate initial mapping choices.
# Users can review and change every mapping before downloading.
# Provider IDs are not mapped into internal Datahub IDs.
# Provider verification fields are not mapped into Reoon/Valid fields.


def normalise_header(value):
    return str(value).replace("\ufeff", "").strip()


def clean_headers(headers):
    cleaned = [normalise_header(value) for value in headers]
    duplicates = sorted({
        value for value in cleaned if cleaned.count(value) > 1
    })
    if duplicates:
        raise ValueError(
            "Duplicate input headers found: " + ", ".join(duplicates)
        )
    if any(not value for value in cleaned):
        raise ValueError("An input column has no header. Please name or remove it.")
    return cleaned


def read_csv_file(raw):
    text = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError("Could not read this CSV's text encoding.")

    try:
        dialect = csv.Sniffer().sniff(
            text[:65536], delimiters=",;\t|"
        )
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text, newline=""), dialect)
    try:
        headers = clean_headers(next(reader))
    except StopIteration:
        raise ValueError("The CSV is empty.")

    rows = []
    for line_number, row in enumerate(reader, start=2):
        if not row or all(value == "" for value in row):
            continue
        if len(row) != len(headers):
            raise ValueError(
                f"CSV record {line_number} has {len(row)} fields; "
                f"the header has {len(headers)}. Check its delimiter or quotes."
            )
        rows.append(row)

    return pd.DataFrame(rows, columns=headers, dtype=str)


def read_excel_file(raw, sheet_name):
    # Read header separately so duplicate headers aren't silently renamed.
    frame = pd.read_excel(
        io.BytesIO(raw),
        sheet_name=sheet_name,
        header=None,
        dtype=str,
        keep_default_na=False,
        engine="openpyxl",
    )
    if frame.empty:
        raise ValueError("The selected sheet is empty.")

    headers = clean_headers(frame.iloc[0].tolist())
    data = frame.iloc[1:].copy()
    data.columns = headers
    data = data.loc[
        ~data.apply(lambda row: all(value == "" for value in row), axis=1)
    ]
    return data.reset_index(drop=True)


def detect_source(headers):
    headers = set(headers)
    apollo = len(headers & {
        "Apollo Contact Id", "Apollo Account Id",
        "Company Name for Emails", "Work Direct Phone", "# Employees",
    })
    zoom = len(headers & {
        "ZoomInfo Contact ID", "ZoomInfo Company ID",
        "LinkedIn Contact Profile URL", "Revenue (in 000s USD)",
        "Company HQ Phone",
    })
    if apollo > zoom:
        return "Apollo"
    if zoom > apollo:
        return "ZoomInfo"
    return None


def domain_from_email(value):
    email = str(value).strip()
    if email.count("@") != 1 or re.search(r"\s", email):
        return ""
    local, domain = email.rsplit("@", 1)
    if not local:
        return ""
    domain = domain.lower()
    if not re.fullmatch(
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z]{2,63}",
        domain,
    ):
        return ""
    return domain


st.title("LeadQA File Converter")
st.write(
    "Upload Apollo or ZoomInfo data and download it in the "
    "76-column LeadQA format."
)
st.caption(
    "Source values are copied unchanged. Domain is extracted from Email. "
    "Files are processed in memory; this app does not write uploads to disk."
)

uploaded = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx"],
)

if uploaded is None:
    st.stop()

raw = uploaded.getvalue()

try:
    if uploaded.name.lower().endswith(".xlsx"):
        with pd.ExcelFile(io.BytesIO(raw), engine="openpyxl") as book:
            sheet_names = book.sheet_names
        sheet = st.selectbox("Worksheet", sheet_names)
        data = read_excel_file(raw, sheet)
    else:
        data = read_csv_file(raw)
except Exception as exc:
    st.error(f"Unable to read this file: {exc}")
    st.stop()

if data.empty:
    st.warning("This file contains headers but no data rows.")
    st.stop()

detected = detect_source(data.columns)
source_choice = st.selectbox(
    "Input format",
    ["Auto-detect", "Apollo", "ZoomInfo"],
)

if source_choice == "Auto-detect":
    if detected is None:
        st.warning("Could not confidently detect the format. Select it above.")
        st.stop()
    source = detected
else:
    source = source_choice

st.success(
    f"{source} format · {len(data):,} records · "
    f"{len(data.columns)} input columns"
)

base_mapping = (
    APOLLO_MAPPING if source == "Apollo" else ZOOMINFO_MAPPING
)

missing = sorted({
    field for field in base_mapping.values()
    if field not in data.columns
})

if missing:
    st.warning(
        "Some expected source columns are missing. Their output fields "
        "will remain blank unless you choose another source below: "
        + ", ".join(missing)
    )

st.info(
    "Initial mappings use company addresses for Address1/City/State/Country, "
    "and person locations for contact_country/contact_city/contact_state. "
    "Review or change these below. Internal IDs and verification results "
    "remain blank by default."
)

if source == "ZoomInfo":
    st.warning(
        "Revenue is copied unchanged from 'Revenue (in 000s USD)'. "
        "For example, 25000 stays 25000; it is not multiplied by 1,000."
    )

mapping_rows = []
for output_header in OUTPUT_HEADERS:
    if output_header == "Domain":
        continue
    proposed = base_mapping.get(output_header, "")
    mapping_rows.append({
        "Output column": output_header,
        "Input column": proposed if proposed in data.columns else "",
    })

with st.expander("Review or change column mappings", expanded=False):
    st.caption(
        "Select an input column for each output field, or leave it blank. "
        "Domain is always generated from the mapped Email field."
    )
    edited_mapping = st.data_editor(
        pd.DataFrame(mapping_rows),
        hide_index=True,
        disabled=["Output column"],
        column_config={
            "Input column": st.column_config.SelectboxColumn(
                "Input column",
                options=[""] + list(data.columns),
                required=False,
            )
        },
        key=f"mapping_{uploaded.name}_{source}_{tuple(data.columns)}",
    )

output = pd.DataFrame("", index=data.index, columns=OUTPUT_HEADERS)

for _, row in edited_mapping.iterrows():
    source_header = row["Input column"]
    if isinstance(source_header, str) and source_header in data.columns:
        output[row["Output column"]] = data[source_header]

output["Domain"] = output["Email"].map(domain_from_email)

left, middle, right = st.columns(3)
left.metric("Output records", f"{len(output):,}")
middle.metric("Output columns", len(output.columns))
right.metric("Email domains extracted", f"{output['Domain'].ne('').sum():,}")

st.subheader("Output preview")
st.dataframe(output.head(20), hide_index=True)

with st.expander("Output fields left completely blank"):
    blank_fields = [
        column for column in OUTPUT_HEADERS
        if output[column].eq("").all()
    ]
    st.write(", ".join(blank_fields) if blank_fields else "None")

csv_output = output.to_csv(
    index=False,
    lineterminator="\r\n",
).encode("utf-8-sig")

st.download_button(
    "Download LeadQA CSV",
    data=csv_output,
    file_name=f"{source.lower()}_leadqa_converted.csv",
    mime="text/csv",
    type="primary",
)

st.caption(
    "CSV preserves the supplied text, including leading zeros. "
    "Opening a CSV directly in Excel may cause Excel to reinterpret "
    "phone numbers, postcodes or date-like values."
)
