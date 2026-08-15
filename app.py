import streamlit as st
import pandas as pd
from datetime import date
import io
import os
import json
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

# --- INJECT MODERN STYLING ---
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
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
PAYEE_UPI_ID = "harshitmasrani123@okaxis"
PAYEE_NAME = "Harshit Masrani"

DONATIONS_CSV = "donations_ledger.csv"
EXPENSES_CSV = "expenses_ledger.csv"
CATEGORIES_FILE = "categories.json"

DEFAULT_INCOME_CATS = [
    "General Vargani", "Aarti Sponsorship", "Prasad / Sweets", 
    "Mahaprasad", "Maha Aarti", "Flower Decoration"
]

DEFAULT_EXPENSE_CATS = [
    "Mandap & Stage Setup", "Sound System / DJ", "Lighting & Electrical", 
    "Idol / Murti & Pooja Samagri", "Mahaprasad & Catering", 
    "Security & Permissions", "Visarjan Arrangements", "Prize & Cultural Events", "Miscellaneous"
]

# --- NUMBER TO WORDS CONVERTER (INDIAN NUMBERING SYSTEM) ---
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
def load_categories():
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"income": DEFAULT_INCOME_CATS, "expense": DEFAULT_EXPENSE_CATS}

def save_categories():
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(st.session_state.categories, f, indent=4)

if "categories" not in st.session_state:
    st.session_state.categories = load_categories()

def load_data():
    if os.path.exists(DONATIONS_CSV):
        st.session_state.donations = pd.read_csv(DONATIONS_CSV)
    else:
        st.session_state.donations = pd.DataFrame(columns=[
            "Receipt_No", "Year", "Festival", "Donor_Name", "Bldg_No", "Flat_No", 
            "Mobile", "Amount", "Category", "Payment_Mode", "Txn_Ref", "Date"
        ])
        
    if os.path.exists(EXPENSES_CSV):
        st.session_state.expenses = pd.read_csv(EXPENSES_CSV)
    else:
        st.session_state.expenses = pd.DataFrame(columns=[
            "Voucher_No", "Year", "Festival", "Category", "Amount", 
            "Vendor_Name", "Description", "Payment_Mode", "Date"
        ])

if "donations" not in st.session_state or "expenses" not in st.session_state:
    load_data()

def save_donations():
    st.session_state.donations.to_csv(DONATIONS_CSV, index=False)

def save_expenses():
    st.session_state.expenses.to_csv(EXPENSES_CSV, index=False)

# --- HELPER: UPI QR CODE ---
def generate_upi_qr(upi_id, payee_name, amount, note):
    upi_payload = {
        "pa": upi_id,
        "pn": payee_name,
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tn": note
    }
    upi_url = f"upi://pay?{urllib.parse.urlencode(upi_payload)}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#800000", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# --- HELPER: ENHANCED PDF RECEIPT ---
def generate_pdf_receipt(receipt_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, 
        rightMargin=36, leftMargin=36, topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    
    elements = []
    
    title_style = ParagraphStyle('HeaderTitle', fontName='Helvetica-Bold', fontSize=17, alignment=1, textColor=colors.HexColor('#800000'), spaceAfter=3)
    sub_title_style = ParagraphStyle('HeaderSub', fontName='Helvetica', fontSize=10, alignment=1, textColor=colors.HexColor('#444444'), spaceAfter=2)
    fest_style = ParagraphStyle('HeaderFest', fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.HexColor('#B8860B'), spaceAfter=10)
    label_style = ParagraphStyle('LabelStyle', fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.HexColor('#333333'))
    val_style = ParagraphStyle('ValStyle', fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor('#111111'))
    amount_style = ParagraphStyle('AmtStyle', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#800000'))
    words_style = ParagraphStyle('WordsStyle', fontName='Helvetica-Oblique', fontSize=9, textColor=colors.HexColor('#222222'))
    disclaimer_style = ParagraphStyle('Discl', fontName='Helvetica', fontSize=8, alignment=1, textColor=colors.HexColor('#666666'), leading=11)
    
    elements.append(Paragraph("RADHANAGAR TOWERS CULTURAL COMMITTEE", title_style))
    elements.append(Paragraph("Kalyan West, Maharashtra", sub_title_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#B8860B'), spaceAfter=8))
    elements.append(Paragraph(f"OFFICIAL DONATION RECEIPT — {str(receipt_data['Festival']).upper()} {receipt_data['Year']}", fest_style))
    
    bldg_flat = f"Wing: {receipt_data.get('Bldg_No', 'N/A')} | Flat: {receipt_data.get('Flat_No', 'N/A')}"
    amt_val = float(receipt_data['Amount'])
    amt_in_words = num_to_words_inr(amt_val)
    
    table_data = [
        [Paragraph("<b>Receipt No:</b>", label_style), Paragraph(str(receipt_data["Receipt_No"]), val_style), 
         Paragraph("<b>Date:</b>", label_style), Paragraph(str(receipt_data["Date"]), val_style)],
        
        [Paragraph("<b>Donor Name:</b>", label_style), Paragraph(str(receipt_data["Donor_Name"]), val_style), 
         Paragraph("<b>Premises:</b>", label_style), Paragraph(bldg_flat, val_style)],
        
        [Paragraph("<b>Mobile No:</b>", label_style), Paragraph(str(receipt_data["Mobile"]), val_style), 
         Paragraph("<b>Payment Mode:</b>", label_style), Paragraph(str(receipt_data["Payment_Mode"]), val_style)],
        
        [Paragraph("<b>Category:</b>", label_style), Paragraph(str(receipt_data["Category"]), val_style), 
         Paragraph("<b>Txn Ref / UTR:</b>", label_style), Paragraph(str(receipt_data["Txn_Ref"]), val_style)],
        
        [Paragraph("<b>Amount Paid:</b>", label_style), 
         Paragraph(f"<b>Rs. {amt_val:,.2f}</b>", amount_style), 
         "", ""],
         
        [Paragraph("<b>Amount in Words:</b>", label_style), 
         Paragraph(f"<b>{amt_in_words}</b>", words_style), 
         "", ""]
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
        "All collections and event expenditures can be viewed transparently in real-time on the RTCC portal."
    )
    disc_data = [[Paragraph(disclaimer_text, disclaimer_style)]]
    disc_table = Table(disc_data, colWidths=[540])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F5F5F5')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(disc_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- SIDEBAR PORTAL ---
st.sidebar.markdown("""
<div style="text-align:center; margin-bottom:15px;">
    <h2 style="color:#800000; margin:0;">🚩 RTCC Portal</h2>
    <small style="color:#666;">Radhanagar Towers</small>
</div>
""", unsafe_allow_html=True)

selected_year = st.sidebar.selectbox("Select Festival Year", [2027, 2026, 2025, 2024], index=1)
selected_festival = st.sidebar.selectbox("Select Festival", ["Ganeshotsav", "Navratri Utsav"], index=0)

st.sidebar.markdown("---")
menu = st.sidebar.radio("Navigation Menu", [
    "📊 Real-time Balance Sheet", 
    "✍️ Admin: Donation Entry & QR", 
    "💸 Admin: Log Expenditure",
    "📜 All Records & Manage Entries",
    "⚙️ Manage Categories"
])

# Banner
st.markdown(f"""
<div class="main-header">
    <h1>🏛️ Radhanagar Towers Cultural Committee</h1>
    <p>Financial Management & Transparency Portal • <b>{selected_festival} {selected_year}</b></p>
</div>
""", unsafe_allow_html=True)

filtered_donations = st.session_state.donations[
    (st.session_state.donations["Year"] == int(selected_year)) & 
    (st.session_state.donations["Festival"] == selected_festival)
]
filtered_expenses = st.session_state.expenses[
    (st.session_state.expenses["Year"] == int(selected_year)) & 
    (st.session_state.expenses["Festival"] == selected_festival)
]

# =========================================================
# VIEW 1: REAL-TIME BALANCE SHEET DASHBOARD
# =========================================================
if menu == "📊 Real-time Balance Sheet":
    total_income = filtered_donations["Amount"].astype(float).sum() if not filtered_donations.empty else 0.0
    total_expense = filtered_expenses["Amount"].astype(float).sum() if not filtered_expenses.empty else 0.0
    net_balance = total_income - total_expense
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e7e34 0%, #28a745 100%); padding: 18px 20px; border-radius: 12px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
            <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.9;">📥 Total Collections (Income)</div>
            <div style="font-size: 26px; font-weight: 700; margin-top: 6px;">₹ {total_income:,.2f}</div>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.85;">Total Donors: {len(filtered_donations)}</div>
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
    
    col_inc, col_exp = st.columns(2)
    
    with col_inc:
        st.markdown("""
        <div style="border-bottom: 2px solid #28a745; padding-bottom: 6px; margin-bottom: 12px;">
            <h4 style="color: #1e7e34; margin: 0;">📥 Income & Donations</h4>
        </div>
        """, unsafe_allow_html=True)
        
        if not filtered_donations.empty:
            tab_inc_sum, tab_inc_det = st.tabs(["📊 Category Summary", "🔎 All Donors Detail"])
            
            with tab_inc_sum:
                inc_cat = filtered_donations.groupby("Category").agg(
                    Total_Amount=("Amount", lambda x: float(x.sum())),
                    Donor_Count=("Amount", "count")
                ).reset_index()
                
                st.dataframe(
                    inc_cat.rename(columns={
                        "Category": "Donation Category",
                        "Total_Amount": "Amount (₹)",
                        "Donor_Count": "Donors"
                    }).style.format({"Amount (₹)": "₹ {:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
                
            with tab_inc_det:
                selected_cat_filter = st.selectbox(
                    "Filter by Category:", 
                    ["All Categories"] + sorted(filtered_donations["Category"].unique().tolist()),
                    key="filter_inc_dropdown"
                )
                
                donor_view = filtered_donations if selected_cat_filter == "All Categories" else filtered_donations[filtered_donations["Category"] == selected_cat_filter]
                
                formatted_donors = donor_view[["Receipt_No", "Donor_Name", "Bldg_No", "Flat_No", "Category", "Amount", "Payment_Mode"]].copy()
                st.dataframe(
                    formatted_donors.rename(columns={
                        "Receipt_No": "Receipt",
                        "Donor_Name": "Donor Name",
                        "Bldg_No": "Bldg",
                        "Flat_No": "Flat",
                        "Payment_Mode": "Mode",
                        "Amount": "Amount (₹)"
                    }).style.format({"Amount (₹)": "₹ {:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No donation records found for this period.")

    with col_exp:
        st.markdown("""
        <div style="border-bottom: 2px solid #dc3545; padding-bottom: 6px; margin-bottom: 12px;">
            <h4 style="color: #bd2130; margin: 0;">📤 Operational Expenditures</h4>
        </div>
        """, unsafe_allow_html=True)
        
        if not filtered_expenses.empty:
            tab_exp_sum, tab_exp_det = st.tabs(["📊 Category Summary", "🔎 All Expense Details"])
            
            with tab_exp_sum:
                exp_cat = filtered_expenses.groupby("Category").agg(
                    Total_Spent=("Amount", lambda x: float(x.sum())),
                    Bill_Count=("Amount", "count")
                ).reset_index()
                
                st.dataframe(
                    exp_cat.rename(columns={
                        "Category": "Expense Category",
                        "Total_Spent": "Amount (₹)",
                        "Bill_Count": "Vouchers"
                    }).style.format({"Amount (₹)": "₹ {:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
                
            with tab_exp_det:
                selected_exp_filter = st.selectbox(
                    "Filter by Category:", 
                    ["All Categories"] + sorted(filtered_expenses["Category"].unique().tolist()),
                    key="filter_exp_dropdown"
                )
                
                exp_view = filtered_expenses if selected_exp_filter == "All Categories" else filtered_expenses[filtered_expenses["Category"] == selected_exp_filter]
                
                formatted_exp = exp_view[["Voucher_No", "Vendor_Name", "Category", "Amount", "Payment_Mode", "Description"]].copy()
                st.dataframe(
                    formatted_exp.rename(columns={
                        "Voucher_No": "Voucher",
                        "Vendor_Name": "Vendor",
                        "Payment_Mode": "Mode",
                        "Amount": "Amount (₹)"
                    }).style.format({"Amount (₹)": "₹ {:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No expenditure records found for this period.")

# =========================================================
# VIEW 2: DONATION ENTRY WITH QR CODE & WHATSAPP
# =========================================================
elif menu == "✍️ Admin: Donation Entry & QR":
    st.subheader(f"✍️ New Donation Entry — {selected_festival} {selected_year}")
    
    col_form, col_qr = st.columns([1.2, 0.8])
    
    with col_form:
        donor_name = st.text_input("Donor Full Name*", placeholder="e.g. Ramesh Patil")
        c_bldg, c_flat = st.columns(2)
        bldg_no = c_bldg.text_input("Building / Wing No.*", placeholder="e.g. Tower B")
        flat_no = c_flat.text_input("Flat No.*", placeholder="e.g. 402")
        
        c_mob, c_amt = st.columns(2)
        mobile = c_mob.text_input("Mobile Number (10 digits)*", placeholder="9876543210")
        amount = c_amt.number_input("Donation Amount (₹)*", min_value=1.0, step=100.0, value=500.0)
        
        st.caption(f"**Amount in Words:** *{num_to_words_inr(amount)}*")
        
        income_cat_options = st.session_state.categories["income"] + ["➕ Add New Category..."]
        chosen_cat = st.selectbox("Donation Category", income_cat_options)
        
        category = chosen_cat
        if chosen_cat == "➕ Add New Category...":
            new_cat_input = st.text_input("Enter New Category Name")
            if new_cat_input:
                category = new_cat_input.strip()
                if category not in st.session_state.categories["income"]:
                    st.session_state.categories["income"].append(category)
                    save_categories()
        
        c_mode, c_ref = st.columns(2)
        payment_mode = c_mode.selectbox("Payment Mode*", ["Cash", "UPI / QR Code", "Cheque", "Bank Transfer"], index=0)
        
        default_ref = "CASH RECEIVED" if payment_mode == "Cash" else ""
        txn_ref = c_ref.text_input("Transaction / UTR No.", value=default_ref, placeholder="Optional for Cash / Mandatory for UPI")
        
        submitted = st.button("💾 Confirm & Generate Official Receipt", type="primary", use_container_width=True)

    with col_qr:
        st.markdown("#### 📱 Instant UPI Payment QR")
        st.caption(f"Payee: **{PAYEE_NAME}** (`{PAYEE_UPI_ID}`)")
        note = f"{selected_festival} {selected_year} - {donor_name if donor_name else 'Donation'}"
        qr_img_bytes = generate_upi_qr(PAYEE_UPI_ID, PAYEE_NAME, amount, note)
        st.image(qr_img_bytes, caption=f"Scan to pay ₹{amount:,.2f} via UPI", width=210)

    if submitted:
        if not donor_name or not mobile:
            st.error("Please fill in required fields: Donor Name and Mobile Number.")
        else:
            receipt_no = f"RTCC-{selected_year}-{len(st.session_state.donations)+101}"
            new_entry = {
                "Receipt_No": receipt_no,
                "Year": int(selected_year),
                "Festival": selected_festival,
                "Donor_Name": donor_name,
                "Bldg_No": bldg_no if bldg_no else "N/A",
                "Flat_No": flat_no if flat_no else "N/A",
                "Mobile": mobile,
                "Amount": float(amount),
                "Category": category,
                "Payment_Mode": payment_mode,
                "Txn_Ref": txn_ref if txn_ref else ("CASH" if payment_mode == "Cash" else "N/A"),
                "Date": str(date.today())
            }
            st.session_state.donations = pd.concat([st.session_state.donations, pd.DataFrame([new_entry])], ignore_index=True)
            save_donations()
            st.success(f"✅ Receipt **{receipt_no}** generated successfully!")
            
            pdf_bytes = generate_pdf_receipt(new_entry)
            
            c_down, c_wa = st.columns(2)
            with c_down:
                st.download_button(
                    label="📄 Download Official PDF Receipt",
                    data=pdf_bytes,
                    file_name=f"{receipt_no}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with c_wa:
                clean_mobile = "91" + str(mobile).strip()[-10:]
                msg = (
                    f"नमस्कार {donor_name} जी,\n\n"
                    f"*Radhanagar Towers Cultural Committee* कडून {selected_festival} {selected_year} करिता "
                    f"आपली ₹{amount:,.2f} ({num_to_words_inr(amount)}) रुपयांची देणगी प्राप्त झाली आहे.\n\n"
                    f"🧾 *अधिकृत पावती तपशील:*\n"
                    f"• पावती क्र: {receipt_no}\n"
                    f"• इमारत/फ्लॅट: {bldg_no} - {flat_no}\n"
                    f"• देणगी पद्धत: {payment_mode}\n"
                    f"• देणगी प्रवर्ग: {category}\n\n"
                    f"📌 *टीप:* ही पावती संगणकीकृत असल्याने स्वाक्षरीची आवश्यकता नाही. सर्व हिशोब आपण ॲपवर रिअल-टाईम पाहू शकता.\n\n"
                    f"🙏 आपल्या सहकार्याबद्दल मनःपूर्वक धन्यवाद!"
                )
                wa_url = f"https://wa.me/{clean_mobile}?text={urllib.parse.quote(msg)}"
                st.markdown(
                    f'<a href="{wa_url}" target="_blank">'
                    f'<button style="background-color:#25D366;color:white;padding:9px 16px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;width:100%;margin-bottom:8px;">'
                    f'📲 Open WhatsApp Chat'
                    f'</button></a>', 
                    unsafe_allow_html=True
                )
                with st.expander("📋 Click to Copy Message"):
                    st.code(msg, language="text")

# =========================================================
# VIEW 3: LOG EXPENDITURE
# =========================================================
elif menu == "💸 Admin: Log Expenditure":
    st.subheader(f"💸 Log Expenditure — {selected_festival} {selected_year}")
    
    col1, col2 = st.columns(2)
    expense_cat_options = st.session_state.categories["expense"] + ["➕ Add New Category..."]
    chosen_exp_cat = col1.selectbox("Expense Category", expense_cat_options)
    
    category = chosen_exp_cat
    if chosen_exp_cat == "➕ Add New Category...":
        new_exp_cat = st.text_input("Enter New Expense Category Name")
        if new_exp_cat:
            category = new_exp_cat.strip()
            if category not in st.session_state.categories["expense"]:
                st.session_state.categories["expense"].append(category)
                save_categories()
                
    amount = col2.number_input("Expense Amount (₹)*", min_value=1.0, step=100.0)
    
    col3, col4 = st.columns(2)
    vendor_name = col3.text_input("Vendor / Payee Name*", placeholder="e.g. Shinde Sound & Mandap")
    payment_mode = col4.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer", "Cheque"])
    description = st.text_area("Details (Bill No, item specifications, etc.)")
    
    submit_exp = st.button("💾 Record Expenditure", type="primary", use_container_width=True)
    
    if submit_exp:
        if not vendor_name or amount <= 0:
            st.error("Please enter Vendor Name and a valid Amount.")
        else:
            voucher_no = f"EXP-{selected_year}-{len(st.session_state.expenses)+201}"
            new_exp = {
                "Voucher_No": voucher_no,
                "Year": int(selected_year),
                "Festival": selected_festival,
                "Category": category,
                "Amount": float(amount),
                "Vendor_Name": vendor_name,
                "Description": description,
                "Payment_Mode": payment_mode,
                "Date": str(date.today())
            }
            st.session_state.expenses = pd.concat([st.session_state.expenses, pd.DataFrame([new_exp])], ignore_index=True)
            save_expenses()
            st.success(f"✅ Expense logged under Voucher No: **{voucher_no}**")

# =========================================================
# VIEW 4: ALL RECORDS & EDIT/DELETE TOOLS
# =========================================================
elif menu == "📜 All Records & Manage Entries":
    st.subheader(f"📜 Ledger Records: {selected_festival} {selected_year}")
    tab1, tab2 = st.tabs(["📥 Income Ledger (Donations)", "📤 Expense Ledger (Expenditures)"])
    
    with tab1:
        if not filtered_donations.empty:
            st.dataframe(filtered_donations, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### ✏️ Manage Existing Donation Entry")
            selected_rec = st.selectbox("Select Receipt Number to Edit or Delete", filtered_donations["Receipt_No"].tolist())
            
            if selected_rec:
                row_idx = st.session_state.donations[st.session_state.donations["Receipt_No"] == selected_rec].index[0]
                rec_data = st.session_state.donations.loc[row_idx]
                
                with st.expander(f"Edit Receipt Details: {selected_rec}", expanded=True):
                    e_name = st.text_input("Donor Name", value=str(rec_data["Donor_Name"]))
                    e_c1, e_c2 = st.columns(2)
                    e_bldg = e_c1.text_input("Bldg / Wing", value=str(rec_data["Bldg_No"]))
                    e_flat = e_c2.text_input("Flat No", value=str(rec_data["Flat_No"]))
                    
                    e_c3, e_c4 = st.columns(2)
                    e_mob = e_c3.text_input("Mobile", value=str(rec_data["Mobile"]))
                    e_amt = e_c4.number_input("Amount (₹)", value=float(rec_data["Amount"]), step=100.0)
                    
                    current_cat = str(rec_data["Category"])
                    cat_list = st.session_state.categories["income"]
                    cat_idx = cat_list.index(current_cat) if current_cat in cat_list else 0
                    e_cat = st.selectbox("Category", cat_list, index=cat_idx)
                    
                    modes = ["Cash", "UPI / QR Code", "Cheque", "Bank Transfer"]
                    mode_idx = modes.index(rec_data["Payment_Mode"]) if rec_data["Payment_Mode"] in modes else 0
                    e_mode = st.selectbox("Payment Mode", modes, index=mode_idx)
                    e_ref = st.text_input("Txn Ref / UTR", value=str(rec_data["Txn_Ref"]))
                    
                    c_up, c_del = st.columns(2)
                    if c_up.button("💾 Update Donation Record", use_container_width=True):
                        st.session_state.donations.at[row_idx, "Donor_Name"] = e_name
                        st.session_state.donations.at[row_idx, "Bldg_No"] = e_bldg
                        st.session_state.donations.at[row_idx, "Flat_No"] = e_flat
                        st.session_state.donations.at[row_idx, "Mobile"] = e_mob
                        st.session_state.donations.at[row_idx, "Amount"] = float(e_amt)
                        st.session_state.donations.at[row_idx, "Category"] = e_cat
                        st.session_state.donations.at[row_idx, "Payment_Mode"] = e_mode
                        st.session_state.donations.at[row_idx, "Txn_Ref"] = e_ref
                        save_donations()
                        st.success("Donation record updated!")
                        st.rerun()
                        
                    if c_del.button("🗑️ Delete This Receipt", type="primary", use_container_width=True):
                        st.session_state.donations = st.session_state.donations.drop(row_idx).reset_index(drop=True)
                        save_donations()
                        st.warning(f"Donation {selected_rec} has been deleted.")
                        st.rerun()
        else:
            st.info("No donation entries recorded yet.")

    with tab2:
        if not filtered_expenses.empty:
            st.dataframe(filtered_expenses, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### ✏️ Manage Existing Expense Entry")
            selected_vouch = st.selectbox("Select Voucher Number to Edit or Delete", filtered_expenses["Voucher_No"].tolist())
            
            if selected_vouch:
                exp_row_idx = st.session_state.expenses[st.session_state.expenses["Voucher_No"] == selected_vouch].index[0]
                exp_data = st.session_state.expenses.loc[exp_row_idx]
                
                with st.expander(f"Edit Voucher Details: {selected_vouch}", expanded=True):
                    exp_vendor = st.text_input("Vendor Name", value=str(exp_data["Vendor_Name"]))
                    exp_amt = st.number_input("Amount (₹)", value=float(exp_data["Amount"]), step=100.0)
                    
                    exp_curr_cat = str(exp_data["Category"])
                    exp_cat_list = st.session_state.categories["expense"]
                    exp_cat_idx = exp_cat_list.index(exp_curr_cat) if exp_curr_cat in exp_cat_list else 0
                    e_exp_cat = st.selectbox("Expense Category", exp_cat_list, index=exp_cat_idx)
                    
                    e_exp_modes = ["Cash", "UPI", "Bank Transfer", "Cheque"]
                    e_exp_mode_idx = e_exp_modes.index(exp_data["Payment_Mode"]) if exp_data["Payment_Mode"] in e_exp_modes else 0
                    e_exp_mode = st.selectbox("Payment Mode", e_exp_modes, index=e_exp_mode_idx)
                    
                    e_exp_desc = st.text_area("Description", value=str(exp_data["Description"]))
                    
                    c_exp_up, c_exp_del = st.columns(2)
                    if c_exp_up.button("💾 Update Expense Record", use_container_width=True):
                        st.session_state.expenses.at[exp_row_idx, "Vendor_Name"] = exp_vendor
                        st.session_state.expenses.at[exp_row_idx, "Amount"] = float(exp_amt)
                        st.session_state.expenses.at[exp_row_idx, "Category"] = e_exp_cat
                        st.session_state.expenses.at[exp_row_idx, "Payment_Mode"] = e_exp_mode
                        st.session_state.expenses.at[exp_row_idx, "Description"] = e_exp_desc
                        save_expenses()
                        st.success("Expense record updated!")
                        st.rerun()
                        
                    if c_exp_del.button("🗑️ Delete This Voucher", type="primary", use_container_width=True):
                        st.session_state.expenses = st.session_state.expenses.drop(exp_row_idx).reset_index(drop=True)
                        save_expenses()
                        st.warning(f"Voucher {selected_vouch} has been deleted.")
                        st.rerun()
        else:
            st.info("No expense entries logged yet.")

# =========================================================
# VIEW 5: MANAGE CATEGORIES
# =========================================================
elif menu == "⚙️ Manage Categories":
    st.subheader("⚙️ Category Master Setup")
    st.caption("Add custom categories or remove unused ones across Income and Expenditure forms.")
    
    col_inc_c, col_exp_c = st.columns(2)
    
    with col_inc_c:
        st.markdown("### 📥 Income Categories")
        c_in_txt, c_in_btn = st.columns([2.5, 1])
        add_inc = c_in_txt.text_input("New Income Category", placeholder="e.g. Special Chanda", label_visibility="collapsed")
        if c_in_btn.button("➕ Add", key="add_inc_btn", use_container_width=True):
            if add_inc and add_inc.strip() not in st.session_state.categories["income"]:
                st.session_state.categories["income"].append(add_inc.strip())
                save_categories()
                st.success(f"Added '{add_inc.strip()}'")
                st.rerun()
                
        st.markdown("---")
        for idx, cat in enumerate(st.session_state.categories["income"]):
            c_label, c_action = st.columns([3, 1])
            c_label.markdown(f"• **{cat}**")
            if c_action.button("🗑️", key=f"del_inc_{idx}", help=f"Delete {cat}"):
                st.session_state.categories["income"].remove(cat)
                save_categories()
                st.rerun()
                
    with col_exp_c:
        st.markdown("### 📤 Expense Categories")
        c_ex_txt, c_ex_btn = st.columns([2.5, 1])
        add_exp = c_ex_txt.text_input("New Expense Category", placeholder="e.g. Flower Garland", label_visibility="collapsed")
        if c_ex_btn.button("➕ Add", key="add_exp_btn", use_container_width=True):
            if add_exp and add_exp.strip() not in st.session_state.categories["expense"]:
                st.session_state.categories["expense"].append(add_exp.strip())
                save_categories()
                st.success(f"Added '{add_exp.strip()}'")
                st.rerun()
                
        st.markdown("---")
        for idx, cat in enumerate(st.session_state.categories["expense"]):
            c_label, c_action = st.columns([3, 1])
            c_label.markdown(f"• **{cat}**")
            if c_action.button("🗑️", key=f"del_exp_{idx}", help=f"Delete {cat}"):
                st.session_state.categories["expense"].remove(cat)
                save_categories()
                st.rerun()