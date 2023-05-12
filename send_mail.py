import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

from report_html import generate_report_html

load_dotenv()

ADDR_FROM = os.getenv('ADDR_FROM')
ADDR_TO = os.getenv('ADDR_TO')
PASSWORD = os.getenv('PASSWORD')
SERVER = os.getenv('SERVER')
PORT = os.getenv('PORT')


def send_mail(table, date_from, date_to=None, email=''):
    addr_to = email if email else ADDR_TO

    message = MIMEMultipart()
    message['From'] = ADDR_FROM
    message['To'] = addr_to

    if date_to:
        subject = f'Звіт з {date_from} по {date_to}'
    else:
        subject = f'Звіт за {date_from}'

    message['Subject'] = subject

    html = generate_report_html(table, date_from, date_to)
    message.attach(MIMEText(html, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(SERVER, int(PORT)) as server:
        server.login(ADDR_FROM, PASSWORD)
        try:
            server.send_message(message)
        except smtplib.SMTPRecipientsRefused:
            pass
