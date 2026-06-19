import time
import json
import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ======================================
# LOAD CONFIG
# ======================================

import os

username = os.environ["ARMS_USERNAME"]
password = os.environ["ARMS_PASSWORD"]

email_sender = os.environ["EMAIL_SENDER"]
email_password = os.environ["EMAIL_APP_PASSWORD"]
email_receiver = os.environ["EMAIL_RECEIVER"]

# ======================================
# CACHE
# ======================================

CACHE_FILE = "attendance_cache.json"

if os.path.exists(CACHE_FILE):

    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)

else:

    cache = {}

# ======================================
# FUNCTIONS
# ======================================
def send_email(subject, body):

    try:

        msg = MIMEMultipart()

        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = subject

        msg.attach(
            MIMEText(body, "plain")
        )

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            email_sender,
            email_password
        )

        server.send_message(msg)

        server.quit()

        print("📧 Email Sent")

    except Exception as e:

        print("Email Error:", e)
        
def save_cache(data):

    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def classes_needed(attended, total):

    attended = int(attended)
    total = int(total)

    if total == 0:
        return 0

    if attended / total >= 0.80:
        return 0

    x = 0

    while ((attended + x) / (total + x)) < 0.80:
        x += 1

    return x


# ======================================
# DRIVER
# ======================================

from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

driver.maximize_window()

try:

    # ======================================
    # LOGIN
    # ======================================

    print("\nOpening ARMS Portal...")

    driver.get("https://arms.sse.saveetha.com")

    time.sleep(3)

    driver.find_element(
        By.ID,
        "txtusername"
    ).send_keys(username)

    driver.find_element(
        By.ID,
        "txtpassword"
    ).send_keys(password)

    driver.find_element(
        By.ID,
        "btnlogin"
    ).click()

    time.sleep(5)

    print("Login Successful!")


    # ======================================
    # ATTENDANCE CONFIRMATION
    # ======================================

    print("\n==============================")
    print("ATTENDANCE CONFIRMATION")
    print("==============================")

    attendance_box = driver.find_element(
        By.ID,
        "ullnotification"
    )

    attendance_text = attendance_box.text.strip()

    if attendance_text:

        print("\n✅ Attendance Found\n")
        print(attendance_text)

        send_email(
    "📚 Attendance Received",
    attendance_text
)

    else:

        print("\n❌ No Attendance Found")

    # ======================================
    # ATTENDANCE REPORT
    # ======================================

    print("\nOpening Attendance Report...")

    driver.get(
        "https://arms.sse.saveetha.com/StudentPortal/AttendanceReport.aspx"
    )

    time.sleep(5)

    table = driver.find_element(
        By.ID,
        "tblStudent"
    )

    rows = table.find_elements(
        By.TAG_NAME,
        "tr"
    )

    print("\n==============================")
    print("TRACKED COURSES REPORT")
    print("==============================")

    for row in rows:

        cols = row.find_elements(
            By.TAG_NAME,
            "td"
        )

        if len(cols) >= 8:

            course_code = cols[1].text.strip()
            course_name = cols[2].text.strip()
            attended = cols[3].text.strip()
            total = cols[5].text.strip()
            percentage = cols[7].text.strip()

            matched = any(
                keyword.lower() in course_name.lower()
                for keyword in TRACKED_COURSES
            )

            if matched:

                print("\n--------------------------------")
                print("Course Code :", course_code)
                print("Course Name :", course_name)
                print("Attended    :", attended)
                print("Total       :", total)
                print("Percentage  :", percentage)

                current_data = {
    "attended": attended,
    "total": total,
    "percentage": percentage,
    "low_alert_sent": needed > 0
}

                previous_data = cache.get(course_name)

                if previous_data:

                    old_attended = previous_data["attended"]
                    old_total = previous_data["total"]

                    if (
                        old_attended != attended
                        or
                        old_total != total
                    ):

                        print("\n🔔 ATTENDANCE UPDATED")

                        print(
                            f"{old_attended}/{old_total}"
                            f" -> "
                            f"{attended}/{total}"
                        )

                        # Send email notification
                        send_email(
                            "Attendance Updated",
                            f"Attendance for {course_name} has been updated.\n\nOld: {old_attended}/{old_total}\nNew: {attended}/{total}"
                        )

                    else:

                        print(
                            "\nℹ️ No attendance change detected"
                        )

                else:

                    print(
                        "\n🆕 First time tracking this course"
                    )

                try:

                    pct = float(
                        percentage.replace("%", "").strip()
                    )

                except:

                    pct = 0

                needed = classes_needed(
                    attended,
                    total
                )

                if needed > 0:

                    alert_message = f"""
⚠️ LOW ATTENDANCE ALERT

Course:
{course_name}

Current:
{percentage}

Need:
{needed} consecutive classes to reach {ATTENDANCE_THRESHOLD}%

Checked:
{datetime.now().strftime('%d-%m-%Y %I:%M %p')}
"""

                    send_email(
                        "⚠️ Low Attendance Alert",
                        alert_message
                    )

                    print(
                        f"\n⚠️ Below {ATTENDANCE_THRESHOLD}%"
                    )

                    print(
                        f"Need {needed} consecutive classes "
                        f"to reach {ATTENDANCE_THRESHOLD}%"
                    )

                else:

                    print(
                        f"\n✅ Above {ATTENDANCE_THRESHOLD}%"
                    )

                cache[course_name] = current_data

    save_cache(cache)

    print("\nCache Updated Successfully")

except Exception as e:

    print("\nERROR:")
    print(e)

finally:

    print("Finished.")

    driver.quit()