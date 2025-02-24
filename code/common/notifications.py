# module with functions allowing to send notifications

import os
import smtplib
import mimetypes
from email.message import EmailMessage

def send_email(subject, body, recipients, server, port, user, password, attachments=None):

    # check recipients
    if len(recipients)<1:
        print("WARNING: Empty list of recipients. Notification will not be sent.")
        return -1


    try:
        # compose e-mail
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = ', '.join(recipients)
        msg.set_content(body)

        # add attachments (https://docs.python.org/3/library/email.examples.html)
        if attachments != None:
            for attachment in attachments:

                # make sure this is a valid file
                if not os.path.isfile(attachment):
                    print("WARNING: Could not find attachment file \"" + attachment + "\"")
                    continue

            # Guess the content type based on the file's extension.  Encoding
            # will be ignored, although we should check for simple things like
            # gzip'd or compressed files.
            ctype, encoding = mimetypes.guess_type(attachment)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            with open(attachment, 'rb') as fp:
                msg.add_attachment(fp.read(),
                                maintype=maintype,
                                subtype=subtype,
                                filename=os.path.basename(attachment))
    except Exception as e:
        print("ERROR: Could not compose e-mail notification:")
        print(e)
        return -1

    try:
        # send e-mail
        with smtplib.SMTP_SSL(server, port) as smtp_server:
            smtp_server.login(user, password)
            smtp_server.sendmail(user, recipients, msg.as_string())

    except Exception as e:
        print("ERROR: Could not send e-mail notification:")
        print(e)
        return -1
    
    return True
