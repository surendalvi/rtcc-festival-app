import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import os
import json
import re
import urllib.parse
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Try to import PyGithub for automatic sync & backup
try:
    from github import Github
    HAS_GITHUB = True
except ImportError:
    HAS_GITHUB = False

st.set_page_config(
    page_title="Radhanagar Towers Cultural Committee", 
    page_icon="🪔", 
    layout="wide"
)

# --- GLOBAL STYLING ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    input, textarea, div[data-baseweb="input"] input, div[data-baseweb="base-input"] {
        color: #0F172A !important;
        -webkit-text-fill-color: #0F172A !important;
        background-color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border-color: #CBD5E1 !important;
    }
    .main-header {
        background: linear-gradient(135deg, #6b0912 0%, #9c1c28 50%, #B8860B 100%);
        padding: 26px 20px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 18px;
        box-shadow: 0px 6px 20px rgba(122, 12, 22, 0.25);
        border: 1px solid rgba(255, 215, 0, 0.3);
    }
    .main-header h1 {
        color: #FFFDF0 !important;
        font-size: 23px !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
        line-height: 1.3;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .main-header p {
        color: #FEEBC8 !important;
        margin: 6px 0 0 0 !important;
        font-size: 13.5px !important;
        font-weight: 500;
    }
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 16px;
    }
    @media (max-width: 768px) {
        .kpi-container {
            grid-template-columns: 1fr;
            gap: 10px;
        }
        .main-header h1 {
            font-size: 19px !important;
        }
    }
    .kpi-card {
        padding: 14px 16px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-card-inc {
        background: linear-gradient(135deg, #15803D 0%, #16A34A 100%);
        color: white;
    }
    .kpi-card-exp {
        background: linear-gradient(135deg, #B91C1C 0%, #DC2626 100%);
        color: white;
    }
    .kpi-card-bal {
        background: #FFFFFF;
        border: 1.5px solid #BBF7D0;
        color: #15803D;
    }
    .kpi-card-bal-def {
        background: #FFFFFF;
        border: 1.5px solid #FECACA;
        color: #B91C1C;
    }
    .kpi-label {
        font-size: 11.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        opacity: 0.95;
    }
    .kpi-val {
        font-size: 22px;
        font-weight: 800;
        margin-top: 3px;
        letter-spacing: -0.3px;
    }
    .kpi-sub {
        font-size: 11px;
        margin-top: 3px;
        opacity: 0.9;
    }
    .modern-card {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        color: #1E293B !important;
        margin-bottom: 16px;
    }
    .card-title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
        border-bottom: 1.5px solid #F1F5F9;
        padding-bottom: 10px;
    }
    .card-title {
        font-size: 14px;
        font-weight: 800;
        color: #800000 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pill-green {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 3px 9px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 11px;
        display: inline-block;
    }
    .pill-red {
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 11px;
        display: inline-block;
    }
    .pill-amber {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 11px;
        display: inline-block;
    }
    .pill-blue {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 11px;
        display: inline-block;
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
        background-color: #FFFFFF !important;
        color: #1E293B !important;
    }
    .custom-table th {
        background-color: #F8FAFC !important;
        color: #475569 !important;
        font-weight: 700;
        padding: 9px 12px;
        text-align: left;
        border-bottom: 1.5px solid #E2E8F0;
        font-size: 11.5px;
        text-transform: uppercase;
    }
    .custom-table td {
        padding: 9px 12px;
        border-bottom: 1px solid #F1F5F9;
    }
    button, .stDownloadButton button {
        min-height: 40px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "rtcc@2026")
PAYEE_UPI_ID = "harshitmasrani123@okaxis"
PAYEE_NAME = "Harshit Masrani"
LIVE_APP_URL = "https://radhanagar-cultural.streamlit.app/"

DONATIONS_CSV = "donations_ledger.csv"
EXPENSES_CSV = "expenses_ledger.csv"
CONFIG_FILE = "app_config.json"

DEFAULT_BUILDINGS = ["Building 1", "Building 2", "Building 3", "Tower A", "Tower B", "Tower C", "Society Common"]
DEFAULT_INCOME_CATS = [
    "Opening Balance (Carried Forward)", "General Vargani", "Aarti Sponsorship", 
    "Prasad / Sweets", "Mahaprasad", "Maha Aarti", "Flower Decoration", 
    "Bank Savings Interest", "Scrap Sale / Raddi", "Other Miscellaneous Income"
]
DEFAULT_EXPENSE_CATS = [
    "Mandap & Stage Setup", "Sound System / DJ", "Lighting & Electrical", 
    "Idol / Murti & Pooja Samagri", "Mahaprasad & Catering", "Security & Permissions", 
    "Visarjan Arrangements", "Prize & Cultural Events", "Miscellaneous"
]

DEFAULT_SCHEDULES = [
    {"id": 1, "date": "Everyday", "time": "07:30 AM - 08:15 AM", "program": "Morning Daily Aarti & Pooja", "venue": "Central Garden Mandap", "coordinator": "Pooja Volunteers", "status": "Upcoming"},
    {"id": 2, "date": "Everyday", "time": "08:00 PM - 08:45 PM", "program": "Evening Maha Aarti & Prasad Vitran", "venue": "Central Garden Mandap", "coordinator": "Wing-Wise Volunteers", "status": "Upcoming"},
    {"id": 3, "date": "2026-09-13", "time": "08:00 PM Onwards", "program": "Bappa Aagman", "venue": "Central Garden Mandap", "coordinator": "Cultural Committee", "status": "Upcoming"},
    {"id": 4, "date": "2026-09-14", "time": "10:00 AM - 10:30 AM", "program": "Ganesh Murti Sthapana & Pranpratishtha Pooja", "venue": "Central Garden Mandap", "coordinator": "Pooja Samiti", "status": "Upcoming"}
]

# --- GITHUB SYNC HELPERS ---
def fetch_from_github(file_path):
    if not HAS_GITHUB:
        return False
    try:
        if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            file_contents = repo.get_contents(file_path)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_contents.decoded_content.decode("utf-8"))
            return True
    except Exception:
        pass
    return False

def backup_to_github(file_path):
    if not HAS_GITHUB:
        return
    try:
        if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                file_contents = repo.get_contents(file_path)
                repo.update_file(file_contents.path, f"Auto-backup {file_path}", content, file_contents.sha)
            except Exception:
                repo.create_file(file_path, f"Initial auto-backup {file_path}", content)
    except Exception as e:
        print(f"GitHub Sync Error: {e}")

def standardize_date(d_val):
    if pd.isna(d_val) or not str(d_val).strip() or str(d_val).strip().lower() == 'nan':
        return str(date.today())
    d_str = str(d_val).strip()
    if d_str.lower() == 'everyday' or 'to' in d_str.lower():
        return d_str
    clean_part = d_str.split()[0]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(clean_part, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return d_str

def clean_year(y_val):
    if pd.isna(y_val):
        return "2026"
    y_str = str(y_val).strip()
    if y_str.endswith(".0"):
        y_str = y_str[:-2]
    return y_str

def num_to_words_inr(num):
    num = int(num)
    if num == 0:
        return "Zero Rupees Only"
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    def convert_below_thousand(n):
        res = ""
        if n >= 100:
            res += units[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            res += tens[n // 10] + " "
            n %= 10
        if n > 0:
            res += units[n] + " "
        return res
    words = ""
    crores = num // 10000000
    num %= 10000000
    if crores > 0: words += convert_below_thousand(crores) + "Crore "
    lakhs = num // 100000
    num %= 100000
    if lakhs > 0: words += convert_below_thousand(lakhs) + "Lakh "
    thousands = num // 1000
    num %= 1000
    if thousands > 0: words += convert_below_thousand(thousands) + "Thousand "
    if num > 0: words += convert_below_thousand(num)
    return words.strip() + " Rupees Only"

# --- PERSISTENT STORAGE HELPERS WITH GITHUB RECOVERY ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        fetch_from_github(CONFIG_FILE)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if "buildings" not in data: data["buildings"] = DEFAULT_BUILDINGS
                if "income" not in data: data["income"] = DEFAULT_INCOME_CATS
                if "expense" not in data: data["expense"] = DEFAULT_EXPENSE_CATS
                if "start_receipt_no" not in data: data["start_receipt_no"] = 101
                if "schedules" not in data: data["schedules"] = DEFAULT_SCHEDULES
                return data
        except Exception:
            pass
    return {
        "buildings": DEFAULT_BUILDINGS, "income": DEFAULT_INCOME_CATS,
        "expense": DEFAULT_EXPENSE_CATS, "start_receipt_no": 101, "schedules": DEFAULT_SCHEDULES
    }

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(st.session_state.app_config, f, indent=4)
    backup_to_github(CONFIG_FILE)

if "app_config" not in st.session_state:
    st.session_state.app_config = load_config()

def read_donations():
    if not os.path.exists(DONATIONS_CSV):
        fetch_from_github(DONATIONS_CSV)
    if os.path.exists(DONATIONS_CSV):
        try:
            df = pd.read_csv(DONATIONS_CSV, dtype=str)
            if "Date" in df.columns: df["Date"] = df["Date"].apply(standardize_date)
            if "Year" in df.columns: df["Year"] = df["Year"].apply(clean_year)
            if "Festival" in df.columns: df["Festival"] = df["Festival"].astype(str).str.strip()
            if "Amount" in df.columns: df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(",", "").str.replace("₹", "").str.strip(), errors="coerce").fillna(0.0)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "Receipt_No", "Year", "Festival", "Donor_Name", "Bldg_No", "Flat_No", 
        "Mobile", "Amount", "Category", "Payment_Mode", "Txn_Ref", "Date"
    ])

def read_expenses():
    if not os.path.exists(EXPENSES_CSV):
        fetch_from_github(EXPENSES_CSV)
    if os.path.exists(EXPENSES_CSV):
        try:
            df = pd.read_csv(EXPENSES_CSV, dtype=str)
            if "Date" in df.columns: df["Date"] = df["Date"].apply(standardize_date)
            if "Year" in df.columns: df["Year"] = df["Year"].apply(clean_year)
            if "Festival" in df.columns: df["Festival"] = df["Festival"].astype(str).str.strip()
            if "Amount" in df.columns: df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(",", "").str.replace("₹", "").str.strip(), errors="coerce").fillna(0.0)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "Voucher_No", "Year", "Festival", "Category", "Amount", 
        "Vendor_Name", "Description", "Payment_Mode", "Date"
    ])

def save_donations_to_disk(df):
    df.to_csv(DONATIONS_CSV, index=False)
    backup_to_github(DONATIONS_CSV)
    st.session_state.donations = df

def save_expenses_to_disk(df):
    df.to_csv(EXPENSES_CSV, index=False)
    backup_to_github(EXPENSES_CSV)
    st.session_state.expenses = df

def append_donation(new_entry):
    new_entry["Date"] = standardize_date(new_entry.get("Date", date.today()))
    new_entry["Year"] = clean_year(new_entry.get("Year", date.today().year))
    new_entry["Festival"] = str(new_entry.get("Festival", "Ganeshotsav")).strip()
    current_df = read_donations()
    updated_df = pd.concat([current_df, pd.DataFrame([new_entry])], ignore_index=True)
    save_donations_to_disk(updated_df)

def append_expense(new_entry):
    new_entry["Date"] = standardize_date(new_entry.get("Date", date.today()))
    new_entry["Year"] = clean_year(new_entry.get("Year", date.today().year))
    new_entry["Festival"] = str(new_entry.get("Festival", "Ganeshotsav")).strip()
    current_df = read_expenses()
    updated_df = pd.concat([current_df, pd.DataFrame([new_entry])], ignore_index=True)
    save_expenses_to_disk(updated_df)

st.session_state.donations = read_donations()
st.session_state.expenses = read_expenses()

# --- QR & PDF GENERATORS ---
def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_payload = {"pa": upi_id, "pn": payee_name, "am": f"{amount:.2f}", "cu": "INR", "tn": note}
    upi_url = f"upi://pay?{urllib.parse.urlencode(upi_payload)}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#800000", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def generate_pdf_receipt(receipt_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []
    title_style = ParagraphStyle('HeaderTitle', fontName='Helvetica-Bold', fontSize=17, alignment=1, textColor=colors.HexColor('#800000'), spaceAfter=3)
    sub_title_style = ParagraphStyle('HeaderSub', fontName='Helvetica', fontSize=10, alignment=1, textColor=colors.HexColor('#444444'), spaceAfter=2)
    fest_style = ParagraphStyle('HeaderFest', fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.HexColor('#B8860B'), spaceAfter=10)
    label_style = ParagraphStyle('LabelStyle', fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.HexColor('#333333'))
    val_style = ParagraphStyle('ValStyle', fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor('#111111'))
    amount_style = ParagraphStyle('AmtStyle', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#800000'))
    words_style = ParagraphStyle('WordsStyle', fontName='Helvetica-Oblique', fontSize=9, textColor=colors.HexColor('#222222'))
    disclaimer_style = ParagraphStyle('Discl', fontName='Helvetica', fontSize=8.5, alignment=1, textColor=colors.HexColor('#444444'), leading=12)
    
    elements.append(Paragraph("RADHANAGAR TOWERS CULTURAL COMMITTEE", title_style))
    elements.append(Paragraph("Kalyan West, Maharashtra", sub_title_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#B8860B'), spaceAfter=8))
    elements.append(Paragraph(f"OFFICIAL DONATION RECEIPT — {str(receipt_data['Festival']).upper()} {receipt_data['Year']}", fest_style))
    
    bldg_flat = f"Wing: {receipt_data.get('Bldg_No', 'N/A')} | Flat: {receipt_data.get('Flat_No', 'N/A')}"
    mob_val = str(receipt_data.get('Mobile', ''))
    mob_display = mob_val if mob_val and mob_val.lower() != 'nan' and mob_val != '' else "N/A"
    amt_val = float(receipt_data['Amount'])
    amt_in_words = num_to_words_inr(amt_val)
    
    table_data = [
        [Paragraph("<b>Receipt No:</b>", label_style), Paragraph(str(receipt_data["Receipt_No"]), val_style), Paragraph("<b>Date:</b>", label_style), Paragraph(str(receipt_data["Date"]), val_style)],
        [Paragraph("<b>Donor Name:</b>", label_style), Paragraph(str(receipt_data["Donor_Name"]), val_style), Paragraph("<b>Premises:</b>", label_style), Paragraph(bldg_flat, val_style)],
        [Paragraph("<b>Mobile No:</b>", label_style), Paragraph(mob_display, val_style), Paragraph("<b>Payment Mode:</b>", label_style), Paragraph(str(receipt_data["Payment_Mode"]), val_style)],
        [Paragraph("<b>Category:</b>", label_style), Paragraph(str(receipt_data["Category"]), val_style), Paragraph("<b>Txn Ref / UTR:</b>", label_style), Paragraph(str(receipt_data["Txn_Ref"]), val_style)],
        [Paragraph("<b>Amount Paid:</b>", label_style), Paragraph(f"<b>Rs. {amt_val:,.2f}</b>", amount_style), "", ""],
        [Paragraph("<b>Amount in Words:</b>", label_style), Paragraph(f"<b>{amt_in_words}</b>", words_style), "", ""]
    ]
    t = Table(table_data, colWidths=[105, 165, 95, 175])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FDFDFD')),
        ('BOX', (0,0), (-1,-1), 1.2, colors.HexColor('#B8860B')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
        ('SPAN', (1, 4), (3, 4)), ('SPAN', (1, 5), (3, 5)),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Thank you for your generous contribution to the festival celebrations!", ParagraphStyle('Thanks', fontName='Helvetica-Bold', alignment=1, fontSize=9.5, textColor=colors.HexColor('#333333'))))
    elements.append(Spacer(1, 10))
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_master_financial_pdf(festival, year, donations_df, expenses_df, other_notes=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []
    title_style = ParagraphStyle('RptTitle', fontName='Helvetica-Bold', fontSize=18, alignment=1, textColor=colors.HexColor('#800000'), spaceAfter=4)
    sub_title_style = ParagraphStyle('RptSub', fontName='Helvetica', fontSize=10, alignment=1, textColor=colors.HexColor('#444444'), spaceAfter=2)
    sec_heading = ParagraphStyle('SecHead', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#800000'), spaceBefore=12, spaceAfter=6)
    tbl_hdr = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white, alignment=1)
    tbl_body = ParagraphStyle('TblTxt', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#111111'))
    tbl_body_bold = ParagraphStyle('TblTxtB', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#111111'))
    tbl_body_amt = ParagraphStyle('TblAmt', fontName='Helvetica-Bold', fontSize=8, alignment=2, textColor=colors.HexColor('#111111'))
    
    elements.append(Paragraph("RADHANAGAR TOWERS CULTURAL COMMITTEE", title_style))
    elements.append(Paragraph("Kalyan West, Maharashtra — Official Accounts Statement", sub_title_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#B8860B'), spaceAfter=8))
    elements.append(Paragraph(f"<b>ANNUAL AUDITED FESTIVAL REPORT: {festival.upper()} {year}</b>", ParagraphStyle('SubF', alignment=1, fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#B8860B'), spaceAfter=10)))
    
    total_inc = donations_df["Amount"].astype(float).sum() if not donations_df.empty else 0.0
    total_exp = expenses_df["Amount"].astype(float).sum() if not expenses_df.empty else 0.0
    net_bal = total_inc - total_exp
    
    elements.append(Paragraph("<b>SECTION 1: EXECUTIVE CATEGORY-WISE SUMMARY</b>", sec_heading))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#800000'), spaceAfter=8))
    
    overview_data = [[Paragraph("<b>Total Collections:</b>", tbl_body_bold), Paragraph(f"Rs. {total_inc:,.2f}", tbl_body_amt), Paragraph("<b>Total Expenses:</b>", tbl_body_bold), Paragraph(f"Rs. {total_exp:,.2f}", tbl_body_amt), Paragraph("<b>Net Balance:</b>", tbl_body_bold), Paragraph(f"Rs. {net_bal:,.2f}", tbl_body_amt)]]
    ov_tbl = Table(overview_data, colWidths=[105, 75, 95, 75, 95, 95])
    ov_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F5F5F5')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#B8860B')), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
    elements.append(ov_tbl)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- PERSISTENT ADMIN SESSION ---
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = True if st.query_params.get("admin") == "1" else False

if "last_entry_state" not in st.session_state: st.session_state.last_entry_state = None
if "last_non_rec_state" not in st.session_state: st.session_state.last_non_rec_state = None
if "last_expense_state" not in st.session_state: st.session_state.last_expense_state = None

# --- SIDEBAR ---
st.sidebar.markdown("""
<div style="text-align:center; margin-bottom:12px;">
    <h2 style="color:#800000; margin:0; font-size:20px;">🚩 RTCC Portal</h2>
    <small style="color:#666;">Radhanagar Towers</small>
</div>
""", unsafe_allow_html=True)

selected_year = st.sidebar.selectbox("Select Festival Year", [2027, 2026, 2025, 2024], index=1)
selected_festival = st.sidebar.selectbox("Select Festival", ["Ganeshotsav", "Navratri Utsav"], index=0)
st.sidebar.markdown("---")

nav_options = [
    "📊 Real-time Balance Sheet", 
    "✍️ Admin: Income & Donation Entry", 
    "💸 Admin: Log Expenditure",
    "📜 All Records & Reports",
    "⚙️ Master Settings (Backup, Series & Schedule)",
    "🔐 Admin Login"
] if st.session_state.admin_logged_in else [
    "📊 Real-time Balance Sheet (Public View)",
    "🔐 Admin Login"
]

menu = st.sidebar.radio("Navigation Menu", nav_options)
st.sidebar.markdown("---")

if st.session_state.admin_logged_in:
    st.sidebar.success("🔒 Admin Mode Active")
    if st.sidebar.button("🚪 Logout Admin", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.query_params["admin"] = "0"
        st.rerun()
else:
    st.sidebar.info("👁️ Public View Mode")

st.markdown(f"""
<div class="main-header">
    <div style="display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:4px;">
        <span style="font-size:24px;">✨🪔✨</span>
        <h1 style="display:inline; margin:0;">🏛️ Radhanagar Towers Cultural Committee</h1>
        <span style="font-size:24px;">✨🪔✨</span>
    </div>
    <p>Financial Transparency & Festival Ledger • <b>{selected_festival} {selected_year}</b></p>
</div>
""", unsafe_allow_html=True)

st.session_state.donations = read_donations()
st.session_state.expenses = read_expenses()

target_year_str = clean_year(selected_year)
target_fest_str = str(selected_festival).strip().lower()

filtered_donations = st.session_state.donations[
    (st.session_state.donations["Year"].astype(str).apply(clean_year) == target_year_str) & 
    (st.session_state.donations["Festival"].astype(str).str.strip().str.lower() == target_fest_str)
]
filtered_expenses = st.session_state.expenses[
    (st.session_state.expenses["Year"].astype(str).apply(clean_year) == target_year_str) & 
    (st.session_state.expenses["Festival"].astype(str).str.strip().str.lower() == target_fest_str)
]

# =========================================================
# VIEW 1: BALANCE SHEET & PUBLIC DASHBOARD
# =========================================================
if menu in ["📊 Real-time Balance Sheet", "📊 Real-time Balance Sheet (Public View)"]:
    total_income = filtered_donations["Amount"].astype(float).sum() if not filtered_donations.empty else 0.0
    total_expense = filtered_expenses["Amount"].astype(float).sum() if not filtered_expenses.empty else 0.0
    net_balance = total_income - total_expense
    
    bal_card_class = "kpi-card-bal" if net_balance >= 0 else "kpi-card-bal-def"
    bal_status_text = "🟢 In Surplus" if net_balance >= 0 else "🔴 In Deficit"
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card kpi-card-inc">
            <div class="kpi-label">📥 Total Collections</div>
            <div class="kpi-val">₹ {total_income:,.2f}</div>
            <div class="kpi-sub">Total Entries: {len(filtered_donations)}</div>
        </div>
        <div class="kpi-card kpi-card-exp">
            <div class="kpi-label">📤 Total Expenses</div>
            <div class="kpi-val">₹ {total_expense:,.2f}</div>
            <div class="kpi-sub">Total Vouchers: {len(filtered_expenses)}</div>
        </div>
        <div class="kpi-card {bal_card_class}">
            <div class="kpi-label">💰 Net Balance</div>
            <div class="kpi-val">₹ {net_balance:,.2f}</div>
            <div class="kpi-sub" style="font-weight:700;">Status: {bal_status_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Resident Finder
    with st.container():
        st.markdown("""
        <div class="modern-card" style="padding:14px 18px; margin-bottom:14px;">
            <div class="card-title-row" style="margin-bottom:10px;">
                <span class="card-title">🔍 Resident Receipt Finder</span>
                <span style="font-size:11.5px; color:#64748B; font-weight:600;">Instant Self-Service</span>
            </div>
        """, unsafe_allow_html=True)
        search_query = st.text_input("Search Receipt", placeholder="Enter Flat No (e.g. 402), Receipt No, or Name...", label_visibility="collapsed")
        if search_query and search_query.strip():
            sq = search_query.strip().lower()
            res_df = filtered_donations[
                (filtered_donations["Receipt_No"].astype(str).str.lower().str.contains(sq)) |
                (filtered_donations["Flat_No"].astype(str).str.lower().str.contains(sq)) |
                (filtered_donations["Donor_Name"].astype(str).str.lower().str.contains(sq)) |
                (filtered_donations["Bldg_No"].astype(str).str.lower().str.contains(sq))
            ]
            if not res_df.empty:
                st.success(f"Found {len(res_df)} matching donation record(s):")
                for _, r_match in res_df.iterrows():
                    col_card, col_btn = st.columns([3.2, 1])
                    with col_card:
                        b_txt = f"{r_match['Bldg_No']} - Flat {r_match['Flat_No']}" if r_match['Bldg_No'] != 'N/A' else 'General Collection'
                        st.markdown(f"""
                        <div style="background-color:#FFFFFF; border:1px solid #DCFCE7; border-radius:8px; padding:10px 12px; margin-bottom:6px; font-size:13px; color:#0F172A;">
                            <b style="color:#800000;">{r_match['Receipt_No']}</b> | <b style="color:#0F172A;">{r_match['Donor_Name']}</b> <span style="color:#475569;">({b_txt})</span><br/>
                            <span style="color:#15803D; font-weight:800;">₹{float(r_match['Amount']):,.2f}</span> | <span style="color:#1E293B;">{r_match['Category']}</span> | Mode: {r_match['Payment_Mode']} | Date: {r_match['Date']}
                        </div>
                        """, unsafe_allow_html=True)
                    with col_btn:
                        pdf_match_bytes = generate_pdf_receipt(r_match)
                        st.download_button(label=f"📄 Download", data=pdf_match_bytes, file_name=f"{r_match['Receipt_No']}.pdf", mime="application/pdf", key=f"dl_search_{r_match['Receipt_No']}", use_container_width=True)
            else:
                st.warning(f"No receipts found matching '{search_query}'.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Top 10 Donors & Cash Balances
    col_top10, col_mode_bal = st.columns([1.2, 1])
    with col_top10:
        if not filtered_donations.empty:
            don_only = filtered_donations[~filtered_donations["Category"].str.contains("Opening Balance", case=False, na=False)].copy()
            if not don_only.empty:
                top_donors_df = don_only.groupby(["Donor_Name", "Bldg_No", "Flat_No"]).agg(Total_Amt=("Amount", lambda x: float(x.sum()))).reset_index()
                top_donors_df = top_donors_df.sort_values(by="Total_Amt", ascending=False).head(10)
                donor_rows = []
                for idx, r in top_donors_df.reset_index(drop=True).iterrows():
                    b_prem = f"{r['Bldg_No']}-{r['Flat_No']}" if str(r['Bldg_No']) != 'N/A' else 'General'
                    medal = "🥇" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else f"#{idx+1}"))
                    donor_rows.append(f"""<tr><td><b>{medal} {r['Donor_Name']}</b> <span style="color:#64748B; font-size:11px;">({b_prem})</span></td><td style="text-align: right; font-weight: 700; color: #16A34A;">₹{r['Total_Amt']:,.2f}</td></tr>""")
                st.markdown(f"""<div class="modern-card"><div class="card-title-row"><span class="card-title">🏆 Top Donors Leaderboard</span><span class="pill-green">Top 10</span></div><table class="custom-table"><thead><tr><th>Donor Name & Premises</th><th style="text-align: right;">Amount</th></tr></thead><tbody>{"".join(donor_rows)}</tbody></table></div>""", unsafe_allow_html=True)
            else:
                st.markdown("""<div class="modern-card"><div class="card-title-row"><span class="card-title">🏆 Top Donors Leaderboard</span></div><p style="color:#64748B; font-size:12.5px;">No donor contributions logged yet.</p></div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="modern-card"><div class="card-title-row"><span class="card-title">🏆 Top Donors Leaderboard</span></div><p style="color:#64748B; font-size:12.5px;">No donations logged for this period.</p></div>""", unsafe_allow_html=True)

    with col_mode_bal:
        modes_track = ["Cash", "UPI / QR Code", "Bank Transfer", "Cheque"]
        pm_stats = []
        for m in modes_track:
            m_keyword = m.split()[0]
            m_inc = filtered_donations[filtered_donations["Payment_Mode"].str.contains(m_keyword, case=False, na=False)]["Amount"].astype(float).sum() if not filtered_donations.empty else 0.0
            m_exp = filtered_expenses[filtered_expenses["Payment_Mode"].str.contains(m_keyword, case=False, na=False)]["Amount"].astype(float).sum() if not filtered_expenses.empty else 0.0
            pm_stats.append({"mode": m, "inc": m_inc, "exp": m_exp, "net": m_inc - m_exp})
            
        cash_inflow = next(item["inc"] for item in pm_stats if item["mode"] == "Cash")
        cash_outflow = next(item["exp"] for item in pm_stats if item["mode"] == "Cash")
        cash_net = cash_inflow - cash_outflow
        digital_inflow = total_income - cash_inflow
        digital_outflow = total_expense - cash_outflow
        digital_net = digital_inflow - digital_outflow
        
        st.markdown(f"""
        <div class="modern-card">
            <div class="card-title-row"><span class="card-title">💳 Cash vs Digital Balances</span></div>
            <div style="margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #F1F5F9;">
                <div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 13px; font-weight: 700; color: #1E293B;">💵 Physical Cash In-Hand</span><span class="pill-{'green' if cash_net >= 0 else 'red'}">{'In Hand' if cash_net >= 0 else 'Shortage'}</span></div>
                <div style="font-size: 20px; font-weight: 800; color: {'#15803D' if cash_net >= 0 else '#B91C1C'}; margin-top: 2px;">₹{cash_net:,.2f}</div>
                <div style="font-size: 11px; color: #64748B; margin-top: 2px;">In: ₹{cash_inflow:,.2f} | Out: ₹{cash_outflow:,.2f}</div>
            </div>
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 13px; font-weight: 700; color: #1E293B;">📱 Bank & UPI Balance</span><span class="pill-{'green' if digital_net >= 0 else 'red'}">Active</span></div>
                <div style="font-size: 20px; font-weight: 800; color: {'#15803D' if digital_net >= 0 else '#B91C1C'}; margin-top: 2px;">₹{digital_net:,.2f}</div>
                <div style="font-size: 11px; color: #64748B; margin-top: 2px;">In: ₹{digital_inflow:,.2f} | Out: ₹{digital_outflow:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# ADMIN LOGIN VIEW
# =========================================================
elif menu == "🔐 Admin Login":
    st.subheader("🔐 Committee Member & Admin Login")
    col_l1, col_l2 = st.columns([1, 1])
    with col_l1:
        pwd_input = st.text_input("Enter Admin Password", type="password", placeholder="••••••••")
        if st.button("Unlock Admin Portal", type="primary", use_container_width=True):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.query_params["admin"] = "1"
                st.rerun()
            else:
                st.error("❌ Incorrect Password.")

# =========================================================
# VIEW 2: INCOME ENTRY
# =========================================================
elif menu == "✍️ Admin: Income & Donation Entry" and st.session_state.admin_logged_in:
    st.subheader(f"✍️ Income Entry Portal — {selected_festival} {selected_year}")
    if st.session_state.last_entry_state is not None:
        entry = st.session_state.last_entry_state
        st.success(f"🎉 **Entry {entry['Receipt_No']} Recorded & Auto-Backed up to GitHub!**")
        if st.button("➕ Record Next Entry", type="primary"):
            st.session_state.last_entry_state = None
            st.rerun()
    else:
        donor_name = st.text_input("Donor Full Name*", placeholder="e.g. Ramesh Patil")
        c_bldg, c_flat = st.columns(2)
        bldg_no = c_bldg.selectbox("Building / Wing No.*", st.session_state.app_config["buildings"])
        flat_no = c_flat.text_input("Flat No.*", placeholder="e.g. 402")
        c_mob, c_amt = st.columns(2)
        raw_mob = c_mob.text_input("Mobile Number (Optional)", max_chars=10)
        amount = c_amt.number_input("Donation Amount (₹)*", min_value=1.0, value=500.0)
        category = st.selectbox("Donation Category", [c for c in st.session_state.app_config["income"] if not c.startswith("Opening Balance")])
        c_mode, c_ref = st.columns(2)
        payment_mode = c_mode.selectbox("Payment Mode*", ["Cash", "UPI / QR Code", "Cheque", "Bank Transfer"])
        txn_ref = c_ref.text_input("Transaction / UTR No.", value="CASH RECEIVED" if payment_mode == "Cash" else "")
        
        if st.button("💾 Confirm & Generate Official Receipt", type="primary", use_container_width=True):
            if not donor_name or not flat_no:
                st.error("Please fill in mandatory fields.")
            else:
                fresh_df = read_donations()
                receipt_no = f"RTCC-{selected_year}-{int(st.session_state.app_config.get('start_receipt_no', 101)) + len(fresh_df)}"
                new_entry = {
                    "Receipt_No": receipt_no, "Year": clean_year(selected_year), "Festival": str(selected_festival).strip(),
                    "Donor_Name": donor_name, "Bldg_No": bldg_no, "Flat_No": flat_no, "Mobile": raw_mob,
                    "Amount": float(amount), "Category": category, "Payment_Mode": payment_mode, "Txn_Ref": txn_ref, "Date": str(date.today())
                }
                append_donation(new_entry)
                st.session_state.last_entry_state = new_entry
                st.rerun()

# =========================================================
# VIEW 3: LOG EXPENDITURE
# =========================================================
elif menu == "💸 Admin: Log Expenditure" and st.session_state.admin_logged_in:
    st.subheader(f"💸 Log Expenditure — {selected_festival} {selected_year}")
    col1, col2 = st.columns(2)
    category = col1.selectbox("Expense Category", st.session_state.app_config["expense"])
    amount = col2.number_input("Expense Amount (₹)*", min_value=1.0, step=100.0)
    col3, col4 = st.columns(2)
    vendor_name = col3.text_input("Vendor / Payee Name*")
    payment_mode = col4.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer", "Cheque"])
    description = st.text_area("Details")
    if st.button("💾 Record Expenditure", type="primary", use_container_width=True):
        if not vendor_name or amount <= 0:
            st.error("Please fill in valid details.")
        else:
            fresh_exp = read_expenses()
            voucher_no = f"EXP-{selected_year}-{len(fresh_exp)+201}"
            new_exp = {
                "Voucher_No": voucher_no, "Year": clean_year(selected_year), "Festival": str(selected_festival).strip(),
                "Category": category, "Amount": float(amount), "Vendor_Name": vendor_name,
                "Description": description, "Payment_Mode": payment_mode, "Date": str(date.today())
            }
            append_expense(new_exp)
            st.success("Expense recorded & backed up to GitHub!")
            st.rerun()

# =========================================================
# VIEW 4: ALL RECORDS & REPORTS
# =========================================================
elif menu == "📜 All Records & Reports" and st.session_state.admin_logged_in:
    st.subheader("📜 All Records & Reports")
    tab1, tab2 = st.tabs(["📥 Income Ledger", "📤 Expense Ledger"])
    with tab1:
        if not filtered_donations.empty:
            st.dataframe(filtered_donations, use_container_width=True, hide_index=True)
        else:
            st.info("No income records found.")
    with tab2:
        if not filtered_expenses.empty:
            st.dataframe(filtered_expenses, use_container_width=True, hide_index=True)
        else:
            st.info("No expense records found.")

# =========================================================
# VIEW 5: MASTER SETTINGS
# =========================================================
elif menu == "⚙️ Master Settings (Backup, Series & Schedule)" and st.session_state.admin_logged_in:
    st.subheader("⚙️ Master System Setup & Data Backups")
    st.markdown("### 🔄 Database Backup & Version Restore")
    col_bak_d, col_bak_u = st.columns(2)
    with col_bak_d:
        st.download_button("💾 Download Donations Backup (CSV)", data=read_donations().to_csv(index=False).encode('utf-8'), file_name="donations_ledger.csv", mime="text/csv", use_container_width=True)
        st.download_button("💾 Download Expenses Backup (CSV)", data=read_expenses().to_csv(index=False).encode('utf-8'), file_name="expenses_ledger.csv", mime="text/csv", use_container_width=True)
    with col_bak_u:
        up_don_file = st.file_uploader("Restore Donations Ledger (Upload CSV)", type=["csv"], key="up_don_direct")
        if up_don_file is not None:
            if st.button("⚡ Overwrite Donations DB", type="primary"):
                save_donations_to_disk(pd.read_csv(up_don_file, dtype=str))
                st.success("Donations restored & backed up!")
                st.rerun()
