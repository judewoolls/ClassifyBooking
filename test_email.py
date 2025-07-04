import smtplib
import ssl
import os
import certifi
from dotenv import load_dotenv # Import load_dotenv to read .env file

# Load environment variables from the .env file
# This must be called before accessing os.environ.get() for variables in .env
load_dotenv()

# --- Email Configuration (read from .env or use fallbacks) ---
# It's good practice to get these from environment variables for flexibility
# If you're running this script directly without a .env, you can temporarily
# hardcode values here for testing, but remember to remove them for production.

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587)) # Ensure port is an integer
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD') # This should be your 16-char App Password
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

# Recipient for the test email
TO_EMAIL = 'jwoolls01@gmail.com' # Replace with your actual test recipient email

# --- Print configuration for debugging ---
print(f"Attempting to connect to {EMAIL_HOST}:{EMAIL_PORT}")
print(f"Using user: {EMAIL_HOST_USER}")
print(f"Certifi CA bundle path: {certifi.where()}")
print(f"Is EMAIL_HOST_PASSWORD loaded? {bool(EMAIL_HOST_PASSWORD)}") # Check if password string is non-empty

# --- Pre-check for missing credentials ---
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    print("Error: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD not loaded from environment variables.")
    print("Please ensure your .env file is correctly configured and located in the same directory as this script.")
    exit() # Exit the script if credentials are missing

# --- SMTP Connection and Email Sending Logic ---
try:
    # Create a default SSL context using certifi's CA bundle
    # This helps verify the server's SSL certificate
    context = ssl.create_default_context(cafile=certifi.where())

    # Connect to the SMTP server
    # Use with statement to ensure the connection is properly closed
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        # Start TLS (Transport Layer Security) encryption
        # This upgrades the connection to be secure
        server.starttls(context=context)

        # Log in to the SMTP server with your credentials
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

        # Create the email message
        subject = "Direct Python SMTP Test Email from ClassFit (Gmail)"
        body = "This is a test email sent directly using Python's smtplib, bypassing Django. If you received this, the SMTP connection is working!"
        message = f"Subject: {subject}\n\n{body}"

        # Send the email
        # The first argument is the sender, second is the recipient(s), third is the message itself
        server.sendmail(DEFAULT_FROM_EMAIL, TO_EMAIL, message)
        print("Email sent successfully!")

except ssl.SSLCertVerificationError as e:
    print(f"SSL Certificate Verification Error: {e}")
    print("This means Python cannot verify the server's SSL certificate.")
    print("Ensure certifi is installed and your system's root certificates are up-to-date.")
except smtplib.SMTPAuthenticationError as e:
    print(f"SMTP Authentication Error: {e}")
    print("This means your username or password (App Password for Gmail) is incorrect.")
    print("Double-check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your .env file.")
except smtplib.SMTPConnectError as e:
    print(f"SMTP Connection Error: {e}")
    print("This means the server could not be reached. Check EMAIL_HOST, EMAIL_PORT, and your network connectivity/firewall.")
except Exception as e:
    # Catch any other unexpected errors and print them
    print(f"An unexpected error occurred: {e}")

