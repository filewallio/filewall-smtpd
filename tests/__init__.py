# import necessary packages
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

msg = MIMEMultipart()

message = "Thank you"

msg['From'] = "your_address"
msg['To'] = "to_address"
msg['Subject'] = "Subscription"

# add in the message body
msg.attach(MIMEText(message, 'plain'))

# Add attachment with content diposition
part = MIMEApplication(b'some file content',Name="filename")
part['Content-Disposition'] = 'attachment; filename="%s"' % "filename"
msg.attach(part)

# Add attachment withOUT content diposition
part = MIMEApplication(b'some file content2',Name="filename2")
msg.attach(part)

# Add image withOUT content diposition
part = MIMEImage(open("test.png","rb").read())
msg.attach(part)

server = smtplib.SMTP('localhost: 10025')
server.sendmail(msg['From'], msg['To'], msg.as_string())
server.quit()

print("successfully sent email to %s:" % (msg['To']))
