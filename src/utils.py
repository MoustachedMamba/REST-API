import configparser
import smtplib
import pathlib
from email.mime.text import MIMEText


config_path = pathlib.Path(__file__).parent.absolute() / "config.ini"
config = configparser.ConfigParser()
config.read(config_path)
print(config)

smtpObj = smtplib.SMTP_SSL(config["Email"]["host"] + ":" + config["Email"]["port"])
smtpObj.login(config["Email"]["login"], config["Email"]["password"])


def send_mail(address, subject, content):
    msg = MIMEText(content, "plain")
    msg["Subject"] = subject
    msg["From"] = config["Email"]["email"]
    smtpObj.sendmail(config["Email"]["email"], address, msg.as_string())
    return
