import smtplib
import pandas as pd
import time, os, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Configure logging
logging.basicConfig(
    filename="email_sending.log", 
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load email list from CSV
# df = pd.read_csv("Trail.csv") # CSV should have 'Name' and 'Email' columns
df = pd.read_csv("Palak_Awasthi.csv") # CSV should have 'Name' and 'Email' columns

# Email account credentials
EMAIL = "swaraj.gupta217@gmail.com"
# https://support.google.com/accounts/answer/185833?hl=en
PASSWORD = "mjtr lvxm bkdm iggb"  # Use App Password if using Gmail

# SMTP server settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Email subject and body template
SUBJECT = "Hey, I'm Swaraj Gupta | Full-stack Data Practioner"

BODY_TEMPLATE = """\
<html>
<body>
    <p>Dear {name},</p>

    <p>I came across <b>{company_name}</b>'s work in <b>scalable data & ml pipelines, cloud-native & GenAI initiatives</b> and became really interested. I wanted to reach out regarding the junior-mid level Software Developer position in your team.

    <p>At <b>Ericsson</b>, I have been developing and optimizing <b>distributed big data pipelines, data modeling and MLOps solutions</b>, helping drive efficiency.</p>

    <p>🚀 <b>How I Can Add Value to Your Team:</b></p>
    <ul>
        ✔ <b>Data Modeling & Big Data Engineering</b> – Built cloud-native ETL pipelines using Kubernetes, PySpark, Nifi, Kafka, Airflow, DBT, Hadoop, Dremio Warehouse, MiniIO Datalake and others.<br>
        ✔ <b>Cloud Solutions</b> – CNCF CKAD holder, Certified Kubernetes Applications Developer. Hands-on with Azure, AWS and S3 storage solutions.<br>
        ✔ <b>MLOps & AI Integration</b> – Engineered ML pipelines with automated retraining, using MLflow, AutoML, Kubeflow and forecasting models.
    </ul>

    <p>I have attached my <b>resume and relevant certifications</b> for your review. I have excellent DSA and system design competence. Would you be open to a <b>quick 10-minute call</b> this week or later? I’m happy to align with your schedule. I’d love to discuss how my experience aligns with {company_name}'s goals.</p>

    <p>Looking forward to your response! 😊</p>

    <p>
    <b>Best regards,</b><br>
    Swaraj Gupta<br>
    🔗 <a href="https://www.linkedin.com/in/s3arajgupta/">LinkedIn</a> | 🔗 <a href="https://leetcode.com/u/s3arajgupta/">LeetCode</a><br>
    <b>2.8 Years Experience @ Ericsson | IIIT-NR ECE | Samsung R&D Bengaluru Hackathon Winner💡 | MITACS GRI'21 Montreal✈️ </b><br>
    </p>
    
    <p><b>P.S.</b> I recently built an <b>AI-powered Wikipedia Chatbot (LLM + RAG) using agentic model</b>. Let me know if you’d like to see a demo or perhaps, a short case study on how I optimized data pipelines at Ericsson.</p>
</body>
</html>
"""

# File to attach (Update the filename if your resume is different)
ATTACHMENT_PATHS = [
    "attachments/Resume.pdf",    # Replace with actual file paths
    "attachments/CKAD_Cert.pdf",
]

# Sending emails
try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL, PASSWORD)
    logging.info("Logged into SMTP server successfully.")
except Exception as e:
    logging.error(f"Failed to login to SMTP server: {e}")
    exit()

for index, row in df.iterrows():
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = row["Email"]
        msg["Subject"] = SUBJECT

        # Customize the email body
        body = BODY_TEMPLATE.format(name=row["Name"], company_name=row.get("Company", "Your Company"))
        msg.attach(MIMEText(body, 'html'))

        # Attach files
        for file_path in ATTACHMENT_PATHS:
            if os.path.exists(file_path):
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
                    msg.attach(part)
            else:
                logging.warning(f"File not found: {file_path}")

        # Send email
        server.sendmail(EMAIL, row["Email"], msg.as_string())
        logging.info(f"Email sent to {row['Email']} ({index + 1})")
        
        print(f"Email sent to {row['Email']}")
        print("Waiting 7 seconds...")
        time.sleep(7)  # Delay to avoid spam detection
    except Exception as e:
        logging.error(f"Failed to send email to {row['Email']}: {e}")

server.quit()
print("All emails sent!")