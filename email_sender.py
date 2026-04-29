from fastapi.templating import Jinja2Templates
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

templates = Jinja2Templates(directory="templates")

def send_email(receiver, data):

    html_content = templates.get_template("email_template.html").render(
        result=data
    )

    message = Mail(
        from_email=os.getenv("SENDER_EMAIL"),
        to_emails=receiver,
        subject="Your AI Travel Plan",
        html_content=html_content
    )

    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    response = sg.send(message)

    return response.status_code