import schedule
import time
import os

def run_agent():
    os.system("python main.py")

schedule.every().day.at("08:20").do(run_agent)
schedule.every().day.at("10:20").do(run_agent)
schedule.every().day.at("12:20").do(run_agent)
schedule.every().day.at("14:20").do(run_agent)

print("Scheduler Running...")

while True:
    schedule.run_pending()
    time.sleep(30)