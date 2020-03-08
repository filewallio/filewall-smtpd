# coding=utf-8
import smtpd
import asyncore
import traceback
import email
import base64
import threading
import smtplib
import json
import requests
import logging
import time

APIKEY = "YOUR-APIKEY"

RECEIVE_ON = ("127.0.0.1", 10025)
SEND_TO    = ("127.0.0.1", 10026)

#https://github.com/MiroslavHoudek/postfix-filter-loop
class CustomSMTPServer(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        mailfrom =    mailfrom.replace('\'', '').replace('\"', '')
        rcpttos  = [ recipient.replace('\'', '').replace('\"', '') for recipient in rcpttos]
        try:
            mail = email.message_from_bytes(data)
            parts = [MailPart(part) for part in mail.walk()]
            for part in parts:
                part.join()
            print("################", mail.as_bytes(), "################")
            try:
                server = smtplib.SMTP(SEND_TO[0], SEND_TO[1])
                server.sendmail(mailfrom, rcpttos, mail.as_bytes())
                server.quit()
            except Exception as e:
                return
                traceback.format_exc()
        except:
            print('Something went south')
            print(traceback.format_exc())
        return


class MailPart():
    def __init__(self, part):
        self.part = part
        self.maintype = self.part.get_content_maintype()
        self.active_thread = None

        if  self.maintype == "multipart":
            pass
        elif self.maintype == "text":
            pass
        elif self.maintype in [ "application", "image"]:
            self.active_thread = threading.Thread(target=self._handle)
            self.active_thread.start()
        else:
            self._clearpart()

        self._debugprint()

    def _debugprint(self):
        print("########")
        print(self.part)
        print(self.part.get_content_maintype())
        print(self.part.get_content_subtype())
        print(self.part.get_content_type())
        print(self.part.get_content_disposition())
        print("/########")

    def join(self):
        if self.active_thread is not None:
            self.active_thread.join(timeout=3600)

    def _handle(self):
        filename = self.part.get_filename()
        content  = self.part.get_payload(decode=True)

        success, result = Filewall(APIKEY).convert(filename, content)

        if success is False:
            self._clearpart()
            return

        new_filename, new_content = result

        # TRANSFER ENCODING
        del self.part['Content-Transfer-Encoding']
        self.part['Content-Transfer-Encoding'] = "base64"

        # CONTENT
        self.part.set_payload(base64.encodebytes(new_content))

        # CONTENT DISPOSITION
        if self.part.get_content_disposition() is not None:
            del self.part['Content-Disposition']
            if filename is not None:
                self.part['Content-Disposition'] = 'attachment; filename="%s"' % new_filename
            else:
                self.part['Content-Disposition'] = 'attachment; '

        # CONTENT TYPE
        del self.part['Content-Type']
        if self.maintype == "image":
            if filename is not None:
                self.part['Content-Type'] = 'image/jpg; name="%s"' % ( new_filename)
            else:
                self.part['Content-Type'] = 'image/jpg;'
        else:
            self.part['Content-Type'] = 'application/octet-stream; name="%s"' % new_filename

    def _clearpart(self):
        del self.part['Content-Transfer-Encoding']
        del self.part['Content-Type']
        del self.part['Content-Disposition']
        self.part.set_payload('')


class Filewall():
    def __init__(self, apikey):
        self.apikey = apikey

    def convert(self, source_filename, source_content):
        response = self._authorize()
        if "error" in response:
            return False, response["error"]

        success = self._upload(response["links"]["upload"], source_filename, source_content)
        if not success:
            return False, "upload_failed"

        success, url_or_msg = self._poll(response["links"]["self"])
        if not success:
            return False, url_or_msg

        success, data_or_msg = self._download(url_or_msg)
        if not success:
            return False, data_or_msg
        return True, data_or_msg

    def _authorize(self):
        logging.info('Authorize')
        result = {"error": "unknown_error"}
        for _ in range(0, 200):  # try hax 2000 seconds if we have to many requests active, user may want to upgrade his account for more parallel requests
            try:
                r = requests.post("https://filewall.io/api/authorize", headers={"APIKEY": self.apikey})
                result = json.loads(r.text)
                if r.status_code != 429: # to many parallel tasks, try again later
                    return result
            except:
                pass
            time.sleep(10)
        return result

    def _upload(self, upload_url, filename, content):
        logging.info('Upload')
        try:
            r = requests.post(upload_url, content, headers={ "filename": filename})
            return r.status_code == 202
        except:
            return False

    def _poll(self, item_url):
        for _ in range(0, 400):  # poll for max 2000 seconds
            logging.info('Waiting for result')

            response = {}
            try:
                response = requests.get(item_url, headers={"APIKEY": self.apikey})
                response = json.loads(response.text)
            except:
                pass

            if "error" in response:
                return False, response["error"]

            if "status" in response:
                if response["status"] not in ["waiting", "processing"]:
                    if response["status"] == "failed":
                        return False, "processing_failed"

                    if response["status"] == "archived":
                        return False, "file_archived"

                    if response["status"] == "finished":
                        if "links" in response and "download" in response["links"]:
                            return True, response["links"]["download"]
                        else:
                            return False, "no_download_url"

            time.sleep(5)

    def _download(self, download_url):
        logging.info('Download results')

        try:
            response = requests.get(download_url)
        except:
            return False, "download_failed"

        if response.status_code != 200:
            return False, "download_failed"

        filename = response.headers.get("content-disposition").split('; filename="')[-1].split('"')[0]

        logging.info("Secured file '%s' (%s byte) downloaded" % (filename, len(response.content)))

        return True, (filename, response.content)


server = CustomSMTPServer(RECEIVE_ON, None)
asyncore.loop()

