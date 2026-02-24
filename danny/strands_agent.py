"""
Danny AI - Strands Agent Implementation

This module implements Danny using the Strands agent framework,
which provides built-in tool orchestration and conversation management.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# DANNY TOOLS - Strands @tool decorated functions
# =============================================================================

@tool
def get_available_appointments(
    date: Optional[str] = None,
    appointment_type: str = "30 Minute Meeting"
) -> str:
    """
    Get available appointment slots from the practice calendar.
    
    Args:
        date: The date to check (YYYY-MM-DD format). Defaults to next 7 days.
        appointment_type: Type of appointment (e.g., "30 Minute Meeting", "cleaning", "consultation")
    
    Returns:
        A formatted string listing available appointment times.
    """
    import requests
    
    api_key = os.getenv("CALENDLY_API_KEY")
    if not api_key:
        return "I apologize, but I'm having trouble accessing the scheduling system. Please call back or I can transfer you to our staff."
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        # Get user info
        user_response = requests.get("https://api.calendly.com/users/me", headers=headers)
        if user_response.status_code != 200:
            return "Unable to access scheduling system at this time."
        
        user_uri = user_response.json()["resource"]["uri"]
        
        # Get event types
        events_response = requests.get(
            "https://api.calendly.com/event_types",
            headers=headers,
            params={"user": user_uri, "active": "true"}
        )
        
        if events_response.status_code != 200:
            return "Unable to retrieve appointment types."
        
        event_types = events_response.json().get("collection", [])
        if not event_types:
            return "No appointment types are currently available."
        
        # Find matching event type
        event_type = event_types[0]  # Default to first
        for et in event_types:
            if appointment_type.lower() in et.get("name", "").lower():
                event_type = et
                break
        
        # Get available times
        from datetime import timezone
        # Must be in the future - start from now + 1 hour
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        if date:
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d")
                # Set to start of that day but ensure it's in the future
                start_time = parsed_date.replace(hour=8, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                if start_time < datetime.now(timezone.utc):
                    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
            except ValueError:
                pass
        
        end_time = start_time + timedelta(days=7)
        
        # Format times properly for Calendly API
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        availability_response = requests.get(
            "https://api.calendly.com/event_type_available_times",
            headers=headers,
            params={
                "event_type": event_type["uri"],
                "start_time": start_str,
                "end_time": end_str
            }
        )
        
        if availability_response.status_code != 200:
            error_detail = availability_response.json().get("details", [])
            if error_detail:
                error_msg = error_detail[0].get("message", "Unknown error")
                if "external calendar" in error_msg.lower():
                    return "I need to connect our calendar system. In the meantime, I can tell you our typical availability is Monday-Friday 8AM-5PM and Saturday 9AM-2PM. Would you like me to have our scheduling team call you back to confirm an appointment?"
            return f"Unable to check availability at this time. Our typical hours are Monday-Friday 8AM-5PM. Would you like me to have someone call you back?"
        
        available_times = availability_response.json().get("collection", [])
        
        if not available_times:
            return f"I don't see any openings for {event_type['name']} in the next 7 days. Would you like to be added to our waitlist?"
        
        # Format response
        slots_by_day = {}
        for slot in available_times[:15]:  # Limit to 15 slots
            slot_time = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
            day_key = slot_time.strftime("%A, %B %d")
            # Use %#I on Windows, %-I on Unix for non-zero-padded hour
            hour = slot_time.hour % 12 or 12
            minute = slot_time.strftime("%M")
            am_pm = "AM" if slot_time.hour < 12 else "PM"
            time_str = f"{hour}:{minute} {am_pm}"
            if day_key not in slots_by_day:
                slots_by_day[day_key] = []
            slots_by_day[day_key].append(time_str)
        
        result = f"I found several openings for {event_type['name']}:\n\n"
        for day, times in slots_by_day.items():
            result += f"**{day}:** {', '.join(times[:4])}\n"
        
        result += "\nWhich day and time works best for you?"
        return result
        
    except Exception as e:
        return f"I encountered an issue checking availability. Let me transfer you to our staff who can help schedule your appointment."


@tool
def book_appointment(
    date: str,
    time: str,
    patient_name: str,
    patient_email: str,
    patient_phone: Optional[str] = None,
    appointment_type: str = "30 Minute Meeting",
    notes: Optional[str] = None
) -> str:
    """
    Book an appointment for a patient and send a confirmation email.
    
    Args:
        date: The appointment date (YYYY-MM-DD format)
        time: The appointment time (e.g., "2:00 PM", "14:00")
        patient_name: The patient's full name
        patient_email: The patient's email address
        patient_phone: The patient's phone number (optional)
        appointment_type: Type of appointment
        notes: Any special notes or requests
    
    Returns:
        Confirmation message with appointment details.
    """
    from danny.tools.email_tool import send_confirmation_email as _send_email

    formatted_date = date
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        pass
    
    # --- Send confirmation email ---
    email_result = _send_email(
        patient_email=patient_email,
        patient_name=patient_name,
        appointment_date=formatted_date,
        appointment_time=time,
        appointment_type=appointment_type,
        notes=notes or "",
    )

    if email_result["success"]:
        email_status = f"✅ A confirmation email has been sent to **{patient_email}**."
    else:
        email_status = (
            f"⚠️ We could not send a confirmation email ({email_result['message']}). "
            f"Please note down your appointment details."
        )

    confirmation = f"""
✅ **Appointment Confirmed!**

**Patient:** {patient_name}
**Date:** {formatted_date}
**Time:** {time}
**Type:** {appointment_type}

{email_status}

**Reminders:**
- Please arrive 10-15 minutes early
- Bring your insurance card and a photo ID
- If you need to reschedule, please give us 24 hours notice

Is there anything else I can help you with?
"""
    return confirmation


@tool
def verify_insurance(
    insurance_carrier: str,
    member_id: Optional[str] = None,
    patient_name: Optional[str] = None
) -> str:
    """
    Verify a patient's dental insurance coverage.
    
    Args:
        insurance_carrier: Name of the insurance company (e.g., "Delta Dental", "Cigna", "Aetna")
        member_id: The insurance member ID (optional)
        patient_name: Patient's name for lookup (optional)
    
    Returns:
        Insurance coverage details and eligibility information.
    """
    # Mock insurance verification - in production would call clearinghouse API
    
    carrier_lower = insurance_carrier.lower()
    
    # Check if carrier is recognized
    known_carriers = {
        "delta dental": {"name": "Delta Dental PPO", "coverage": "excellent"},
        "cigna": {"name": "Cigna Dental", "coverage": "good"},
        "aetna": {"name": "Aetna DMO", "coverage": "good"},
        "metlife": {"name": "MetLife Dental", "coverage": "excellent"},
        "united": {"name": "United Healthcare Dental", "coverage": "good"},
        "guardian": {"name": "Guardian Dental", "coverage": "good"},
        "humana": {"name": "Humana Dental", "coverage": "moderate"},
    }
    
    carrier_info = None
    for key, info in known_carriers.items():
        if key in carrier_lower:
            carrier_info = info
            break
    
    if not carrier_info:
        return f"""
I don't have {insurance_carrier} in our system, but that doesn't mean we don't accept it.

I can have our billing team verify your coverage and call you back with the details. Would that work for you?

Alternatively, you can bring your insurance card to your appointment and we'll verify it then.
"""
    
    return f"""
Great news! Your **{carrier_info['name']}** coverage is active.

**Typical Coverage with this plan:**
- **Preventive Care** (cleanings, exams, x-rays): 100% covered
- **Basic Procedures** (fillings, extractions): 80% after deductible
- **Major Procedures** (crowns, root canals): 50% after deductible

**Important Notes:**
- Most plans have a $50-$100 annual deductible
- Annual maximum typically ranges from $1,000-$2,000
- Waiting periods may apply for major services

Would you like me to check coverage for a specific procedure, or would you like to schedule an appointment?
"""


@tool
def check_procedure_coverage(
    procedure: str,
    insurance_carrier: Optional[str] = None
) -> str:
    """
    Check insurance coverage for a specific dental procedure.
    
    Args:
        procedure: The dental procedure (e.g., "crown", "root canal", "filling", "cleaning")
        insurance_carrier: The insurance company name (optional)
    
    Returns:
        Estimated coverage and out-of-pocket costs for the procedure.
    """
    procedure_lower = procedure.lower()
    
    # Procedure database with typical costs
    procedures = {
        "cleaning": {
            "name": "Prophylaxis (Cleaning)",
            "code": "D1110",
            "category": "Preventive",
            "typical_cost": 150,
            "coverage_percent": 100
        },
        "exam": {
            "name": "Comprehensive Oral Exam",
            "code": "D0150",
            "category": "Preventive",
            "typical_cost": 75,
            "coverage_percent": 100
        },
        "filling": {
            "name": "Composite Filling",
            "code": "D2391",
            "category": "Basic",
            "typical_cost": 200,
            "coverage_percent": 80
        },
        "crown": {
            "name": "Porcelain Crown",
            "code": "D2750",
            "category": "Major",
            "typical_cost": 1200,
            "coverage_percent": 50
        },
        "root canal": {
            "name": "Root Canal (Molar)",
            "code": "D3330",
            "category": "Major",
            "typical_cost": 1100,
            "coverage_percent": 50
        },
        "extraction": {
            "name": "Simple Extraction",
            "code": "D7140",
            "category": "Basic",
            "typical_cost": 200,
            "coverage_percent": 80
        },
        "whitening": {
            "name": "Teeth Whitening",
            "code": "D9972",
            "category": "Cosmetic",
            "typical_cost": 400,
            "coverage_percent": 0
        },
        "x-ray": {
            "name": "Dental X-Rays",
            "code": "D0274",
            "category": "Preventive", 
            "typical_cost": 100,
            "coverage_percent": 100
        }
    }
    
    # Find matching procedure
    proc_info = None
    for key, info in procedures.items():
        if key in procedure_lower:
            proc_info = info
            break
    
    if not proc_info:
        return f"""
I don't have specific cost information for "{procedure}" in my database.

However, I can have our billing team provide a detailed estimate. Would you like me to:
1. Schedule a consultation where we can assess and provide an exact quote?
2. Have our billing specialist call you with coverage details?
"""
    
    insurance_pays = proc_info["typical_cost"] * (proc_info["coverage_percent"] / 100)
    patient_pays = proc_info["typical_cost"] - insurance_pays
    
    return f"""
**{proc_info['name']}** (Code: {proc_info['code']})

- **Category:** {proc_info['category']}
- **Typical Coverage:** {proc_info['coverage_percent']}%

**Estimated Costs:**
- Procedure cost: ${proc_info['typical_cost']:.2f}
- Insurance pays: ${insurance_pays:.2f}
- Your estimated cost: ${patient_pays:.2f}*

*This is an estimate. Actual costs depend on your specific plan, deductible status, and annual maximum remaining.

Would you like to schedule an appointment for this procedure?
"""


@tool
def transfer_to_staff(
    reason: str,
    urgency: str = "normal"
) -> str:
    """
    Transfer the call to a human staff member.
    
    Args:
        reason: The reason for the transfer (e.g., "billing question", "emergency", "patient request")
        urgency: The urgency level ("normal", "high", "emergency")
    
    Returns:
        Transfer confirmation message.
    """
    return f"""[TRANSFER_REQUESTED]
Reason: {reason}
Urgency: {urgency}

I'll transfer you to a staff member who can help with that. Please hold for just a moment.
"""


@tool
def get_practice_info(
    info_type: str = "hours"
) -> str:
    """
    Get information about the dental practice.
    
    Args:
        info_type: Type of information needed ("hours", "location", "services", "emergency")
    
    Returns:
        Requested practice information.
    """
    practice_name = os.getenv("PRACTICE_NAME", "Sample Dental Practice")
    
    info = {
        "hours": f"""
**{practice_name} Hours:**

- Monday - Friday: 8:00 AM - 5:00 PM
- Saturday: 9:00 AM - 2:00 PM
- Sunday: Closed

We're also available for dental emergencies 24/7. Would you like to schedule an appointment?
""",
        "location": f"""
**{practice_name} Location:**

123 Main Street, Suite 100
Raleigh, NC 27601

We have free parking available in the lot behind our building. The entrance is on the first floor.

Would you like directions or help scheduling an appointment?
""",
        "services": f"""
**Services at {practice_name}:**

**Preventive Care:**
- Cleanings & Exams
- X-Rays & Diagnostics
- Sealants & Fluoride

**Restorative:**
- Fillings
- Crowns & Bridges
- Root Canals

**Cosmetic:**
- Teeth Whitening
- Veneers
- Invisalign

**Other:**
- Extractions
- Emergency Care
- Pediatric Dentistry

Would you like to schedule an appointment for any of these services?
""",
        "emergency": f"""
**Dental Emergency?**

If you're experiencing a dental emergency, we're here to help.

**During office hours:** We reserve time slots for same-day emergencies. Let me check our availability.

**After hours:** Call our emergency line at 555-DENTAL for immediate assistance.

**What qualifies as a dental emergency:**
- Severe tooth pain
- Knocked out tooth
- Broken tooth
- Abscess or swelling
- Uncontrolled bleeding

Is this a dental emergency? I can help you get seen right away.
"""
    }
    
    info_lower = info_type.lower()
    for key, value in info.items():
        if key in info_lower:
            return value
    
    return info["hours"]


# =============================================================================
# DANNY AGENT - Strands Agent with all tools
# =============================================================================

# System prompt for Danny
DANNY_SYSTEM_PROMPT = """You are Danny, a friendly and professional AI dental assistant for {practice_name}. You answer phone calls and help patients with:

1. **Scheduling Appointments** - Check availability and book appointments
2. **Insurance Questions** - Verify coverage and estimate costs
3. **Practice Information** - Hours, location, services offered
4. **Transferring to Staff** - When patients request a human or have complex needs

## Guidelines:

- Be warm, empathetic, and professional
- Keep responses concise - this is a phone conversation
- Always confirm important details (dates, times, names)
- NEVER provide medical advice - direct clinical questions to staff
- If a patient seems distressed or mentions an emergency, prioritize getting them help
- If you can't help with something, offer to transfer to a staff member
- Respect patient privacy - don't ask for unnecessary personal information

## Response Style:

- Speak naturally, as if on a phone call
- Use short sentences that are easy to understand when spoken
- Avoid technical jargon unless explaining it
- Confirm understanding by summarizing what you heard

Remember: You are the first impression of the dental practice. Be helpful, efficient, and caring.
""".format(practice_name=os.getenv("PRACTICE_NAME", "Sample Dental Practice"))


def create_danny_agent(use_bedrock: bool = False, quiet: bool = False) -> Agent:
    """
    Create a Danny AI agent using the Strands framework.
    
    Args:
        use_bedrock: If True, use AWS Bedrock. If False, use Anthropic API directly.
        quiet: If True, suppress tool call output.
    
    Returns:
        A configured Strands Agent instance.
    """
    if use_bedrock:
        from strands.models.bedrock import BedrockModel
        model = BedrockModel(
            region_name=os.getenv("AWS_REGION", "us-west-2"),
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            max_tokens=1024
        )
    else:
        model = AnthropicModel(
            client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
            model_id="claude-sonnet-4-20250514",
            max_tokens=1024
        )
    
    # Define all Danny tools
    tools = [
        get_available_appointments,
        book_appointment,
        verify_insurance,
        check_procedure_coverage,
        transfer_to_staff,
        get_practice_info,
    ]
    
    # Set up callback handler based on quiet mode
    callback_handler = None
    if quiet:
        from strands.handlers import PrintingCallbackHandler
        callback_handler = PrintingCallbackHandler(verbose_tool_use=False)
    
    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=DANNY_SYSTEM_PROMPT,
        name="Danny",
        description="AI Dental Assistant",
        callback_handler=callback_handler
    )
    
    return agent


# Singleton agent instance
_danny_agent: Optional[Agent] = None


def get_danny_agent() -> Agent:
    """Get or create the singleton Danny agent instance."""
    global _danny_agent
    if _danny_agent is None:
        use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
        _danny_agent = create_danny_agent(use_bedrock=use_bedrock)
    return _danny_agent


# =============================================================================
# MAIN - For testing
# =============================================================================

if __name__ == "__main__":
    print("🦷 Danny AI - Strands Agent Test")
    print("=" * 50)
    
    agent = get_danny_agent()
    print(f"Agent: {agent.name}")
    print(f"Model: AnthropicModel")
    print()
    
    # Test conversation
    test_messages = [
        "Hi, I'd like to schedule a cleaning appointment",
        "What are your hours?",
        "Do you accept Delta Dental insurance?",
    ]
    
    for msg in test_messages:
        print(f"👤 User: {msg}")
        response = agent(msg)
        print(f"🤖 Danny: {response}")
        print()
