"""Smart Hostel Assistant + FretBox Integration for SR University.

Handles:
  1. Multi-intent classification for hostel queries:
     - HOSTEL_ELECTRICAL_ISSUE (fan, light, AC, switch, power)
     - HOSTEL_WATER_ISSUE (water shortage, tap leakage, bathroom water)
     - HOSTEL_CLEANING_ISSUE (dirty washroom, housekeeping, hygiene)
     - HOSTEL_WIFI_ISSUE (hostel Wi-Fi not working, connectivity)
     - HOSTEL_MAINTENANCE_COMPLAINT (door lock, furniture, room repair)
     - HOSTEL_MEAL_BOOKING (lunch, dinner, mess reservation)
     - HOSTEL_OUTPASS (outpass request, permission to leave, QR code)
     - HOSTEL_CONTACT_INFORMATION (warden, managers, administrative officer)
     - HOSTEL_RULES (curfew, timings, floor proctors, discipline)
     - HOSTEL_FACILITIES (triple sharing, AC/non-AC, hot water, reading rooms)
     - HOSTEL_INFORMATION (blocks BH-2/3/5, GH-1/8, dining hall location, fees)
     - UNKNOWN_HOSTEL_QUERY (vague issue -> context-aware clarification)
  2. Step-by-step FretBox complaint, meal booking, and outpass workflows.
  3. Dynamic Call-to-Action (CTA) buttons:
     - <Raise Complaint in FretBox>
     - <Book Meal in FretBox>
     - <Apply for Outpass>
     - <Open FretBox>
  4. 100% Handbook-grounded answers for rules, timings, blocks, and contacts (Handbook 2026-27 p.23-24).
"""
import os
import re
from typing import Any, Dict, Optional, Tuple

# Official FretBox access URL (configurable via environment variable)
FRETBOX_URL = os.environ.get("FRETBOX_URL", "https://app.fretbox.biz").strip() or "https://app.fretbox.biz"

# Handbook contact registry for hostels (Handbook 2026-27 p.7, p.23-24)
HOSTEL_CONTACTS = {
    "admin": {
        "title": "Administrative Officer (Hostels)",
        "name": "Mr. Ch. Vinay Kumar",
        "phone": "+91 9966001761",
        "email": "c.vinaykumarreddy@sru.edu.in",
        "cite": "Handbook 2026-27 p.24",
    },
    "boys": {
        "title": "Hostel Manager (Boys)",
        "name": "Mr. A. Surender",
        "phone": "+91 9989671719",
        "email": "a.surender@sru.edu.in",
        "cite": "Handbook 2026-27 p.7, p.24",
    },
    "girls": {
        "title": "Hostel Manager (Girls)",
        "name": "Ms. S. Shobha Rani",
        "phone": "+91 9701578799",
        "email": "s.shobharani@sru.edu.in",
        "cite": "Handbook 2026-27 p.7, p.24",
    },
    "fees": {
        "title": "Hostel Fee In-charge",
        "name": "Mr. O. Krishna",
        "phone": "+91 8523852300",
        "email": None,
        "cite": "Handbook 2026-27 p.7",
    },
}

# --- Intent Regex Patterns ---

RE_ELECTRICAL = re.compile(
    r"\b(?:fan|tube\s*light|lights?|switch(?:es)?|socket|plug|power|electricity|ac|air\s*condition(?:er)?|cooler|geyser)\b.*?\b(?:not\s+working|problem|issue|broken|repair|damaged|spark|off|down|complaint)\b|"
    r"\b(?:problem|issue|complaint)\b.*?\b(?:fan|tube\s*light|lights?|electricity|ac|socket)\b|"
    r"\b(?:no\s+power|power\s+cut|no\s+current)\b",
    re.I,
)

RE_WATER = re.compile(
    r"\b(?:water|tap|shower|flush|pipe|plumbing|wash\s*basin)\b.*?\b(?:not\s+coming|no\s+water|leaking|leakage|problem|issue|dirty|overflow|complaint|shortage)\b|"
    r"\b(?:no\s+water|water\s+problem|water\s+issue|water\s+shortage|tap\s+is\s+leaking|tap\s+leaking)\b",
    re.I,
)

RE_CLEANING = re.compile(
    r"\b(?:washroom|bathroom|toilet|restroom|room|corridor|dustbin|garbage)\b.*?\b(?:not\s+clean|dirty|smell|stinking|hygiene|cleaning|housekeeping|sweep|mop)\b|"
    r"\b(?:cleaning\s+problem|washroom\s+cleaning|bathroom\s+cleaning|dirty\s+bathroom|dirty\s+washroom)\b",
    re.I,
)

RE_WIFI = re.compile(
    r"\b(?:hostel\s+wi-?fi|hostel\s+internet|hostel\s+network|room\s+wi-?fi)\b.*?\b(?:not\s+working|slow|down|issue|problem|disconnected|connecting|speed)\b|"
    r"\b(?:wi-?fi|internet)\b.*?\b(?:hostel|room)\b.*?\b(?:not\s+working|problem|slow|down)\b",
    re.I,
)

RE_MAINTENANCE = re.compile(
    r"\b(?:door\s*lock|lock|door|window|bed|cot|mattress|cupboard|almirah|table|chair|furniture|mirror|ceiling|wall)\b.*?\b(?:damaged|broken|jammed|repair|not\s+working|issue|problem|fix|complaint)\b|"
    r"\b(?:hostel\s+maintenance|room\s+maintenance|carpenter|masonry)\b",
    re.I,
)

RE_MEAL = re.compile(
    r"\b(?:book\s+(?:my\s+)?(?:meals?|lunch|dinner|breakfast|food)|"
    r"how\s+(?:can|do)\s+i\s+book\s+(?:meals?|lunch|dinner|food)|"
    r"meal\s+booking|"
    r"mess\s+booking|"
    r"reserve\s+(?:my\s+)?(?:meals?|food)|"
    r"check\s+(?:my\s+)?meal\s+booking|"
    r"cancel\s+(?:my\s+)?(?:meal|dinner|lunch)|"
    r"mess\s+menu)\b",
    re.I,
)

RE_OUTPASS = re.compile(
    r"\b(?:outpass|gate\s*pass|"
    r"apply\s+(?:for\s+)?(?:an?\s+)?outpass|"
    r"i\s+(?:want|need)\s+(?:an?\s+)?outpass|"
    r"how\s+(?:can|do)\s+i\s+(?:get|apply\s+for|generate)\s+(?:an?\s+)?outpass|"
    r"outpass\s+(?:permission|request|approval|qr\s*code|system|rules?)|"
    r"go\s+outside\s+(?:the\s+)?hostel|"
    r"leave\s+(?:the\s+)?hostel|"
    r"permission\s+to\s+(?:leave|go\s+home|go\s+out)|"
    r"night\s+outpass|"
    r"weekend\s+outpass|"
    r"i\s+want\s+to\s+go\s+home\s+(?:today|tomorrow|this\s+weekend)?|"
    r"generate\s+(?:an?\s+)?outpass|"
    r"outpass\s+qr\s*code)\b",
    re.I,
)

RE_VAGUE_COMPLAINT = re.compile(
    r"^(?:there\s+is\s+a\s+problem\s+in\s+(?:my\s+)?hostel(?:\s+room|\s+accommodation)?|"
    r"problem\s+in\s+(?:my\s+)?hostel(?:\s+room|\s+accommodation)?|"
    r"issue\s+in\s+(?:my\s+)?hostel(?:\s+room|\s+accommodation)?|"
    r"hostel\s+problem|"
    r"hostel\s+issue|"
    r"room\s+problem|"
    r"i\s+have\s+a\s+hostel\s+(?:problem|issue|complaint)|"
    r"hostel\s+complaint)(?:\s+accommodation)?$",
    re.I,
)

RE_HOSTEL_CONTACT = re.compile(
    r"\b(?:whom\s+(?:should|can)\s+i\s+contact\s+regarding\s+hostel|"
    r"hostel\s+(?:warden|manager|authority|office|helpline)\s+(?:contact|number|details|phone)|"
    r"who\s+is\s+the\s+hostel\s+(?:warden|manager)|"
    r"contact\s+hostel\s+(?:management|warden|manager))\b",
    re.I,
)

RE_HOSTEL_AO = re.compile(
    r"\b(?:who\s+is\s+(?:the\s+)?(?:ao|administrative\s+officer)\s+(?:of|for\s+the)?\s*hostel|"
    r"hostel\s+ao\b|ao\s+of\s+(?:the\s+)?hostel|administrative\s+officer\s+(?:of\s+)?hostels?|"
    r"contact\s+(?:the\s+)?hostel\s+ao)\b",
    re.I,
)

RE_HOSTEL_RULES = re.compile(
    r"\b(?:hostel\s+rules|hostel\s+regulations|hostel\s+timings?|curfew\s+timings?|gate\s+closing\s+time|"
    r"hostel\s+discipline|hostel\s+in\s+time|in\s*time\s+for\s+hostel)\b",
    re.I,
)

RE_HOSTEL_FACILITIES = re.compile(
    r"\b(?:hostel\s+facilities|facilities\s+in\s+(?:the\s+)?hostel|"
    r"hostel\s+amenities|hostel\s+rooms?|ac\s+rooms?\s+in\s+hostel|triple\s+sharing)\b",
    re.I,
)

RE_HOSTEL_INFO = re.compile(
    r"\b(?:hostel\s+fees?|hostel\s+blocks?|bh-?2|bh-?3|bh-?5|gh-?1|gh-?8|"
    r"dining\s+hall\s+location|where\s+is\s+boys\s+hostel|where\s+is\s+girls\s+hostel)\b",
    re.I,
)


def classify_hostel_intent(question: str) -> Optional[str]:
    """Classifies a user query into one of the 12 Hostel & FretBox intents."""
    if not question:
        return None
    q = question.strip()
    q_clean = re.sub(r"\s+", " ", q).strip()

    # 1. Specific Maintenance / Complaint Intents
    if RE_ELECTRICAL.search(q):
        return "HOSTEL_ELECTRICAL_ISSUE"
    if RE_WATER.search(q):
        return "HOSTEL_WATER_ISSUE"
    if RE_CLEANING.search(q):
        return "HOSTEL_CLEANING_ISSUE"
    if RE_WIFI.search(q):
        return "HOSTEL_WIFI_ISSUE"
    if RE_MAINTENANCE.search(q):
        return "HOSTEL_MAINTENANCE_COMPLAINT"

    # 2. FretBox Service Actions (Meal Booking & Outpass)
    if RE_MEAL.search(q):
        return "HOSTEL_MEAL_BOOKING"
    if RE_OUTPASS.search(q):
        return "HOSTEL_OUTPASS"

    # 3. Unclear Hostel Complaint -> triggers clarification
    if RE_VAGUE_COMPLAINT.match(q_clean):
        return "UNKNOWN_HOSTEL_QUERY"

    # 4. Contacts & Management
    if RE_HOSTEL_AO.search(q):
        return "HOSTEL_AO_CONTACT"
    if RE_HOSTEL_CONTACT.search(q):
        return "HOSTEL_CONTACT_INFORMATION"

    # 5. Informational Handbook Queries
    if RE_HOSTEL_RULES.search(q):
        return "HOSTEL_RULES"
    if RE_HOSTEL_FACILITIES.search(q):
        return "HOSTEL_FACILITIES"
    if RE_HOSTEL_INFO.search(q):
        return "HOSTEL_INFORMATION"

    # Broad general check: mentions hostel without other specific intent
    if re.search(r"\bhostels?\b", q, re.I):
        if re.search(r"\b(rules?|timing|in\s*time|curfew)\b", q, re.I):
            return "HOSTEL_RULES"
        if re.search(r"\b(facilities|amenities|room|beds?|ac)\b", q, re.I):
            return "HOSTEL_FACILITIES"
        if re.search(r"\b(contact|phone|number|warden|manager)\b", q, re.I):
            return "HOSTEL_CONTACT_INFORMATION"
        return "HOSTEL_INFORMATION"

    return None


def handle_hostel_query(
    question: str,
    history: Optional[list] = None,
    profile: Optional[dict] = None,
) -> Optional[Dict[str, Any]]:
    """Generates an action-oriented or handbook-grounded response for hostel queries."""
    intent = classify_hostel_intent(question)
    if not intent:
        return None

    prof = profile or {}
    gender = prof.get("gender") or prof.get("hostel") or ""
    is_girls = bool(re.search(r"\bgirls?\b|gh-?\d", gender, re.I))

    manager_contact = HOSTEL_CONTACTS["girls"] if is_girls else HOSTEL_CONTACTS["boys"]
    manager_phone = manager_contact["phone"]
    manager_name = manager_contact["name"]
    manager_title = manager_contact["title"]

    # -------------------------------------------------------------
    # 1. UNKNOWN_HOSTEL_QUERY: Clarification
    # -------------------------------------------------------------
    if intent == "UNKNOWN_HOSTEL_QUERY":
        return {
            "answer": (
                "Sorry about that! Could you tell me what problem you are facing in your hostel?\n\n"
                "- **Fan or tube light problem**: Electrical appliances or power switches\n"
                "- **Water supply problem**: Bathroom taps, shower, or shortage\n"
                "- **Bathroom or cleaning problem**: Room or washroom housekeeping\n"
                "- **Wi-Fi or internet problem**: Connectivity or slow speeds\n"
                "- **Furniture or room maintenance**: Door locks, cupboards, beds, or windows\n"
                "- **Other issue**: Any general hostel concern"
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "clarify",
            "options": [
                "Fan or tube light problem",
                "Water supply problem",
                "Bathroom or cleaning problem",
                "Wi-Fi or internet problem",
                "Furniture or room maintenance",
                "Other issue",
            ],
            "clarify_facet": "hostel_issue_type",
        }

    # -------------------------------------------------------------
    # 2. ELECTRICAL ISSUE
    # -------------------------------------------------------------
    if intent == "HOSTEL_ELECTRICAL_ISSUE":
        return {
            "answer": (
                "Sorry to hear that! You can quickly resolve this by lodging a complaint through the **FretBox application** "
                "used by SR University hostel management.\n\n"
                "### Steps to register your complaint:\n"
                "1. Open the **FretBox** app.\n"
                "2. Go to the **Maintenance / Complaint** section.\n"
                "3. Select **Electrical Issues** ➔ Fan / Tube Light / Socket.\n"
                "4. Enter your **Hostel Block** and **Room Number**.\n"
                "5. Submit your complaint.\n\n"
                "If the issue is urgent or requires administrative attention, you can also contact the **Hostel Administrative Officer**:\n"
                "- **Name**: Mr. Ch. Vinay Kumar (AO, Hostels)\n"
                "- **Phone**: `+91 99660 01761`"
            ),
            "citations": ["Handbook 2026-27 p.23", "Handbook 2026-27 p.24"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Open FretBox",
                "intent": "electrical",
                "icon": "⚡",
            },
            "actions": {
                "calls": [
                    {
                        "number": "+91 99660 01761",
                        "tel": "tel:+919966001761",
                        "label": "Call Hostel AO",
                    }
                ],
            },
        }

    # -------------------------------------------------------------
    # 3. WATER ISSUE
    # -------------------------------------------------------------
    if intent == "HOSTEL_WATER_ISSUE":
        return {
            "answer": (
                "Sorry for the inconvenience regarding the water supply! SR University hostel plumbing and "
                "water maintenance requests are handled quickly through the **FretBox application**.\n\n"
                "### How to Report a Water Problem in FretBox:\n"
                "1. Open the **FretBox** application.\n"
                "2. Tap on the **Maintenance / Complaints** icon.\n"
                "3. Choose category: **Plumbing & Water Supply** (e.g., No Water, Tap Leakage, Geyser, Flush).\n"
                "4. Specify your **Hostel Block** and **Room Number**.\n"
                "5. Submit the ticket to alert the hostel maintenance supervisor.\n\n"
                "If water is completely unavailable or needs urgent escalation, you may also reach the **Hostel Administrative Officer**:\n"
                "- **Name**: Mr. Ch. Vinay Kumar (AO, Hostels)\n"
                "- **Phone**: `+91 99660 01761`"
            ),
            "citations": ["Handbook 2026-27 p.23", "Handbook 2026-27 p.24"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Raise Complaint in FretBox",
                "intent": "water",
                "icon": "🚰",
            },
            "actions": {
                "calls": [
                    {
                        "number": "+91 99660 01761",
                        "tel": "tel:+919966001761",
                        "label": "Call Hostel AO",
                    }
                ],
            },
        }

    # -------------------------------------------------------------
    # 4. CLEANING / WASHROOM ISSUE
    # -------------------------------------------------------------
    if intent == "HOSTEL_CLEANING_ISSUE":
        return {
            "answer": (
                "Cleanliness and hygiene are strictly monitored at SR University hostels. You can schedule "
                "housekeeping or report uncleaned washrooms directly through **FretBox**.\n\n"
                "### How to Request Cleaning in FretBox:\n"
                "1. Open the **FretBox** application.\n"
                "2. Go to **Complaints** ➔ **Housekeeping & Cleanliness**.\n"
                "3. Select **Washroom / Room / Corridor Cleaning**.\n"
                "4. Mention your **Floor Proctor** or **Room Number**.\n"
                "5. Submit your request for immediate housekeeping attention."
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Raise Complaint in FretBox",
                "intent": "cleaning",
                "icon": "🧹",
            },
        }

    # -------------------------------------------------------------
    # 5. WI-FI / INTERNET ISSUE
    # -------------------------------------------------------------
    if intent == "HOSTEL_WIFI_ISSUE":
        return {
            "answer": (
                "Wi-Fi access is provided in all university hostel blocks for academic purposes (Handbook p. 23). "
                "If the network is down or slow in your room, log a ticket in **FretBox**:\n\n"
                "### Steps to Report Wi-Fi Issues:\n"
                "1. Open the **FretBox** application.\n"
                "2. Navigate to **Maintenance** ➔ **IT & Wi-Fi Network**.\n"
                "3. Enter your **Hostel Block** and **Room Number**.\n"
                "4. Note down your device MAC address if requested and click **Submit**."
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Raise Complaint in FretBox",
                "intent": "wifi",
                "icon": "📶",
            },
        }

    # -------------------------------------------------------------
    # 6. GENERAL MAINTENANCE / FURNITURE / DOOR LOCK
    # -------------------------------------------------------------
    if intent == "HOSTEL_MAINTENANCE_COMPLAINT":
        return {
            "answer": (
                "Sorry to hear about the maintenance issue! You can raise a repair ticket through the **FretBox application** "
                "used by SR University hostel management.\n\n"
                "### Steps to Submit a Maintenance Request:\n"
                "1. Open the **FretBox** application.\n"
                "2. Navigate to the **Maintenance / Complaints** section.\n"
                "3. Select the relevant issue (e.g., Door Lock, Cupboard, Bed/Cot, Window, Civil Repair).\n"
                "4. Enter your **Hostel Block** and **Room Details**.\n"
                "5. Submit your complaint for the hostel carpenter/supervisor to attend.\n\n"
                "If the issue is urgent or requires administrative attention, you can also contact the **Hostel Administrative Officer**:\n"
                "- **Name**: Mr. Ch. Vinay Kumar (AO, Hostels)\n"
                "- **Phone**: `+91 99660 01761`"
            ),
            "citations": ["Handbook 2026-27 p.23", "Handbook 2026-27 p.24"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Open FretBox",
                "intent": "maintenance",
                "icon": "🛠️",
            },
            "actions": {
                "calls": [
                    {
                        "number": "+91 99660 01761",
                        "tel": "tel:+919966001761",
                        "label": "Call Hostel AO",
                    }
                ],
            },
        }

    # -------------------------------------------------------------
    # 7. MEAL BOOKING
    # -------------------------------------------------------------
    if intent == "HOSTEL_MEAL_BOOKING":
        return {
            "answer": (
                "Hostel dining and meal reservations at SR University are managed through the **FretBox application**.\n\n"
                "### How to Book / Manage Meals in FretBox:\n"
                "1. Open the **FretBox** application.\n"
                "2. Tap on the **Mess / Meal Booking** section.\n"
                "3. Select the meal slot: **Breakfast, Lunch, Snacks, or Dinner**.\n"
                "4. Confirm your booking before the daily cut-off time.\n"
                "5. You can view the weekly menu planned by the **Student Hostel Committee** directly in the app.\n\n"
                "📍 **Dining Hall Location:** Beside the Boys Hostel (Beside BH-2 & BH-3, Handbook p. 23)."
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Book Meal in FretBox",
                "intent": "meal",
                "icon": "🍽️",
            },
        }

    # -------------------------------------------------------------
    # 8. HOSTEL OUTPASS
    # -------------------------------------------------------------
    if intent == "HOSTEL_OUTPASS":
        return {
            "answer": (
                "Hostel outpass requests for SR University residential students are processed digitally through the **FretBox application**.\n\n"
                "### How to Apply for an Outpass:\n"
                "1. Open the **FretBox** application.\n"
                "2. Tap on the **Outpass** module.\n"
                "3. Select the outpass type: **Day Outpass** or **Home / Night Outpass**.\n"
                "4. Enter your destination, leave date/time, expected return date/time, and parent contact details.\n"
                "5. Submit for approval from your **Hostel Warden / Floor Proctor**.\n\n"
                "📱 **Digital Gate Pass:** Once approved by hostel management, FretBox generates a verified **QR Code / Scanner Pass** "
                "that security scans at the main university gate when exiting and returning.\n\n"
                "⚠️ *Note: Outpasses are subject to hostel management and parental approval rules. They are not approved automatically.*"
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "fretbox_action",
            "fretbox": {
                "url": FRETBOX_URL,
                "label": "Apply for Outpass",
                "intent": "outpass",
                "icon": "🎫",
            },
        }

    # -------------------------------------------------------------
    # 9. HOSTEL AO CONTACT (Handbook Grounded - Call AO)
    # -------------------------------------------------------------
    if intent == "HOSTEL_AO_CONTACT":
        return {
            "answer": (
                "Here are the official contact details for the **Hostel Administrative Officer (AO)** (Handbook 2026-27 p. 7, 24):\n\n"
                "- **Name**: Mr. Ch. Vinay Kumar\n"
                "- **Designation**: Administrative Officer (AO, Hostels)\n"
                "- **Phone**: `+91 99660 01761`\n"
                "- **Email**: `c.vinaykumarreddy@sru.edu.in`\n\n"
                "You can contact the Hostel AO for administrative escalation, hostel discipline issues, or special permissions."
            ),
            "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.24"],
            "tool_calls": [],
            "mode": "hostel_contacts",
            "actions": {
                "calls": [
                    {
                        "number": "+91 99660 01761",
                        "tel": "tel:+919966001761",
                        "label": "Call AO",
                    }
                ],
                "emails": ["c.vinaykumarreddy@sru.edu.in"],
            },
        }

    # -------------------------------------------------------------
    # 10. HOSTEL CONTACT INFORMATION
    # -------------------------------------------------------------
    if intent == "HOSTEL_CONTACT_INFORMATION":
        return {
            "answer": (
                "Here are the official contact details for **SR University Hostel Management** (Handbook 2026-27 p. 7, 24):\n\n"
                "- **Administrative Officer (Hostels)**: Mr. Ch. Vinay Kumar\n"
                "  - Phone: `9966001761` | Email: `c.vinaykumarreddy@sru.edu.in`\n"
                "- **Hostel Manager (Boys)**: Mr. A. Surender\n"
                "  - Phone: `9989671719` | Email: `stu.boyshostel@sru.edu.in` / `a.surender@sru.edu.in`\n"
                "- **Hostel Manager (Girls)**: Ms. S. Shobha Rani\n"
                "  - Phone: `9701578799` | Email: `stu.girlshostel@sru.edu.in` / `s.shobharani@sru.edu.in`\n"
                "- **Hostel Fee Inquiries**: Mr. O. Krishna\n"
                "  - Phone: `8523852300`\n\n"
                "💡 For day-to-day maintenance, plumbing, room repairs, or outpass, please raise a ticket directly through **FretBox**."
            ),
            "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.24"],
            "tool_calls": [],
            "mode": "hostel_contacts",
            "actions": {
                "calls": [
                    {"number": "+91 99896 71719", "tel": "tel:+919989671719"},
                    {"number": "+91 97015 78799", "tel": "tel:+919701578799"},
                    {"number": "+91 99660 01761", "tel": "tel:+919966001761"},
                ],
                "emails": ["stu.boyshostel@sru.edu.in", "stu.girlshostel@sru.edu.in"],
            },
        }

    # -------------------------------------------------------------
    # 10. HOSTEL FACILITIES (Handbook Grounded - No FretBox button)
    # -------------------------------------------------------------
    if intent == "HOSTEL_FACILITIES":
        return {
            "answer": (
                "**SR University Hostel Accommodation & Facilities (Handbook 2026-27 p. 23):**\n\n"
                "- **Room Sharing**: Triple-sharing rooms available separately for boys and girls.\n"
                "- **Room Amenities**: Bed, mattress, study table, chair, and personal cupboard for each student.\n"
                "- **AC & Non-AC Options**: Both AC and non-AC rooms are available based on preference.\n"
                "- **Essential Facilities**: Continuous hot water, mineral drinking water, TV halls, and common reading rooms.\n"
                "- **Wi-Fi & Laundry**: High-speed Wi-Fi provided for academic work, and on-campus laundry services are available.\n"
                "- **Dining Halls**: Located conveniently near hostel blocks serving healthy North-Indian and South-Indian cuisine.\n\n"
                "Would you like details on hostel rules, block locations, or contact numbers?"
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "normal",
        }

    # -------------------------------------------------------------
    # 11. HOSTEL RULES & REGULATIONS (Handbook Grounded - No FretBox button)
    # -------------------------------------------------------------
    if intent == "HOSTEL_RULES":
        return {
            "answer": (
                "**SR University Hostel Rules & Disciplinary Policies (Handbook 2026-27 p. 23):**\n\n"
                "- **Care of Property**: Students are responsible for maintaining hostel property. Any loss or damage is charged to the responsible student(s) or divided among group members.\n"
                "- **Floor Proctors**: Each hostel floor has a designated Proctor to maintain discipline and assist with student concerns.\n"
                "- **Student Hostel Committee**: Oversees the mess menu, hostel night celebrations, and general residential welfare.\n"
                "- **Outpass Protocol**: Students leaving the campus must apply for an approved digital outpass through FretBox before gate exit.\n"
                "- **Disciplinary Actions**: Authorities hold the right to terminate hostel residency for deliberate disobedience, damaging property, or engaging in unlawful/antisocial activities.\n\n"
                "Would you like to know the hostel manager contacts or how to apply for an outpass?"
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "normal",
        }

    # -------------------------------------------------------------
    # 12. GENERAL HOSTEL INFORMATION & BLOCKS (Handbook Grounded - No FretBox button)
    # -------------------------------------------------------------
    if intent == "HOSTEL_INFORMATION":
        return {
            "answer": (
                "**SR University Hostel Overview & Block Locations (Handbook 2026-27 p. 23):**\n\n"
                "- **Boys Hostels**:\n"
                "  - **BH-2**: Located beside Dining Hall\n"
                "  - **BH-3**: Located beside Dining Hall\n"
                "  - **BH-5**: Located behind Block-2\n"
                "- **Girls Hostels**:\n"
                "  - **GH-1**: Located beside Boys Hostel\n"
                "  - **GH-8**: Located beside Boys Hostel\n"
                "- **Dining Hall**: Centrally located beside the Boys Hostel (BH-2/BH-3).\n"
                "- **Hostel Fee Inquiries**: Contact Mr. O. Krishna (`8523852300`).\n\n"
                "For room maintenance, plumbing, electrical issues, or meal bookings, students use the **FretBox** app."
            ),
            "citations": ["Handbook 2026-27 p.23"],
            "tool_calls": [],
            "mode": "normal",
        }

    return None
