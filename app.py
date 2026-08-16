import streamlit as st
import pandas as pd
from datetime import date
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

st.set_page_config(
    page_title="Radhanagar Towers Cultural Committee", 
    page_icon="🪔", 
    layout="wide"
)

# --- STYLING ---
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #800000 0%, #B8860B 100%);
        padding: 22px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: #FFF9E6 !important;
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .main-header p {
        color: #F7E7CE;
        margin-top: 5px;
        font-size: 14px;
    }
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E9EF;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    .valid-phone {
        color: #28a745;
        font-weight: 600;
        font-size: 12px;
    }
    .opt-label {
        font-size: 12px;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
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

# --- INDIAN NUMBER TO WORDS ---
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
    if crores > 0:
        words += convert_below_thousand(crores) + "Crore "
    lakhs = num // 100000
    num %= 100000
    if lakhs > 0:
        words += convert_below_thousand(lakhs) + "Lakh "
    thousands = num // 1000
    num %= 1000
    if thousands > 0:
        words += convert_below_thousand(thousands) + "Thousand "
    if num > 0:
        words += convert_below_thousand(num)
    return words.strip() + " Rupees Only"

# --- PERSISTENT DATA HELPERS ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if "buildings" not in data: data["buildings"] = DEFAULT_BUILDINGS
                if "income" not in data: data["income"] = DEFAULT_INCOME_CATS
                if "expense" not in data: data["expense"] = DEFAULT_EXPENSE_CATS
                if "start_receipt_no" not in data: data["start_receipt_no"] = 101
                return data
        except Exception:
            pass
    return {
        "buildings": DEFAULT_BUILDINGS,
        "income": DEFAULT_INCOME_CATS,
        "expense": DEFAULT_EXPENSE_CATS,
        "start_receipt_no": 101
    }

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(st.session_state.app_config, f, indent=4)

if "app_config" not in st.session_state:
    st.session_state.app_config = load_config()

def read_donations():
    if os.path.exists(DONATIONS_CSV):
        try:
            df = pd.read_csv(DONATIONS_CSV, dtype={"Receipt_No": str, "Mobile": str, "Flat_No": str, "Bldg_No": str})
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "Receipt_No", "Year", "Festival", "Donor_Name", "Bldg_No", "Flat_No", 
        "Mobile", "Amount", "Category", "Payment_Mode", "Txn_Ref", "Date"
    ])

def read_expenses():
    if os.path.exists(EXPENSES_CSV):
        try:
            df = pd.read_csv(EXPENSES_CSV, dtype={"Voucher_No": str})
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "Voucher_No", "Year", "Festival", "Category", "Amount", 
        "Vendor_Name", "Description", "Payment_Mode", "Date"
    ])

def append_donation(new_entry):
    current_df = read_donations()
    updated_df = pd.concat([current_df, pd.DataFrame([new_entry])], ignore_index=True)
    updated_df.to_csv(DONATIONS_CSV, index=False)
    st.session_state.donations = updated_df

def append_expense(new_entry):
    current_df = read_expenses()
    updated_df = pd.concat([current_df, pd.DataFrame([new_entry])], ignore_index=True)
    updated_df.to_csv(EXPENSES_CSV, index=False)
    st.session_state.expenses = updated_df

st.session_state.donations = read_donations()
st.session_state.expenses = read_expenses()

# --- HELPER: UPI QR CODE ---
def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_payload = {
        "pa": upi_id, "pn": payee_name, "am": f"{amount:.2f}",
        "cu": "INR", "tn": note
    }
    upi_url = f"upi://pay?{urllib.parse.urlencode(upi_payload)}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#800000", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# --- HELPER: PDF RECEIPT ---
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
        [Paragraph("<b>Receipt No:</b>", label_style), Paragraph(str(receipt_data["Receipt_No"]), val_style), 
         Paragraph("<b>Date:</b>", label_style), Paragraph(str(receipt_data["Date"]), val_style)],
        [Paragraph("<b>Donor Name:</b>", label_style), Paragraph(str(receipt_data["Donor_Name"]), val_style), 
         Paragraph("<b>Premises:</b>", label_style), Paragraph(bldg_flat, val_style)],
        [Paragraph("<b>Mobile No:</b>", label_style), Paragraph(mob_display, val_style), 
         Paragraph("<b>Payment Mode:</b>", label_style), Paragraph(str(receipt_data["Payment_Mode"]), val_style)],
        [Paragraph("<b>Category:</b>", label_style), Paragraph(str(receipt_data["Category"]), val_style), 
         Paragraph("<b>Txn Ref / UTR:</b>", label_style), Paragraph(str(receipt_data["Txn_Ref"]), val_style)],
        [Paragraph("<b>Amount Paid:</b>", label_style), Paragraph(f"<b>Rs. {amt_val:,.2f}</b>", amount_style), "", ""],
        [Paragraph("<b>Amount in Words:</b>", label_style), Paragraph(f"<b>{amt_in_words}</b>", words_style), "", ""]
    ]
    
    t = Table(table_data, colWidths=[105, 165, 95, 175])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FDFDFD')),
        ('BOX', (0,0), (-1,-1), 1.2, colors.HexColor('#B8860B')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E5E5')),
        ('SPAN', (1, 4), (3, 4)),
        ('SPAN', (1, 5), (3, 5)),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Thank you for your generous contribution to the festival celebrations!", ParagraphStyle('Thanks', fontName='Helvetica-Bold', alignment=1, fontSize=9.5, textColor=colors.HexColor('#333333'))))
    elements.append(Spacer(1, 10))
    
    disclaimer_text = (
        "<b>Note:</b> This is a computer-generated digital receipt and does not require a physical signature.<br/>"
        "To view all festival balance sheets and transparency accounts in real-time, visit:<br/>"
        f'<font color="#0056b3"><u><a href="{LIVE_APP_URL}">{LIVE_APP_URL}</a></u></font>'
    )
    disc_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[540])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(disc_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- HELPER: SECTION 1, 1B, 2, & 3 MASTER FINANCIAL REPORT PDF ---
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
    
    bullet_style = ParagraphStyle(
        'BulletTxt', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#222222'),
        leading=13, leftIndent=15, spaceAfter=2
    )
    sub_bullet_style = ParagraphStyle(
        'SubBulletTxt', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#444444'),
        leading=12, leftIndent=32, spaceAfter=2
    )
    
    # Cover / Header
    elements.append(Paragraph("RADHANAGAR TOWERS CULTURAL COMMITTEE", title_style))
    elements.append(Paragraph("Kalyan West, Maharashtra — Official Accounts Statement", sub_title_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#B8860B'), spaceAfter=8))
    elements.append(Paragraph(f"<b>ANNUAL AUDITED FESTIVAL REPORT: {festival.upper()} {year}</b>", ParagraphStyle('SubF', alignment=1, fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#B8860B'), spaceAfter=10)))
    
    total_inc = donations_df["Amount"].astype(float).sum() if not donations_df.empty else 0.0
    total_exp = expenses_df["Amount"].astype(float).sum() if not expenses_df.empty else 0.0
    net_bal = total_inc - total_exp
    
    # ==========================================
    # SECTION 1: CATEGORY-WISE SUMMARY
    # ==========================================
    elements.append(Paragraph("<b>SECTION 1: EXECUTIVE CATEGORY-WISE SUMMARY</b>", sec_heading))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#800000'), spaceAfter=8))
    
    overview_data = [
        [Paragraph("<b>Total Collections (Income):</b>", tbl_body_bold), Paragraph(f"Rs. {total_inc:,.2f}", tbl_body_amt),
         Paragraph("<b>Total Expenses:</b>", tbl_body_bold), Paragraph(f"Rs. {total_exp:,.2f}", tbl_body_amt),
         Paragraph("<b>Net Balance:</b>", tbl_body_bold), Paragraph(f"Rs. {net_bal:,.2f}", tbl_body_amt)]
    ]
    ov_tbl = Table(overview_data, colWidths=[105, 75, 95, 75, 95, 95])
    ov_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F5F5F5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#B8860B')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(ov_tbl)
    elements.append(Spacer(1, 10))
    
    inc_cat_data = [[Paragraph("<b>Income Category</b>", tbl_hdr), Paragraph("<b>Entries</b>", tbl_hdr), Paragraph("<b>Amount (Rs.)</b>", tbl_hdr)]]
    if not donations_df.empty:
        inc_group = donations_df.groupby("Category").agg(amt=("Amount", lambda x: float(x.sum())), count=("Amount", "count")).reset_index()
        for _, row in inc_group.iterrows():
            inc_cat_data.append([Paragraph(str(row["Category"]), tbl_body), Paragraph(str(row["count"]), tbl_body), Paragraph(f"{row['amt']:,.2f}", tbl_body_amt)])
        inc_cat_data.append([Paragraph("<b>TOTAL INCOME</b>", tbl_body_bold), Paragraph(f"<b>{len(donations_df)}</b>", tbl_body_bold), Paragraph(f"<b>Rs. {total_inc:,.2f}</b>", tbl_body_amt)])
    else:
        inc_cat_data.append([Paragraph("No income logged", tbl_body), Paragraph("0", tbl_body), Paragraph("0.00", tbl_body_amt)])
        
    t_inc_sum = Table(inc_cat_data, colWidths=[160, 45, 60])
    t_inc_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e7e34')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    exp_cat_data = [[Paragraph("<b>Expense Category</b>", tbl_hdr), Paragraph("<b>Bills</b>", tbl_hdr), Paragraph("<b>Amount (Rs.)</b>", tbl_hdr)]]
    if not expenses_df.empty:
        exp_group = expenses_df.groupby("Category").agg(amt=("Amount", lambda x: float(x.sum())), count=("Amount", "count")).reset_index()
        for _, row in exp_group.iterrows():
            exp_cat_data.append([Paragraph(str(row["Category"]), tbl_body), Paragraph(str(row["count"]), tbl_body), Paragraph(f"{row['amt']:,.2f}", tbl_body_amt)])
        exp_cat_data.append([Paragraph("<b>TOTAL EXPENSES</b>", tbl_body_bold), Paragraph(f"<b>{len(expenses_df)}</b>", tbl_body_bold), Paragraph(f"<b>Rs. {total_exp:,.2f}</b>", tbl_body_amt)])
    else:
        exp_cat_data.append([Paragraph("No expenses logged", tbl_body), Paragraph("0", tbl_body), Paragraph("0.00", tbl_body_amt)])
        
    t_exp_sum = Table(exp_cat_data, colWidths=[160, 45, 60])
    t_exp_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#bd2130')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    cat_container = Table([[t_inc_sum, t_exp_sum]], colWidths=[268, 272])
    cat_container.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(cat_container)
    elements.append(Spacer(1, 14))

    # ==========================================
    # SECTION 1B: BUILDING / WING-WISE ANALYSIS
    # ==========================================
    elements.append(Paragraph("<b>SECTION 1B: BUILDING & WING-WISE CONTRIBUTION ANALYSIS</b>", ParagraphStyle('SecHeadB', fontName='Helvetica-Bold', fontSize=10.5, textColor=colors.HexColor('#800000'), spaceBefore=4, spaceAfter=4)))
    bldg_tbl_data = [[Paragraph("<b>Building / Wing</b>", tbl_hdr), Paragraph("<b>Total Donors / Units</b>", tbl_hdr), Paragraph("<b>Total Contribution (Rs.)</b>", tbl_hdr), Paragraph("<b>% of Collection</b>", tbl_hdr)]]
    
    if not donations_df.empty:
        b_df = donations_df[donations_df["Bldg_No"] != "N/A"].copy()
        if not b_df.empty:
            b_summary = b_df.groupby("Bldg_No").agg(amt=("Amount", lambda x: float(x.sum())), count=("Amount", "count")).reset_index()
            b_summary = b_summary.sort_values(by="amt", ascending=False)
            for _, r in b_summary.iterrows():
                pct = (r['amt'] / total_inc * 100) if total_inc > 0 else 0
                bldg_tbl_data.append([
                    Paragraph(str(r["Bldg_No"]), tbl_body),
                    Paragraph(str(r["count"]), tbl_body),
                    Paragraph(f"{r['amt']:,.2f}", tbl_body_amt),
                    Paragraph(f"{pct:.1f}%", tbl_body_amt)
                ])
        else:
            bldg_tbl_data.append([Paragraph("No residential building donations logged", tbl_body), "0", "0.00", "0%"])
    else:
        bldg_tbl_data.append([Paragraph("No donation records", tbl_body), "0", "0.00", "0%"])
        
    t_bldg = Table(bldg_tbl_data, colWidths=[180, 110, 140, 110])
    t_bldg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#800000')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    elements.append(t_bldg)
    elements.append(Spacer(1, 15))
    
    # ==========================================
    # SECTION 2: DETAILED ITEM-BY-ITEM LEDGERS
    # ==========================================
    elements.append(Paragraph("<b>SECTION 2: DETAILED INCOME & EXPENDITURE LEDGERS</b>", sec_heading))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#800000'), spaceAfter=8))
    
    # 2A: Detailed Income / Donations List
    elements.append(Paragraph("<b>2A. Detailed Income & Collections (Opening Balance, Donations, Interests)</b>", ParagraphStyle('SubSub', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1e7e34'), spaceAfter=4)))
    don_tbl_data = [[
        Paragraph("<b>Ref / Receipt #</b>", tbl_hdr), Paragraph("<b>Date</b>", tbl_hdr), Paragraph("<b>Source / Donor Name</b>", tbl_hdr), 
        Paragraph("<b>Premises</b>", tbl_hdr), Paragraph("<b>Mode</b>", tbl_hdr), Paragraph("<b>Category</b>", tbl_hdr), Paragraph("<b>Amount (Rs.)</b>", tbl_hdr)
    ]]
    if not donations_df.empty:
        for _, row in donations_df.iterrows():
            prem = f"{row.get('Bldg_No', '')}-{row.get('Flat_No', '')}" if row.get('Bldg_No', '') != 'N/A' else 'General'
            don_tbl_data.append([
                Paragraph(str(row["Receipt_No"]), tbl_body), Paragraph(str(row["Date"]), tbl_body),
                Paragraph(str(row["Donor_Name"]), tbl_body), Paragraph(prem, tbl_body),
                Paragraph(str(row["Payment_Mode"]), tbl_body), Paragraph(str(row["Category"]), tbl_body),
                Paragraph(f"{float(row['Amount']):,.2f}", tbl_body_amt)
            ])
    else:
        don_tbl_data.append([Paragraph("No income records available", tbl_body), "", "", "", "", "", "0.00"])
        
    t_don_det = Table(don_tbl_data, colWidths=[75, 50, 110, 60, 60, 110, 75])
    t_don_det.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#28a745')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    elements.append(t_don_det)
    elements.append(Spacer(1, 14))
    
    # 2B: Detailed Expenses List
    elements.append(Paragraph("<b>2B. Detailed Operational Expenditure Entries</b>", ParagraphStyle('SubSub', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#bd2130'), spaceAfter=4)))
    exp_tbl_data = [[
        Paragraph("<b>Voucher #</b>", tbl_hdr), Paragraph("<b>Date</b>", tbl_hdr), Paragraph("<b>Vendor / Payee</b>", tbl_hdr), 
        Paragraph("<b>Mode</b>", tbl_hdr), Paragraph("<b>Category</b>", tbl_hdr), Paragraph("<b>Description</b>", tbl_hdr), Paragraph("<b>Amount (Rs.)</b>", tbl_hdr)
    ]]
    if not expenses_df.empty:
        for _, row in expenses_df.iterrows():
            desc = str(row.get('Description', '')) if str(row.get('Description', '')) != 'nan' else '-'
            exp_tbl_data.append([
                Paragraph(str(row["Voucher_No"]), tbl_body), Paragraph(str(row["Date"]), tbl_body),
                Paragraph(str(row["Vendor_Name"]), tbl_body), Paragraph(str(row["Payment_Mode"]), tbl_body),
                Paragraph(str(row["Category"]), tbl_body), Paragraph(desc[:40], tbl_body),
                Paragraph(f"{float(row['Amount']):,.2f}", tbl_body_amt)
            ])
    else:
        exp_tbl_data.append([Paragraph("No expense records available", tbl_body), "", "", "", "", "", "0.00"])
        
    t_exp_det = Table(exp_tbl_data, colWidths=[70, 50, 100, 60, 110, 80, 70])
    t_exp_det.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dc3545')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    elements.append(t_exp_det)
    elements.append(Spacer(1, 14))

    # ==========================================
    # SECTION 3: OTHERS / COMMITTEE NOTES (OPTIONAL)
    # ==========================================
    if other_notes and other_notes.strip():
        elements.append(Paragraph("<b>SECTION 3: OTHERS / COMMITTEE NOTES</b>", sec_heading))
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#800000'), spaceAfter=8))
        
        lines = other_notes.split('\n')
        for raw_line in lines:
            if not raw_line.strip():
                continue
            is_sub_bullet = raw_line.startswith('  ') or raw_line.startswith('\t')
            clean_text = raw_line.strip().lstrip("•-*0123456789.) ")
            
            if is_sub_bullet:
                elements.append(Paragraph(f"– &nbsp; {clean_text}", sub_bullet_style))
            else:
                elements.append(Paragraph(f"• &nbsp; <b>{clean_text}</b>" if clean_text.endswith(':') else f"• &nbsp; {clean_text}", bullet_style))
                
        elements.append(Spacer(1, 14))
    
    # Signatures
    sig_data = [
        [Paragraph("<b>Prepared by Treasurer</b>", tbl_body_bold), Paragraph("<b>Audited & Verified by President / Secretary</b>", ParagraphStyle('SigR', alignment=2, fontName='Helvetica-Bold', fontSize=8))]
    ]
    sig_tbl = Table(sig_data, colWidths=[270, 270])
    sig_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 0.5, colors.HexColor('#666666')),
        ('LINEABOVE', (1,0), (1,0), 0.5, colors.HexColor('#666666')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(sig_tbl)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- PERSISTENT ADMIN SESSION ---
if "admin_logged_in" not in st.session_state:
    if st.query_params.get("admin") == "1":
        st.session_state.admin_logged_in = True
    else:
        st.session_state.admin_logged_in = False

if "last_entry_state" not in st.session_state:
    st.session_state.last_entry_state = None

if "last_non_rec_state" not in st.session_state:
    st.session_state.last_non_rec_state = None

if "last_expense_state" not in st.session_state:
    st.session_state.last_expense_state = None

# --- SIDEBAR ---
st.sidebar.markdown("""
<div style="text-align:center; margin-bottom:15px;">
    <h2 style="color:#800000; margin:0;">🚩 RTCC Portal</h2>
    <small style="color:#666;">Radhanagar Towers</small>
</div>
""", unsafe_allow_html=True)

selected_year = st.sidebar.selectbox("Select Festival Year", [2027, 2026, 2025, 2024], index=1)
selected_festival = st.sidebar.selectbox("Select Festival", ["Ganeshotsav", "Navratri Utsav"], index=0)
st.sidebar.markdown("---")

if st.session_state.admin_logged_in:
    nav_options = [
        "📊 Real-time Balance Sheet", 
        "✍️ Admin: Income & Donation Entry", 
        "💸 Admin: Log Expenditure",
        "📜 All Records & Reports",
        "⚙️ Master Settings (Backup & Series)"
    ]
else:
    nav_options = [
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

# Banner
st.markdown(f"""
<div class="main-header">
    <h1>🏛️ Radhanagar Towers Cultural Committee</h1>
    <p>Financial Transparency & Festival Ledger • <b>{selected_festival} {selected_year}</b></p>
</div>
""", unsafe_allow_html=True)

# Fresh read from disk
st.session_state.donations = read_donations()
st.session_state.expenses = read_expenses()

filtered_donations = st.session_state.donations[
    (st.session_state.donations["Year"].astype(str) == str(selected_year)) & 
    (st.session_state.donations["Festival"] == selected_festival)
]
filtered_expenses = st.session_state.expenses[
    (st.session_state.expenses["Year"].astype(str) == str(selected_year)) & 
    (st.session_state.expenses["Festival"] == selected_festival)
]

# =========================================================
# VIEW 1: REAL-TIME BALANCE SHEET (PUBLIC & ADMIN)
# =========================================================
if menu in ["📊 Real-time Balance Sheet", "📊 Real-time Balance Sheet (Public View)"]:
    total_income = filtered_donations["Amount"].astype(float).sum() if not filtered_donations.empty else 0.0
    total_expense = filtered_expenses["Amount"].astype(float).sum() if not filtered_expenses.empty else 0.0
    net_balance = total_income - total_expense
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e7e34 0%, #28a745 100%); padding: 18px 20px; border-radius: 12px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
            <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.9;">📥 Total Collections (Income)</div>
            <div style="font-size: 26px; font-weight: 700; margin-top: 6px;">₹ {total_income:,.2f}</div>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.85;">Total Entries: {len(filtered_donations)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #bd2130 0%, #dc3545 100%); padding: 18px 20px; border-radius: 12px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
            <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">📤 Total Expenses</div>
            <div style="font-size: 26px; font-weight: 700; margin-top: 6px;">₹ {total_expense:,.2f}</div>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.85;">Total Vouchers: {len(filtered_expenses)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        bal_color = "#155724" if net_balance >= 0 else "#721c24"
        bal_bg = "#d4edda" if net_balance >= 0 else "#f8d7da"
        bal_border = "#c3e6cb" if net_balance >= 0 else "#f5c6cb"
        st.markdown(f"""
        <div style="background-color: {bal_bg}; border: 1px solid {bal_border}; padding: 18px 20px; border-radius: 12px; color: {bal_color}; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">💰 Net Balance / Surplus</div>
            <div style="font-size: 26px; font-weight: 700; margin-top: 6px;">₹ {net_balance:,.2f}</div>
            <div style="font-size: 12px; margin-top: 4px; font-weight: 600;">Status: {'🟢 In Surplus' if net_balance >= 0 else '🔴 In Deficit'}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # =========================================================
    # MODERN HORIZONTAL BUILDING CONTRIBUTION DASHBOARD
    # =========================================================
    st.markdown("### 🏢 Building & Wing-Wise Contribution Analytics")
    bldg_donations = filtered_donations[filtered_donations["Bldg_No"] != "N/A"].copy() if not filtered_donations.empty else pd.DataFrame()
    
    if not bldg_donations.empty:
        col_chart_box, col_tbl_box = st.columns([1.3, 0.9])
        
        # Aggregate and calculate percentages
        bldg_summary_df = bldg_donations.groupby("Bldg_No").agg(
            Total_Amount=("Amount", lambda x: float(x.sum())),
            Donor_Count=("Amount", "count")
        ).reset_index()
        
        bldg_summary_df = bldg_summary_df.sort_values(by="Total_Amount", ascending=False)
        max_bldg_val = bldg_summary_df["Total_Amount"].max() if not bldg_summary_df.empty else 1.0
        
        with col_chart_box:
            st.markdown("""
            <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <span style="font-size: 14px; font-weight: 700; color: #800000; text-transform: uppercase; letter-spacing: 0.5px;">🏢 Wing Collection Leaderboard</span>
                    <span style="font-size: 12px; color: #888; font-weight: 500;">Sorted by Top Contributions</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Render custom horizontal cards
            for _, r in bldg_summary_df.iterrows():
                b_name = r["Bldg_No"]
                b_amt = r["Total_Amount"]
                b_cnt = r["Donor_Count"]
                
                # Proportions
                bar_pct = (b_amt / max_bldg_val) * 100
                total_pct = (b_amt / total_income * 100) if total_income > 0 else 0
                
                st.markdown(f"""
                <div style="margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                        <span style="font-size: 14px; font-weight: 600; color: #222;">
                            🏛️ <b>{b_name}</b> 
                            <span style="font-size: 11.5px; color: #666; font-weight: normal; margin-left: 6px;">({b_cnt} {'Donor' if b_cnt == 1 else 'Donors'})</span>
                        </span>
                        <span>
                            <b style="font-size: 14px; color: #800000;">₹{b_amt:,.2f}</b>
                            <span style="font-size: 11.5px; background-color: #FFF3E0; color: #D97706; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-left: 6px;">{total_pct:.1f}%</span>
                        </span>
                    </div>
                    <div style="width: 100%; background-color: #F1F3F5; height: 10px; border-radius: 6px; overflow: hidden;">
                        <div style="width: {bar_pct}%; background: linear-gradient(90deg, #800000 0%, #B8860B 100%); height: 100%; border-radius: 6px; transition: width 0.5s ease;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_tbl_box:
            st.markdown("""
            <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                <div style="font-size: 14px; font-weight: 700; color: #444; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;">📋 Unit Breakdown</div>
            """, unsafe_allow_html=True)
            
            bldg_summary_tbl = bldg_summary_df.rename(columns={
                "Bldg_No": "Building / Wing",
                "Total_Amount": "Amount (₹)",
                "Donor_Count": "Donors"
            })
            
            st.dataframe(
                bldg_summary_tbl.style.format({"Amount (₹)": "₹ {:,.2f}"}),
                use_container_width=True,
                hide_index=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No building-specific donations logged yet to generate analytics.")
	
    # Category Breakdowns
    col_inc, col_exp = st.columns(2)
    
    with col_inc:
        st.markdown("""<div style="border-bottom: 2px solid #28a745; padding-bottom: 6px; margin-bottom: 12px;"><h4 style="color: #1e7e34; margin: 0;">📥 Income & Collections (Categorized)</h4></div>""", unsafe_allow_html=True)
        if not filtered_donations.empty:
            inc_cat = filtered_donations.groupby("Category").agg(
                Total_Amount=("Amount", lambda x: float(x.sum())),
                Count=("Amount", "count")
            ).reset_index()
            st.dataframe(inc_cat.rename(columns={"Category": "Income Category", "Total_Amount": "Amount (₹)", "Count": "Entries"}).style.format({"Amount (₹)": "₹ {:,.2f}"}), use_container_width=True, hide_index=True)
            
            if st.session_state.admin_logged_in:
                with st.expander("🔎 [Admin] View Itemized Income & Donor Records"):
                    disp_inc = filtered_donations[["Receipt_No", "Donor_Name", "Bldg_No", "Flat_No", "Category", "Amount", "Payment_Mode"]].copy()
                    st.dataframe(disp_inc.style.format({"Amount": "₹ {:,.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.caption("🔒 *Individual donor entries are restricted to committee admin view.*")
        else:
            st.info("No income records found for this period.")

    with col_exp:
        st.markdown("""<div style="border-bottom: 2px solid #dc3545; padding-bottom: 6px; margin-bottom: 12px;"><h4 style="color: #bd2130; margin: 0;">📤 Operational Expenditures (Categorized)</h4></div>""", unsafe_allow_html=True)
        if not filtered_expenses.empty:
            exp_cat = filtered_expenses.groupby("Category").agg(
                Total_Spent=("Amount", lambda x: float(x.sum())),
                Bill_Count=("Amount", "count")
            ).reset_index()
            st.dataframe(exp_cat.rename(columns={"Category": "Expense Category", "Total_Spent": "Amount (₹)", "Bill_Count": "Vouchers"}).style.format({"Amount (₹)": "₹ {:,.2f}"}), use_container_width=True, hide_index=True)
            
            if st.session_state.admin_logged_in:
                with st.expander("🔎 [Admin] View Itemized Expense Records"):
                    disp_exp = filtered_expenses[["Voucher_No", "Vendor_Name", "Category", "Amount", "Payment_Mode", "Description"]].copy()
                    st.dataframe(disp_exp.style.format({"Amount": "₹ {:,.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.caption("🔒 *Detailed vendor and item vouchers are restricted to committee admin view.*")
        else:
            st.info("No expenditure records found for this period.")

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
                st.success("✅ Password verified! Unlocking portal...")
                st.rerun()
            else:
                st.error("❌ Incorrect Password. Please check with the Cultural Committee.")

# =========================================================
# VIEW 2: INCOME ENTRY (DONATIONS + OPENING BALANCE / NON-RECEIPT)
# =========================================================
elif menu == "✍️ Admin: Income & Donation Entry":
    st.subheader(f"✍️ Income Entry Portal — {selected_festival} {selected_year}")
    
    # 1. State: Resident Donation Receipt Generated
    if st.session_state.last_entry_state is not None:
        entry = st.session_state.last_entry_state
        receipt_no = entry["Receipt_No"]
        
        st.success(f"🎉 **Entry {receipt_no} Recorded Successfully!**")
        mob_disp = entry['Mobile'] if entry['Mobile'] else "Not Provided"
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #dcdcdc; border-radius: 8px; padding: 14px; margin-bottom: 15px;">
            <b>Source / Donor:</b> {entry['Donor_Name']} | <b>Wing/Flat:</b> {entry['Bldg_No']} - {entry['Flat_No']} | <b>Amount:</b> ₹{entry['Amount']:,.2f}<br/>
            <b>Category:</b> {entry['Category']} | <b>Mode:</b> {entry['Payment_Mode']} | <b>Mobile:</b> {mob_disp}
        </div>
        """, unsafe_allow_html=True)
        
        pdf_bytes = generate_pdf_receipt(entry)
        c_down, c_wa, c_edit, c_next = st.columns([1, 1.2, 0.8, 1])
        
        with c_down:
            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=f"{receipt_no}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
        with c_wa:
            if entry['Mobile']:
                clean_mobile = "91" + str(entry['Mobile']).strip()[-10:]
                msg = (
                    f"नमस्कार {entry['Donor_Name']} जी,\n\n"
                    f"*Radhanagar Towers Cultural Committee* कडून {selected_festival} {selected_year} करिता "
                    f"आपली ₹{entry['Amount']:,.2f} ({num_to_words_inr(entry['Amount'])}) रुपयांची देणगी प्राप्त झाली आहे.\n\n"
                    f"🧾 *अधिकृत पावती तपशील:*\n"
                    f"• पावती क्र: {receipt_no}\n"
                    f"• इमारत/फ्लॅट: {entry['Bldg_No']} - {entry['Flat_No']}\n"
                    f"• देणगी पद्धत: {entry['Payment_Mode']}\n"
                    f"• देणगी प्रवर्ग: {entry['Category']}\n\n"
                    f"📥 *आपली डिजिटल पावती पाहण्यासाठी व रिअल-टाईम हिशोब तपासण्यासाठी लिंक:*\n"
                    f"{LIVE_APP_URL}\n\n"
                    f"📌 *टीप:* ही पावती संगणकीकृत असल्याने स्वाक्षरीची आवश्यकता नाही.\n\n"
                    f"🙏 आपल्या सहकार्याबद्दल मनःपूर्वक धन्यवाद!"
                )
                wa_url = f"https://wa.me/{clean_mobile}?text={urllib.parse.quote(msg)}"
                st.markdown(
                    f'<a href="{wa_url}" target="_blank">'
                    f'<button style="background-color:#25D366;color:white;padding:8px 12px;border:none;border-radius:4px;cursor:pointer;font-weight:bold;width:100%;height:38px;">'
                    f'📲 Send WhatsApp'
                    f'</button></a>', 
                    unsafe_allow_html=True
                )
            else:
                st.button("📲 WhatsApp (No Mobile Entered)", disabled=True, use_container_width=True)

        with c_edit:
            if st.button("✏️ Edit Entry", use_container_width=True):
                st.session_state["edit_record_target"] = receipt_no
                st.session_state.last_entry_state = None
                st.rerun()

        with c_next:
            if st.button("➕ Record Next Entry", type="primary", use_container_width=True):
                st.session_state.last_entry_state = None
                st.rerun()

    # 2. State: Non-Receipt / Opening Balance Recorded
    elif st.session_state.get("last_non_rec_state") is not None:
        last_non_rec = st.session_state.last_non_rec_state
        ref_no = last_non_rec["Receipt_No"]
        
        st.success(f"✅ **{last_non_rec['Category']} Recorded Successfully!**")
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #dcdcdc; border-radius: 8px; padding: 14px; margin-bottom: 15px;">
            <b>Reference ID:</b> {ref_no} | <b>Source / Description:</b> {last_non_rec['Donor_Name']}<br/>
            <b>Amount:</b> ₹{last_non_rec['Amount']:,.2f} | <b>Mode:</b> {last_non_rec['Payment_Mode']} | <b>Date:</b> {last_non_rec['Date']}<br/>
            <b>Account Note:</b> {last_non_rec['Txn_Ref']}
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("➕ Record Next Direct Income Entry", type="primary", use_container_width=True):
            st.session_state.last_non_rec_state = None
            st.rerun()

    # 3. State: Input Forms
    else:
        tab_don_entry, tab_non_rec = st.tabs(["🧾 Resident Donation (Generates Receipt)", "🏦 Opening Balance & General Income (Non-Receipt)"])
        
        # TAB 1: RESIDENT DONATION
        with tab_don_entry:
            col_form, col_qr = st.columns([1.2, 0.8])
            
            with col_form:
                donor_name = st.text_input("Donor Full Name*", placeholder="e.g. Ramesh Patil", key="inp_name")
                c_bldg, c_flat = st.columns(2)
                
                bldg_options = st.session_state.app_config["buildings"] + ["➕ Add New Building/Wing..."]
                chosen_bldg = c_bldg.selectbox("Building / Wing No.*", bldg_options, key="inp_bldg")
                bldg_no = chosen_bldg
                if chosen_bldg == "➕ Add New Building/Wing...":
                    new_bldg_input = c_bldg.text_input("Enter New Building Name")
                    if new_bldg_input:
                        bldg_no = new_bldg_input.strip()
                        if bldg_no not in st.session_state.app_config["buildings"]:
                            st.session_state.app_config["buildings"].append(bldg_no)
                            save_config()
                
                flat_no = c_flat.text_input("Flat No.*", placeholder="e.g. 402", key="inp_flat")
                
                c_mob, c_amt = st.columns(2)
                raw_mob = c_mob.text_input("Mobile Number (Optional)", placeholder="10 Digits (e.g. 9876543210)", max_chars=10, key="inp_mob")
                clean_digits = re.sub(r"\D", "", raw_mob) if raw_mob else ""
                is_valid_phone = len(clean_digits) == 10
                
                if clean_digits:
                    if is_valid_phone:
                        c_mob.markdown("<span class='valid-phone'>✅ Valid 10-Digit Mobile Number</span>", unsafe_allow_html=True)
                    else:
                        c_mob.caption(f"ℹ️ {len(clean_digits)}/10 digits entered")
                else:
                    c_mob.markdown("<span class='opt-label'>Optional</span>", unsafe_allow_html=True)

                amount = c_amt.number_input("Donation Amount (₹)*", min_value=1.0, step=100.0, value=500.0, key="inp_amt")
                st.caption(f"**Amount in Words:** *{num_to_words_inr(amount)}*")
                
                donation_cat_list = [c for c in st.session_state.app_config["income"] if not c.startswith("Opening Balance")]
                income_cat_options = donation_cat_list + ["➕ Add New Category..."]
                chosen_cat = st.selectbox("Donation Category", income_cat_options, key="inp_cat")
                category = chosen_cat
                if chosen_cat == "➕ Add New Category...":
                    new_cat_input = st.text_input("Enter New Category Name")
                    if new_cat_input:
                        category = new_cat_input.strip()
                        if category not in st.session_state.app_config["income"]:
                            st.session_state.app_config["income"].append(category)
                            save_config()
                
                c_mode, c_ref = st.columns(2)
                payment_mode = c_mode.selectbox("Payment Mode*", ["Cash", "UPI / QR Code", "Cheque", "Bank Transfer"], index=0, key="inp_mode")
                default_ref = "CASH RECEIVED" if payment_mode == "Cash" else ""
                txn_ref = c_ref.text_input("Transaction / UTR No.", value=default_ref, key="inp_ref")
                
                submitted = st.button("💾 Confirm & Generate Official Receipt", type="primary", use_container_width=True)

            with col_qr:
                st.markdown("#### 📱 Instant UPI Payment QR")
                st.caption(f"Payee: **{PAYEE_NAME}** (`{PAYEE_UPI_ID}`)")
                note = f"{selected_festival} {selected_year} - {donor_name if donor_name else 'Donation'}"
                qr_img_bytes = generate_upi_qr(PAYEE_UPI_ID, PAYEE_NAME, amount, note)
                st.image(qr_img_bytes, caption=f"Scan to pay ₹{amount:,.2f} via UPI", width=210)

            if submitted:
                if not donor_name or not bldg_no or not flat_no:
                    st.error("Please fill in mandatory fields: Donor Name, Building, and Flat Number.")
                elif raw_mob and not is_valid_phone:
                    st.error("Please enter a valid 10-digit mobile number or leave it blank.")
                else:
                    fresh_df = read_donations()
                    start_base = int(st.session_state.app_config.get("start_receipt_no", 101))
                    next_seq = start_base + len(fresh_df)
                    receipt_no = f"RTCC-{selected_year}-{next_seq}"
                    
                    new_entry = {
                        "Receipt_No": receipt_no,
                        "Year": int(selected_year),
                        "Festival": selected_festival,
                        "Donor_Name": donor_name,
                        "Bldg_No": bldg_no,
                        "Flat_No": flat_no,
                        "Mobile": clean_digits if is_valid_phone else "",
                        "Amount": float(amount),
                        "Category": category,
                        "Payment_Mode": payment_mode,
                        "Txn_Ref": txn_ref if txn_ref else ("CASH" if payment_mode == "Cash" else "N/A"),
                        "Date": str(date.today())
                    }
                    
                    append_donation(new_entry)
                    st.session_state.last_entry_state = new_entry
                    st.rerun()

        # TAB 2: OPENING BALANCE & GENERAL INCOME
        with tab_non_rec:
            st.markdown("#### 🏦 Log Opening Balance / Miscellaneous Income")
            st.caption("Use this for Opening Balances carried forward, bank interest, scrap sales, or lump-sum collections where individual receipts are not issued.")
            
            with st.container():
                col_nb1, col_nb2 = st.columns(2)
                
                income_type = col_nb1.selectbox("Income Type / Category*", [
                    "Opening Balance (Carried Forward)",
                    "Bank Savings Interest",
                    "Scrap Sale / Raddi",
                    "Sponsorship / Banner Advertisement",
                    "Other Miscellaneous Income"
                ], key="nb_cat")
                
                nb_source = col_nb2.text_input("Source / Description*", value="Previous Year Balance" if "Opening" in income_type else "", placeholder="e.g. RTCC Bank Account / Society Fund", key="nb_src")
                
                col_nb3, col_nb4 = st.columns(2)
                nb_amount = col_nb3.number_input("Amount (₹)*", min_value=1.0, step=500.0, value=5000.0, key="nb_amt")
                nb_mode = col_nb4.selectbox("Payment / Transfer Mode*", ["Bank Transfer", "Cash", "Cheque", "UPI"], index=0, key="nb_mode")
                
                nb_ref = st.text_input("Account Ref / Cheque / Bank Note", value="CARRIED FORWARD" if "Opening" in income_type else "", key="nb_ref")
                
                if st.button("💾 Record Direct Income (No Receipt Needed)", type="primary", use_container_width=True):
                    if not nb_source or nb_amount <= 0:
                        st.error("Please enter a valid Source description and Amount.")
                    else:
                        fresh_df = read_donations()
                        tag_prefix = "OPEN" if "Opening" in income_type else "MISC"
                        rec_tag = f"INC-{tag_prefix}-{selected_year}-{len(fresh_df)+1}"
                        
                        direct_entry = {
                            "Receipt_No": rec_tag,
                            "Year": int(selected_year),
                            "Festival": selected_festival,
                            "Donor_Name": nb_source,
                            "Bldg_No": "N/A",
                            "Flat_No": "N/A",
                            "Mobile": "",
                            "Amount": float(nb_amount),
                            "Category": income_type,
                            "Payment_Mode": nb_mode,
                            "Txn_Ref": nb_ref if nb_ref else "N/A",
                            "Date": str(date.today())
                        }
                        append_donation(direct_entry)
                        st.session_state.last_non_rec_state = direct_entry
                        st.rerun()

# =========================================================
# VIEW 3: SEQUENTIAL LOG EXPENDITURE (ADMIN ONLY)
# =========================================================
elif menu == "💸 Admin: Log Expenditure":
    st.subheader(f"💸 Log Expenditure — {selected_festival} {selected_year}")
    
    if st.session_state.last_expense_state is not None:
        last_exp = st.session_state.last_expense_state
        voucher_no = last_exp["Voucher_No"]
        
        st.success(f"✅ **Expense Voucher {voucher_no} Recorded Successfully!**")
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #dcdcdc; border-radius: 8px; padding: 14px; margin-bottom: 15px;">
            <b>Vendor/Payee:</b> {last_exp['Vendor_Name']} | <b>Category:</b> {last_exp['Category']} | <b>Amount:</b> ₹{last_exp['Amount']:,.2f}<br/>
            <b>Payment Mode:</b> {last_exp['Payment_Mode']} | <b>Date:</b> {last_exp['Date']}<br/>
            <b>Description:</b> {last_exp['Description']}
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("➕ Record Next Expense Entry", type="primary", use_container_width=True):
            st.session_state.last_expense_state = None
            st.rerun()

    else:
        col1, col2 = st.columns(2)
        expense_cat_options = st.session_state.app_config["expense"] + ["➕ Add New Category..."]
        chosen_exp_cat = col1.selectbox("Expense Category", expense_cat_options)
        category = chosen_exp_cat
        if chosen_exp_cat == "➕ Add New Category...":
            new_exp_cat = st.text_input("Enter New Expense Category Name")
            if new_exp_cat:
                category = new_exp_cat.strip()
                if category not in st.session_state.app_config["expense"]:
                    st.session_state.app_config["expense"].append(category)
                    save_config()
                    
        amount = col2.number_input("Expense Amount (₹)*", min_value=1.0, step=100.0)
        col3, col4 = st.columns(2)
        vendor_name = col3.text_input("Vendor / Payee Name*", placeholder="e.g. Shinde Sound & Mandap")
        payment_mode = col4.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer", "Cheque"])
        description = st.text_area("Details (Bill No, item specifications, etc.)")
        
        if st.button("💾 Record Expenditure", type="primary", use_container_width=True):
            if not vendor_name or amount <= 0:
                st.error("Please enter Vendor Name and a valid Amount.")
            else:
                fresh_exp = read_expenses()
                voucher_no = f"EXP-{selected_year}-{len(fresh_exp)+201}"
                new_exp = {
                    "Voucher_No": voucher_no,
                    "Year": int(selected_year),
                    "Festival": selected_festival,
                    "Category": category,
                    "Amount": float(amount),
                    "Vendor_Name": vendor_name,
                    "Description": description if description else "-",
                    "Payment_Mode": payment_mode,
                    "Date": str(date.today())
                }
                append_expense(new_exp)
                st.session_state.last_expense_state = new_exp
                st.rerun()

# =========================================================
# VIEW 4: ALL RECORDS, EDITABLE RECEIPT #, & SECTION 3 PDF
# =========================================================
elif menu == "📜 All Records & Reports":
    st.subheader(f"📜 Ledger Records & Audited Reports — {selected_festival} {selected_year}")
    
    st.markdown("##### 📑 Official Audited Balance Sheet Statement")
    
    with st.expander("⚙️ Optional: Add Section 3 (Others / Committee Notes to Report)", expanded=False):
        add_sec_3 = st.checkbox("Include 'SECTION 3: OTHERS' in the PDF Report", value=False)
        other_notes_input = ""
        if add_sec_3:
            other_notes_input = st.text_area(
                "Enter Committee Notes / Observations (Indent sub-bullets with 2 spaces or a tab):",
                placeholder="Other contributions:\n  - Material by Sachin\n  - Material by Sathe\n  - Material by Rahul\nAudit observations:\n  - All accounts verified",
                height=120
            )
    
    pdf_report_bytes = generate_master_financial_pdf(
        selected_festival, selected_year, filtered_donations, filtered_expenses, 
        other_notes=other_notes_input if add_sec_3 else None
    )
    
    col_pdf, col_csv1, col_csv2 = st.columns([1.3, 1, 1])
    with col_pdf:
        st.download_button(
            label="📄 Download Official PDF Report (Sections 1, 1B, 2 & 3)",
            data=pdf_report_bytes,
            file_name=f"RTCC_Financial_Report_{selected_festival}_{selected_year}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    with col_csv1:
        if not filtered_donations.empty:
            csv_don = filtered_donations.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Income Ledger (CSV)", data=csv_don, file_name=f"RTCC_Income_{selected_festival}_{selected_year}.csv", mime="text/csv", use_container_width=True)
    with col_csv2:
        if not filtered_expenses.empty:
            csv_exp = filtered_expenses.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Export Expenses Ledger (CSV)", data=csv_exp, file_name=f"RTCC_Expenses_{selected_festival}_{selected_year}.csv", mime="text/csv", use_container_width=True)
            
    st.markdown("---")
    tab1, tab2 = st.tabs(["📥 Income Ledger (Donations & Balances)", "📤 Expense Ledger (Expenditures)"])
    
    with tab1:
        if not filtered_donations.empty:
            st.dataframe(filtered_donations, use_container_width=True, hide_index=True)
            st.markdown("#### ✏️ Modify, Delete, or Re-send Receipt (Editable Ref / Receipt Numbers)")
            
            rec_list = filtered_donations["Receipt_No"].tolist()
            pre_idx = 0
            if "edit_record_target" in st.session_state and st.session_state["edit_record_target"] in rec_list:
                pre_idx = rec_list.index(st.session_state["edit_record_target"])
                
            selected_rec = st.selectbox("Select Receipt Number / Income Reference to Manage", rec_list, index=pre_idx)
            
            if selected_rec:
                row_idx = st.session_state.donations[st.session_state.donations["Receipt_No"] == selected_rec].index[0]
                rec_data = st.session_state.donations.loc[row_idx]
                
                with st.expander(f"📝 Edit & Re-send Tools for Entry #{selected_rec}", expanded=True):
                    e_rec_no = st.text_input("Receipt Number / Reference (Editable)", value=str(rec_data["Receipt_No"]))
                    e_name = st.text_input("Source / Donor Full Name", value=str(rec_data["Donor_Name"]))
                    
                    e_c1, e_c2 = st.columns(2)
                    current_bldg = str(rec_data["Bldg_No"])
                    bldg_list = st.session_state.app_config["buildings"]
                    bldg_idx = bldg_list.index(current_bldg) if current_bldg in bldg_list else 0
                    e_bldg = e_c1.selectbox("Building / Wing", bldg_list, index=bldg_idx, key="e_bldg_sel")
                    e_flat = e_c2.text_input("Flat No", value=str(rec_data["Flat_No"]))
                    
                    e_c3, e_c4 = st.columns(2)
                    curr_mob = "" if pd.isna(rec_data["Mobile"]) or str(rec_data["Mobile"]).lower() == 'nan' else str(rec_data["Mobile"])
                    e_mob = e_c3.text_input("Mobile Number (Optional)", value=curr_mob)
                    e_amt = e_c4.number_input("Amount (₹)", value=float(rec_data["Amount"]), step=100.0)
                    
                    e_c5, e_c6 = st.columns(2)
                    current_cat = str(rec_data["Category"])
                    cat_list = st.session_state.app_config["income"]
                    cat_idx = cat_list.index(current_cat) if current_cat in cat_list else 0
                    e_cat = e_c5.selectbox("Income Category", cat_list, index=cat_idx, key="e_cat_sel")
                    
                    modes = ["Cash", "UPI / QR Code", "Cheque", "Bank Transfer"]
                    mode_idx = modes.index(rec_data["Payment_Mode"]) if rec_data["Payment_Mode"] in modes else 0
                    e_mode = e_c6.selectbox("Payment Mode", modes, index=mode_idx, key="e_mode_sel")
                    e_ref = st.text_input("Transaction Ref / UTR No.", value=str(rec_data["Txn_Ref"]))
                    
                    c_save, c_del = st.columns(2)
                    if c_save.button("💾 Save Changes to Record", type="primary", use_container_width=True):
                        if e_rec_no != selected_rec and e_rec_no in st.session_state.donations["Receipt_No"].tolist():
                            st.error(f"Reference/Receipt Number {e_rec_no} already exists! Please pick a unique number.")
                        else:
                            st.session_state.donations.at[row_idx, "Receipt_No"] = e_rec_no
                            st.session_state.donations.at[row_idx, "Donor_Name"] = e_name
                            st.session_state.donations.at[row_idx, "Bldg_No"] = e_bldg
                            st.session_state.donations.at[row_idx, "Flat_No"] = e_flat
                            st.session_state.donations.at[row_idx, "Mobile"] = e_mob
                            st.session_state.donations.at[row_idx, "Amount"] = float(e_amt)
                            st.session_state.donations.at[row_idx, "Category"] = e_cat
                            st.session_state.donations.at[row_idx, "Payment_Mode"] = e_mode
                            st.session_state.donations.at[row_idx, "Txn_Ref"] = e_ref
                            st.session_state.donations.to_csv(DONATIONS_CSV, index=False)
                            st.success("✅ Record updated!")
                            st.rerun()
                        
                    if c_del.button("🗑️ Delete Entry", use_container_width=True):
                        st.session_state.donations = st.session_state.donations.drop(row_idx).reset_index(drop=True)
                        st.session_state.donations.to_csv(DONATIONS_CSV, index=False)
                        st.warning(f"Entry {selected_rec} deleted.")
                        st.rerun()
                    
                    if not str(e_rec_no).startswith("INC-OPEN"):
                        st.markdown("---")
                        updated_dict = {
                            "Receipt_No": e_rec_no, "Year": int(rec_data["Year"]), "Festival": str(rec_data["Festival"]),
                            "Donor_Name": e_name, "Bldg_No": e_bldg, "Flat_No": e_flat, "Mobile": e_mob,
                            "Amount": float(e_amt), "Category": e_cat, "Payment_Mode": e_mode, "Txn_Ref": e_ref, "Date": str(rec_data["Date"])
                        }
                        updated_pdf = generate_pdf_receipt(updated_dict)
                        
                        c_p_down, c_p_wa = st.columns(2)
                        with c_p_down:
                            st.download_button("📄 Download Updated PDF", data=updated_pdf, file_name=f"{e_rec_no}.pdf", mime="application/pdf", use_container_width=True)
                        
                        with c_p_wa:
                            if e_mob:
                                clean_mob = "91" + str(e_mob).strip()[-10:]
                                re_msg = (
                                    f"नमस्कार {e_name} जी,\n\n"
                                    f"*Radhanagar Towers Cultural Committee* कडून {rec_data['Festival']} {rec_data['Year']} करिता "
                                    f"आपली अद्ययावत पावती (Updated Receipt) प्राप्त झाली आहे:\n\n"
                                    f"🧾 *पावती क्र:* {e_rec_no}\n"
                                    f"🏢 *इमारत/फ्लॅट:* {e_bldg} - {e_flat}\n"
                                    f"💰 *रक्कम:* ₹{float(e_amt):,.2f}\n"
                                    f"💳 *पद्धत:* {e_mode}\n\n"
                                    f"📥 *पावती पाहण्यासाठी व बॅलन्स शीट लिंक:*\n{LIVE_APP_URL}\n\n"
                                    f"🙏 धन्यवाद!"
                                )
                                re_wa_url = f"https://wa.me/{clean_mob}?text={urllib.parse.quote(re_msg)}"
                                st.markdown(f'<a href="{re_wa_url}" target="_blank"><button style="background-color:#25D366;color:white;padding:8px 12px;border:none;border-radius:4px;cursor:pointer;font-weight:bold;width:100%;height:38px;">📲 Send Updated WhatsApp</button></a>', unsafe_allow_html=True)
        else:
            st.info("No income entries recorded yet.")

    with tab2:
        if not filtered_expenses.empty:
            st.dataframe(filtered_expenses, use_container_width=True, hide_index=True)
            st.markdown("#### ✏️ Modify or Delete Expense Entry")
            selected_vouch = st.selectbox("Select Voucher Number", filtered_expenses["Voucher_No"].tolist())
            
            if selected_vouch:
                exp_row_idx = st.session_state.expenses[st.session_state.expenses["Voucher_No"] == selected_vouch].index[0]
                exp_data = st.session_state.expenses.loc[exp_row_idx]
                
                with st.expander(f"Modify Voucher #{selected_vouch}", expanded=True):
                    e_vouch_no = st.text_input("Voucher Number (Editable)", value=str(exp_data["Voucher_No"]))
                    exp_vendor = st.text_input("Vendor Name", value=str(exp_data["Vendor_Name"]))
                    exp_amt = st.number_input("Amount (₹)", value=float(exp_data["Amount"]), step=100.0)
                    exp_curr_cat = str(exp_data["Category"])
                    exp_cat_list = st.session_state.app_config["expense"]
                    exp_cat_idx = exp_cat_list.index(exp_curr_cat) if exp_curr_cat in exp_cat_list else 0
                    e_exp_cat = st.selectbox("Expense Category", exp_cat_list, index=exp_cat_idx, key="e_exp_sel")
                    e_exp_modes = ["Cash", "UPI", "Bank Transfer", "Cheque"]
                    e_exp_mode_idx = e_exp_modes.index(exp_data["Payment_Mode"]) if exp_data["Payment_Mode"] in e_exp_modes else 0
                    e_exp_mode = st.selectbox("Payment Mode", e_exp_modes, index=e_exp_mode_idx, key="e_exp_m_sel")
                    e_exp_desc = st.text_area("Description", value=str(exp_data["Description"]))
                    
                    c_exp_up, c_exp_del = st.columns(2)
                    if c_exp_up.button("💾 Save Updated Voucher", type="primary", use_container_width=True):
                        if e_vouch_no != selected_vouch and e_vouch_no in st.session_state.expenses["Voucher_No"].tolist():
                            st.error(f"Voucher Number {e_vouch_no} already exists! Please choose a unique voucher number.")
                        else:
                            st.session_state.expenses.at[exp_row_idx, "Voucher_No"] = e_vouch_no
                            st.session_state.expenses.at[exp_row_idx, "Vendor_Name"] = exp_vendor
                            st.session_state.expenses.at[exp_row_idx, "Amount"] = float(exp_amt)
                            st.session_state.expenses.at[exp_row_idx, "Category"] = e_exp_cat
                            st.session_state.expenses.at[exp_row_idx, "Payment_Mode"] = e_exp_mode
                            st.session_state.expenses.at[exp_row_idx, "Description"] = e_exp_desc
                            st.session_state.expenses.to_csv(EXPENSES_CSV, index=False)
                            st.success("Expense updated!")
                            st.rerun()
                        
                    if c_exp_del.button("🗑️ Delete Voucher", use_container_width=True):
                        st.session_state.expenses = st.session_state.expenses.drop(exp_row_idx).reset_index(drop=True)
                        st.session_state.expenses.to_csv(EXPENSES_CSV, index=False)
                        st.warning(f"Voucher {selected_vouch} deleted.")
                        st.rerun()
        else:
            st.info("No expense entries logged yet.")

# =========================================================
# VIEW 5: MASTER SETTINGS (FULL SYSTEM CONFIG BACKUP & RESTORE)
# =========================================================
elif menu == "⚙️ Master Settings (Backup & Series)":
    st.subheader("⚙️ Master System Setup & Data Backups")
    
    # 1. RECEIPT SERIES & NUMBERING SETUP
    st.markdown("### 🔢 Receipt Numbering Series Setup")
    c_s1, c_s2 = st.columns([1.5, 2])
    with c_s1:
        curr_start = int(st.session_state.app_config.get("start_receipt_no", 101))
        new_start = st.number_input("Starting Receipt Sequence Number", min_value=1, step=1, value=curr_start)
        if st.button("💾 Save Starting Number", use_container_width=True):
            st.session_state.app_config["start_receipt_no"] = int(new_start)
            save_config()
            st.success(f"Receipt starting number set to: RTCC-{selected_year}-{new_start}")
            st.rerun()
            
    st.markdown("---")
    
    # 2. MASTER CONFIGURATIONS BACKUP & RESTORE
    st.markdown("### ⚙️ Master System Configurations Backup & Restore")
    st.caption("Export or import all custom buildings, wings, income categories, expense categories, and sequence numbers in one JSON file.")
    
    c_cfg_d, c_cfg_u = st.columns(2)
    with c_cfg_d:
        config_json_str = json.dumps(st.session_state.app_config, indent=4)
        st.download_button(
            "💾 Download Master Configurations (JSON)", 
            data=config_json_str, 
            file_name="rtcc_master_config_backup.json", 
            mime="application/json", 
            use_container_width=True
        )
    with c_cfg_u:
        up_cfg_file = st.file_uploader("Restore Master Configurations (Upload JSON)", type=["json"], key="up_cfg")
        if up_cfg_file is not None:
            if st.button("⚡ Overwrite & Restore Master Configs", type="primary", use_container_width=True):
                try:
                    uploaded_cfg = json.load(up_cfg_file)
                    st.session_state.app_config = uploaded_cfg
                    save_config()
                    st.success("✅ Master configurations (Buildings, Categories, Series) restored successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to read JSON: {e}")

    st.markdown("---")
    
    # 3. FULL DATABASE BACKUP & RESTORE
    st.markdown("### 🔄 Complete Database Backup & Version Restore")
    st.caption("Download full financial CSV ledgers or upload prior CSV backups.")
    
    col_bak_d, col_bak_u = st.columns(2)
    
    with col_bak_d:
        st.markdown("#### 📥 Database Backup Download")
        all_donations = read_donations()
        all_expenses = read_expenses()
        
        csv_all_don = all_donations.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Download Master Donations Backup (CSV)", data=csv_all_don, file_name="master_donations_ledger_backup.csv", mime="text/csv", use_container_width=True)
        
        csv_all_exp = all_expenses.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Download Master Expenses Backup (CSV)", data=csv_all_exp, file_name="master_expenses_ledger_backup.csv", mime="text/csv", use_container_width=True)
        
    with col_bak_u:
        st.markdown("#### 📤 Restore Database from CSV")
        up_don_file = st.file_uploader("Restore Donations Ledger (Upload CSV)", type=["csv"], key="up_don")
        if up_don_file is not None:
            if st.button("⚡ Overwrite & Restore Donations Database", type="primary", use_container_width=True):
                restored_don = pd.read_csv(up_don_file, dtype={"Receipt_No": str, "Mobile": str, "Flat_No": str, "Bldg_No": str})
                restored_don.to_csv(DONATIONS_CSV, index=False)
                st.session_state.donations = restored_don
                st.success("✅ Donations Ledger restored successfully!")
                st.rerun()
                
        up_exp_file = st.file_uploader("Restore Expenses Ledger (Upload CSV)", type=["csv"], key="up_exp")
        if up_exp_file is not None:
            if st.button("⚡ Overwrite & Restore Expenses Database", type="primary", use_container_width=True):
                restored_exp = pd.read_csv(up_exp_file, dtype={"Voucher_No": str})
                restored_exp.to_csv(EXPENSES_CSV, index=False)
                st.session_state.expenses = restored_exp
                st.success("✅ Expenses Ledger restored successfully!")
                st.rerun()

    st.markdown("---")
    
    # 4. BUILDINGS & CATEGORIES VISUAL MANAGER
    st.markdown("### 🏢 Buildings & Financial Categories Setup")
    col_bldg_m, col_inc_m, col_exp_m = st.columns(3)
    
    with col_bldg_m:
        st.markdown("##### 🏢 Buildings / Wings")
        c_b_txt, c_b_btn = st.columns([2.5, 1])
        add_bldg = c_b_txt.text_input("New Building", placeholder="e.g. Tower D", label_visibility="collapsed")
        if c_b_btn.button("➕ Add", key="add_bldg_btn", use_container_width=True):
            if add_bldg and add_bldg.strip() not in st.session_state.app_config["buildings"]:
                st.session_state.app_config["buildings"].append(add_bldg.strip())
                save_config()
                st.success(f"Added '{add_bldg.strip()}'")
                st.rerun()
                
        for idx, bldg_item in enumerate(st.session_state.app_config["buildings"]):
            cb_label, cb_del = st.columns([3, 1])
            cb_label.markdown(f"• **{bldg_item}**")
            if cb_del.button("🗑️", key=f"del_bldg_{idx}", help=f"Delete {bldg_item}"):
                st.session_state.app_config["buildings"].remove(bldg_item)
                save_config()
                st.rerun()

    with col_inc_m:
        st.markdown("##### 📥 Income Categories")
        c_in_txt, c_in_btn = st.columns([2.5, 1])
        add_inc = c_in_txt.text_input("New Income Cat", placeholder="e.g. Aarti Sponsor", label_visibility="collapsed")
        if c_in_btn.button("➕ Add", key="add_inc_btn", use_container_width=True):
            if add_inc and add_inc.strip() not in st.session_state.app_config["income"]:
                st.session_state.app_config["income"].append(add_inc.strip())
                save_config()
                st.success(f"Added '{add_inc.strip()}'")
                st.rerun()
                
        for idx, cat in enumerate(st.session_state.app_config["income"]):
            c_label, c_action = st.columns([3, 1])
            c_label.markdown(f"• **{cat}**")
            if c_action.button("🗑️", key=f"del_inc_{idx}", help=f"Delete {cat}"):
                st.session_state.app_config["income"].remove(cat)
                save_config()
                st.rerun()

    with col_exp_m:
        st.markdown("##### 📤 Expense Categories")
        c_ex_txt, c_ex_btn = st.columns([2.5, 1])
        add_exp = c_ex_txt.text_input("New Expense Cat", placeholder="e.g. Flower Garland", label_visibility="collapsed")
        if c_ex_btn.button("➕ Add", key="add_exp_btn", use_container_width=True):
            if add_exp and add_exp.strip() not in st.session_state.app_config["expense"]:
                st.session_state.app_config["expense"].append(add_exp.strip())
                save_config()
                st.success(f"Added '{add_exp.strip()}'")
                st.rerun()
                
        for idx, cat in enumerate(st.session_state.app_config["expense"]):
            c_label, c_action = st.columns([3, 1])
            c_label.markdown(f"• **{cat}**")
            if c_action.button("🗑️", key=f"del_exp_{idx}", help=f"Delete {cat}"):
                st.session_state.app_config["expense"].remove(cat)
                save_config()
                st.rerun()