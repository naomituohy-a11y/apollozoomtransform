# LeadQA File Converter

Converts Apollo and ZoomInfo exports into the confirmed
76-column LeadQA Conversion Template.

## Use

1. Upload an Apollo or ZoomInfo CSV or XLSX file.
2. Select the worksheet if uploading Excel.
3. Check the detected input format.
4. Review or adjust column mappings if needed.
5. Download the converted CSV.

The output template is built in. No template upload is required.

## Conversion behaviour

- Keeps the exact 76 output headers in the required order.
- Preserves input record order.
- Copies source values unchanged.
- Leaves unmapped output fields blank.
- Derives Domain from the mapped Email value.
- Keeps personal email domains when present.
- Does not perform industry, revenue, employee-band or other value mapping.
- Does not deduplicate records.
- Does not include any example records from the output template.
- Ignores completely empty input rows.

## Initial mapping choices

- Company addresses populate Address1, City, State, Zipcode and Country
  where the source provides them.
- Person location fields populate contact_country, contact_city and
  contact_state.
- Apollo Corporate Phone populates Switch.
- Apollo Company Phone populates company_phone.
- ZoomInfo Company HQ Phone populates both Switch and company_phone.
- Apollo Industry and ZoomInfo Primary Industry populate Industry.
- ZoomInfo Primary Sub-Industry populates sub_industry.
- Apollo Seniority and ZoomInfo Management Level populate Job Level.
- Source provider IDs are not placed into internal Datahub ID fields.
- Provider email verification results are not treated as Reoon results.
- Fields without a clear equivalent remain blank.

All mappings except the derived Domain field can be reviewed and changed
in the app before downloading.

## Revenue units

ZoomInfo's Revenue (in 000s USD) is copied unchanged.
A source value of 25000 remains 25000.

No multiplication, currency conversion or band conversion is performed.

## File handling

CSV input is read as text to preserve leading zeros.
UTF-8, Windows-1252 and Latin-1 encodings are supported.
Comma, semicolon, tab and pipe delimiters are detected.

XLSX files are supported; legacy XLS files are not.
Leading zeros already lost in an Excel source cannot be reconstructed.

Uploads are processed in memory. The app does not explicitly save uploaded
files to disk or send them to another API.

## Run locally

pip install -r requirements.txt
streamlit run app.py

## Deployment

Set app.py as the main application file when deploying with Streamlit.
Configure access appropriately before sharing the app with the team.
