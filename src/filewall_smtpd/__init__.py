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
import os, sys
import configparser
import hashlib
import mimetypes

CONFIGFILE = "/etc/filewall-smtpd.conf"
APIKEY = None
RECEIVE_ON = None
SEND_TO = None

class CustomSMTPServer(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        mailfrom =    mailfrom.replace('\'', '').replace('\"', '')
        rcpttos  = [ recipient.replace('\'', '').replace('\"', '') for recipient in rcpttos]
        try:
            mail = email.message_from_bytes(data)
            parts = [p for p in mail.walk()]
            parts = [MailPart(part) for part in parts]
            for part in parts:
                part.join()
            print("################", mail.as_bytes(), "################")

            try:
                server = smtplib.SMTP(SEND_TO[0], SEND_TO[1])
                server.sendmail(mailfrom, rcpttos, mail.as_bytes())
                server.quit()
            except Exception as e:
                print(e)

        except:
            print('Something went south')
            print(traceback.format_exc())
        return

class MailPart():
    def __init__(self, part):
        self.part = part
        self.active_thread = None
        self.contenttype =  self.part.get_content_type()
        self.filename =  self.part.get_param('name')
        try:  # Hack: Search for a .js extension
            fname, fextension = os.path.splitext(self.filename)
        except:
            fextension = "none"

        #self._debugprint()
        if  self.contenttype not in ('text/plain', 'text/html') or fextension == '.js':
            self.active_thread = threading.Thread(target=self._handle)
            self.active_thread.start()

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

        success = False
        result = None, None
        data = self.part.get_payload(None, True)

        if data:
            md5 = hashlib.md5(data).hexdigest()
            if not self.filename:
                self.filename = md5
            f_name, f_ext = os.path.splitext(self.filename)
            if not f_ext:
                mime_ext = mimetypes.guess_extension(self.contenttype)
                if not mime_ext:
                    mime_ext = '.bin'  # Use a generic bag-of-bits extension
                self.filename += mime_ext
            print('Sending interesting file to filewall.io: %s (%s)' % (self.filename, self.contenttype))
            success, result = Filewall(APIKEY).convert(self.filename, data)

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
            self.part['Content-Disposition'] = 'attachment; filename="%s"' % new_filename

        # CONTENT TYPE
        del self.part['Content-Type']
        if new_filename.endswith(".pdf"):
            self.part['Content-Type'] = 'application/octet-stream; name="%s"' % new_filename
        else:
            self.part['Content-Type'] = 'image/jpg; name="%s"' % ( new_filename)

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


def main():
    load_config()
    server = CustomSMTPServer(RECEIVE_ON, None)
    asyncore.loop()

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIGFILE)
    global APIKEY, RECEIVE_ON, SEND_TO
    APIKEY = config.get("main", "APIKEY")
    RECEIVE_ON = (config.get("main", "BIND_HOST"), int(config.get("main", "BIND_PORT")))
    SEND_TO = (config.get("main", "SENDTO_HOST"), int(config.get("main", "SENDTO_PORT")))


if __name__ == "__main__":
    main()
