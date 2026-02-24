"""
Email confirmation tool for Danny AI.
Sends professional HTML appointment confirmation emails via SMTP.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


def _get_confirmation_html(
    patient_name: str,
    appointment_date: str,
    appointment_time: str,
    appointment_type: str,
    practice_name: str,
    practice_phone: str = "",
    notes: str = "",
) -> str:
    """Generate a professional HTML confirmation email."""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=0" />
</head>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color:#09090B;padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#00D4AA;font-size:28px;font-weight:700;letter-spacing:-0.5px;">
                {practice_name}
              </h1>
              <p style="margin:8px 0 0;color:#a1a1aa;font-size:14px;">
                Powered by Danny AI
              </p>
            </td>
          </tr>

          <!-- Confirmation Badge -->
          <tr>
            <td style="padding:32px 40px 16px;text-align:center;">
              <div style="display:inline-block;background-color:#ecfdf5;border:1px solid #00D4AA;border-radius:50%;width:64px;height:64px;line-height:64px;font-size:32px;text-align:center;">
                &#10003;
              </div>
              <h2 style="margin:16px 0 4px;color:#09090B;font-size:22px;font-weight:600;">
                Appointment Confirmed
              </h2>
              <p style="margin:0;color:#71717a;font-size:15px;">
                Hi {patient_name}, your appointment has been booked!
              </p>
            </td>
          </tr>

          <!-- Appointment Details Card -->
          <tr>
            <td style="padding:8px 40px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#fafafa;border:1px solid #e4e4e7;border-radius:10px;">
                <tr>
                  <td style="padding:24px 28px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="padding:8px 0;border-bottom:1px solid #e4e4e7;">
                          <span style="color:#71717a;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;">Date</span><br/>
                          <span style="color:#09090B;font-size:16px;font-weight:600;">{appointment_date}</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0;border-bottom:1px solid #e4e4e7;">
                          <span style="color:#71717a;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;">Time</span><br/>
                          <span style="color:#09090B;font-size:16px;font-weight:600;">{appointment_time}</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0;border-bottom:1px solid #e4e4e7;">
                          <span style="color:#71717a;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;">Appointment Type</span><br/>
                          <span style="color:#09090B;font-size:16px;font-weight:600;">{appointment_type}</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0;">
                          <span style="color:#71717a;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;">Location</span><br/>
                          <span style="color:#09090B;font-size:16px;font-weight:600;">{practice_name}</span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          {f'''<!-- Notes -->
          <tr>
            <td style="padding:0 40px 24px;">
              <div style="background-color:#fffbeb;border:1px solid #fbbf24;border-radius:8px;padding:16px 20px;">
                <strong style="color:#92400e;font-size:14px;">Note:</strong>
                <span style="color:#92400e;font-size:14px;"> {notes}</span>
              </div>
            </td>
          </tr>''' if notes else ''}

          <!-- Reminders -->
          <tr>
            <td style="padding:0 40px 32px;">
              <h3 style="margin:0 0 12px;color:#09090B;font-size:16px;font-weight:600;">Before Your Visit</h3>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:6px 0;color:#52525b;font-size:14px;">
                    &#128337;&nbsp; Please arrive <strong>10-15 minutes early</strong> for paperwork
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;color:#52525b;font-size:14px;">
                    &#128179;&nbsp; Bring your <strong>insurance card</strong> and a <strong>photo ID</strong>
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;color:#52525b;font-size:14px;">
                    &#128214;&nbsp; Bring a list of any <strong>current medications</strong>
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;color:#52525b;font-size:14px;">
                    &#128197;&nbsp; Need to reschedule? Please give us <strong>24 hours notice</strong>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Contact -->
          <tr>
            <td style="padding:0 40px 32px;text-align:center;">
              <p style="margin:0;color:#71717a;font-size:14px;">
                Questions? Contact us{f' at <strong>{practice_phone}</strong>' if practice_phone else ''}.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#09090B;padding:24px 40px;text-align:center;">
              <p style="margin:0;color:#71717a;font-size:12px;">
                &copy; {practice_name} &mdash; Scheduled with Danny AI<br/>
                <span style="color:#52525b;">This is an automated confirmation. Please do not reply to this email.</span>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_confirmation_email(
    patient_email: str,
    patient_name: str,
    appointment_date: str,
    appointment_time: str,
    appointment_type: str = "Dental Appointment",
    notes: str = "",
) -> dict:
    """
    Send an appointment confirmation email to the patient.

    Returns dict with 'success' bool and 'message' string.
    """
    # ---- SMTP config from env ----
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")  # Gmail App Password
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)
    from_name = os.getenv("SMTP_FROM_NAME", "")

    practice_name = os.getenv("PRACTICE_NAME", "Dental Practice")
    practice_phone = os.getenv("PRACTICE_PHONE", "")

    if not from_name:
        from_name = practice_name

    if not smtp_user or not smtp_password:
        logger.warning("SMTP credentials not configured – skipping confirmation email")
        return {
            "success": False,
            "message": "Email not configured. SMTP_USER and SMTP_PASSWORD environment variables are required.",
        }

    # ---- Build the email ----
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Appointment Confirmed — {appointment_date} at {appointment_time}"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = patient_email

    # Plain-text fallback
    plain = (
        f"Hi {patient_name},\n\n"
        f"Your appointment has been confirmed!\n\n"
        f"Date: {appointment_date}\n"
        f"Time: {appointment_time}\n"
        f"Type: {appointment_type}\n"
        f"Location: {practice_name}\n\n"
        f"Reminders:\n"
        f"- Please arrive 10-15 minutes early\n"
        f"- Bring your insurance card and a photo ID\n"
        f"- Need to reschedule? Please give us 24 hours notice\n\n"
        f"See you soon!\n{practice_name}"
    )
    msg.attach(MIMEText(plain, "plain"))

    # HTML version
    html = _get_confirmation_html(
        patient_name=patient_name,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        appointment_type=appointment_type,
        practice_name=practice_name,
        practice_phone=practice_phone,
        notes=notes,
    )
    msg.attach(MIMEText(html, "html"))

    # ---- Send ----
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [patient_email], msg.as_string())

        logger.info(f"Confirmation email sent to {patient_email}")
        return {
            "success": True,
            "message": f"Confirmation email sent to {patient_email}",
        }
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check SMTP_USER / SMTP_PASSWORD")
        return {
            "success": False,
            "message": "Email authentication failed. Please verify SMTP credentials.",
        }
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}",
        }
