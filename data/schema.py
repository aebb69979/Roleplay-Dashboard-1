"""
Column layout for the Roleplay Responses Google Sheet and the Mapping
roster workbook.

The Form's Thai headers are long and have already drifted between
questions (inconsistent trailing spaces, one missing its closing
parenthesis on "2.2 ... Pain Point (10 คะแนน"). Matching on header text
is brittle, so responses are ingested by COLUMN POSITION and renamed to
these stable internal names immediately — nothing downstream should ever
reference a raw Thai header again.
"""

# Position-ordered columns of 'Form Responses 1' in
# "แบบประเมินการทำ Roleplay (Responses)" (columns A:N).
RESPONSE_COLUMNS = [
    "timestamp",
    "evaluator_role",       # ผู้ทำการประเมิน
    "evaluee_position",     # ตำแหน่งผู้ถูกประเมิน
    "sale_code_raw",        # Sale Code  ผู้ถูกประเมิน — free text, dirty
    "score_1_1",            # 1.1 เปิดการขายได้เป็นธรรมชาติ (10)
    "score_1_2",            # 1.2 แนะนำตัวชัดเจน บอกสังกัด บทบาท (10)
    "score_2_1",            # 2.1 สอบถามความต้องการ พฤติกรรมการใช้งาน (10)
    "score_2_2",            # 2.2 วิเคราะห์ Pain Point (10)
    "score_3",              # 3. นำเสนอ Solution / Package (10)
    "score_4_1",            # 4.1 ตอบข้อโต้แย้ง (10)
    "score_4_2",            # 4.2 ขอข้อมูลลูกค้า / นัดติดตั้ง (10)
    "score_5_1",            # 5.1 ชี้แจงการชำระบิล (10)
    "score_5_2",            # 5.2 ช่องทางติดต่อกรณีพบปัญหา (10)
    "score_6",               # 6. การสื่อสารและบุคลิกภาพ (10)
]

SCORE_COLS = [c for c in RESPONSE_COLUMNS if c.startswith("score_")]
MAX_RAW_SCORE = len(SCORE_COLS) * 5   # 10 items x 1-5 each = 50
PASS_THRESHOLD_PCT = 80               # per the form's own stated criterion

# Columns kept from the mapping workbook's 'Data' sheet (org roster).
MAPPING_KEEP_COLUMNS = [
    "Channel",
    "REGION_(New)",
    "PROVINCE_(64)",
    "LOWER_Sale_Code2",
    "LOWER_FULL_Name_TH",
    "LOWER_DMS_Type2",
    "LOWER_Status",
]

# Roster rows where LOWER_Sale_Code2 isn't a real code — an onboarding
# status flag instead ("0" = no code yet, the Thai strings mean "waiting
# for phone number" / "waiting for Thai ID"). Never join on these.
ROSTER_PLACEHOLDER_CODES = {"0", "* รอเบอร์โทร", "* รอ Thai ID"}

# Short labels for the "All Responses" table - mirrors the form's own
# question numbering rather than the long Thai sentence per column.
SCORE_COL_LABELS = {
    "score_1_1": "1.1",
    "score_1_2": "1.2",
    "score_2_1": "2.1",
    "score_2_2": "2.2",
    "score_3": "3",
    "score_4_1": "4.1",
    "score_4_2": "4.2",
    "score_5_1": "5.1",
    "score_5_2": "5.2",
    "score_6": "6",
}

# Column order + display names for the "All Responses" table, laid out to
# mirror 'Form Responses 1' in the old analysis workbook (Timestamp,
# evaluator, position, Sale Code, name, Channel, Region, Province, the 10
# per-question scores, then the totals).
IDENTITY_COLUMNS = [
    "timestamp",
    "evaluator_role",
    "evaluee_position",
    "sale_code_display",
    "LOWER_FULL_Name_TH",
    "Channel",
    "REGION_(New)",
    "PROVINCE_(64)",
]

RESPONSE_TABLE_COLUMNS = [
    *IDENTITY_COLUMNS,
    *SCORE_COLS,
    "score_raw",
    "score_pct",
    "passed",
]

# Thai labels matching the original form field names - shared by the
# "All Responses" column headers and its filter widgets, so they stay in
# sync in one place.
EVALUATOR_LABEL_TH = "ผู้ทำการประเมิน"
POSITION_LABEL_TH = "ตำแหน่งผู้ถูกประเมิน"
SALE_CODE_LABEL_TH = "Sale code ผู้ถูกประเมิน"
NAME_LABEL_TH = "ชื่อ-สกุล"

DISPLAY_LABELS = {
    "timestamp": "Timestamp",
    "evaluator_role": EVALUATOR_LABEL_TH,
    "evaluee_position": POSITION_LABEL_TH,
    "sale_code_display": SALE_CODE_LABEL_TH,
    "LOWER_FULL_Name_TH": NAME_LABEL_TH,
    "Channel": "Channel",
    "REGION_(New)": "Region",
    "PROVINCE_(64)": "Province",
    "score_raw": "Score (/50)",
    "score_pct": "Score (%)",
    "passed": "Pass",
    **SCORE_COL_LABELS,
}

# Original Thai question text per criterion, for the "All Responses" page
# legend - so "1.1", "4.2" etc. are never just bare codes to the viewer.
SCORE_CRITERIA_TH = {
    "1.1": "เปิดการขายได้เป็นธรรมชาติ สร้างความสนใจลูกค้า (10 คะแนน)",
    "1.2": "แนะนำตัวชัดเจน บอกสังกัด บทบาท เหตุผลที่เข้าพบ (10 คะแนน)",
    "2.1": "มีการสอบถามความต้องการ พฤติกรรมการใช้งาน (10 คะแนน)",
    "2.2": "การสอบถามความต้องการ การวิเคราะห์ Pain Point (10 คะแนน)",
    "3": "เสนอ Package/บริการ ตรงกับความต้องการลูกค้า (10 คะแนน)",
    "4.1": "สามารถตอบคำถาม หรือข้อกังวลของลูกค้าได้ (10 คะแนน)",
    "4.2": "มีการขอข้อมูลลูกค้า และขอนัดติดตั้งอย่างชัดเจน (10 คะแนน)",
    "5.1": "มีการชี้แจงรายละเอียด หรือการชำระค่าบริการ และช่องทางการติดต่อกรณีที่ลูกค้าพบปัญหา (10 คะแนน)",
    "5.2": "ช่องทางการติดต่อกรณีที่ลูกค้าพบปัญหา (10 คะแนน)",
    "6": "การสื่อสารและบุคลิกภาพ น้ำเสียง มั่นใจ บุคลิกดี สื่อสารเข้าใจง่าย (10 คะแนน)",
}
