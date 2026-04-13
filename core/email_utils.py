import smtplib
from email.mime.text import MIMEText
from utils.config import EMAIL_ADDRESS, EMAIL_PASSWORD


def send_report_email(to_email: str, subject: str, body: str) -> str:
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials are missing. Add EMAIL_ADDRESS and EMAIL_PASSWORD in environment variables."

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, [to_email], msg.as_string())
        server.quit()

        return f"Report sent successfully to {to_email}"
    except Exception as exc:
        return f"Failed to send email: {exc}"
