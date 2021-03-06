import datetime
import os
import subprocess
import smtplib
import socket

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dropbox import rest
from urllib3.exceptions import MaxRetryError

from config import *


NOTIFY_EMAILS = ["keith.scheiwiller@gmail.com"]
SMTP_SERVER = "smtp.depaul.edu"
SMTP_USER = None
SMTP_PASSWORD = None


def email_changes(new_files, deleted_files):
    hostname = str(socket.gethostname())

    msg = MIMEMultipart()
    msg['Subject'] = 'Slides changed on %s' % hostname
    msg['To'] = ', '.join(NOTIFY_EMAILS)
    msg['From'] = "p2b@localhost"
    msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    # Create and add body
    body = "The following files were ADDED to %s:\n" % hostname
    for nfile in new_files:
        body += " - %s\n" % nfile
    body += "The following files were REMOVED from %s:\n" % hostname
    for ofile in deleted_files:
        body += " - %s\n" % ofile
    part1 = MIMEText(body, 'plain')
    msg.attach(part1)

    # Send the email using SMTP
    s = smtplib.SMTP(SMTP_SERVER, 25)
    if SMTP_USER and SMTP_PASSWORD:
        s.login(SMTP_USER, SMTP_PASSWORD)
    s.sendmail("p2b@localhost", NOTIFY_EMAILS, msg.as_string())
    s.quit()


class Slideshow:
    def __init__(self, dbc, local_dir, db_dir):
        """
        Parameters:
            dbc: The dropboxconnector to use.
            local_dir: The local directory that will hold the images.
            db_dir: The remote Dropbox directory containing the images.
        """
        self.dbc = dbc
        self.remote_directory = "/" + (db_dir[0:-1]
                                       if db_dir[-1] == "/"
                                       else db_dir)
        self.local_directory = local_dir
        self.file_set = set([f for f in os.listdir(self.local_directory)
                             if os.path.isfile(os.path.join(
                                               self.local_directory, f))])
        self.config = Config()
        self.config_date = ""

    def run_show(self):
        """
        Run loop for slideshow.

        Parameters: n/a
        Returns: n/a
        """
        self.update_files()
        self.check_config()
        child = subprocess.Popen(["feh", "-FY", "-Sfilename", "-D",
                                  str(self.config.delay()),
                                  self.local_directory])
        while True:
            try:
                if self.dbc.poll(self.remote_directory):
                    child.kill()
                    self.config.reload(self.local_directory + "/" + "config.txt")
                    child = subprocess.Popen(["feh", "-FY", "-Sfilename", "-D",
                                              str(self.config.delay()),
                                              self.local_directory])
            except MaxRetryError as e:
                pass

            except rest.ErrorResponse as e:
                print str(datetime.datetime.now()) + ": " + str(e)

            except Exception as e:
                print str(datetime.datetime.now()) + ": " + str(e)

    def update_files(self):
        """
        Updates fileset from Dropbox if it has changed.
        Returns True if fileset changed.

        Parameters: n/a
        Returns: True if fileset has changed, otherwise False
        """
        try:
            db_files = self.dbc.get_file_list(self.remote_directory)
        except rest.ErrorResponse as e:
            print str(datetime.datetime.now()) \
                + ": Could not get remote file list."
            print e.reason
            return False
        new_files = set(db_files) - self.file_set
        old_files = self.file_set - set(db_files)
        if new_files != set() or old_files != set():
            self.file_set = set(db_files)
            for filename in new_files:
                try:
                    self.dbc.get_file(filename)
                except rest.ErrorResponse as e:
                    print str(datetime.datetime.now()) + e.reason
            for filename in old_files:
                try:
                    os.remove(self.local_directory + "/" + filename)
                except OSError:
                    pass
            print str(datetime.datetime.now()) + ": Fileset changed:"
            print self.file_set
            email_changes(new_files, old_files)
            print str(datetime.datetime.now()) \
                + ": Email sent from update_files()."
            return True
        return False

    def check_config(self):
        """
        Checks for a new config in Dropbox and downloads it.
        Returns True if there is a new config.

        Parameters: n/a
        Returns: True if there is a new config, otherwise False
        """
        try:
            config_metadata = self.dbc.get_metadata("config.txt")
        except rest.ErrorResponse:
            print str(datetime.datetime.now()) \
                + ": No config.txt in Dropbox directory. Exiting."
            sys.exit()
        if config_metadata["modified"] != self.config_date:
            print str(datetime.datetime.now()) + ": Config changed"
            self.config_date = config_metadata["modified"]
            try:
                self.dbc.get_file("config.txt")
            except rest.ErrorResponse as e:
                print str(datetime.datetime.now()) + e.reason
                return False
            self.config.reload(self.local_directory + "/" + "config.txt")
            return True
        return False
