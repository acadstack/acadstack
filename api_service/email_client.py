import logging
import smtplib
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED


class Emailer:
    """Helper class for sending emails in a separate thread
    using a ThreadPoolExecutor. The number of pending email
    tasks is specified by MAX_PENDING_TASKS, which is 1000
    by default.
    """

    MAX_PENDING_TASKS = 1000

    def __init__(self, config=None) -> None:
        """C'tor for the class. Ooptionally, it allows
        specifying a dict of settings which will be used
        to connect to the email server.

        Args:
            config (dict, optional): Email server connection settings.
            Defaults to None.
        """
        if config:
            self.config = config
            logging.info("Created emailer with config.")
        self.executor = ThreadPoolExecutor()
        self.pending_tasks = set()
        logging.info("Created TPE for emailer.")
    
    
    def configure(self, config):
        """Configures the email server connection settings.

        Args:
            config (dict): Email server connection params.
        """
        self.config = config
        logging.info("Configured emailer.")
    

    def send_mail(self, to, subject, body, attachment=None,
                att_file_name=None, use_executor=True):
        """[summary]

        Args:
            to (str): Comma-separated list of email recipients.
            subject (str): Subject of the email message to send.
            body (str): Email text to go into the message body.
            attachment (Any, optional): Attachment data. Defaults to None.
            att_file_name (str, optional): Name of the attachment file. Defaults to None.
            use_executor (bool, optional): Whether to send email syncronously,
            or via a separate thread. Defaults to True.
        """
    
        sender = self.config["user"]
        password = self.config["password"]
        host = self.config["host"]
        port = self.config["port"]
        is_fake = self.config["dryrun"]
        
        if use_executor:
            # We want to wait if there are Emailer.MAX_PENDING_TASKS
            # uncompleted tasks
            if len(self.pending_tasks) >= Emailer.MAX_PENDING_TASKS:
                done_tasks, self.pending_tasks = wait(self.pending_tasks, 
                                                    return_when=FIRST_COMPLETED)
            
            fut = self.executor.submit(self._send_mail, is_fake, sender, password, 
                    host, port, to, subject, body, 
                    attachment, att_file_name)
            self.pending_tasks.add(fut)
            logging.debug("Pending emails {0}".format(len(self.pending_tasks)))
        else:
            self._send_mail(is_fake, sender, password, 
                    host, port, to, subject, body, 
                    attachment, att_file_name)


    def _send_mail(self, is_fake, sender, password, host, port, to, 
                    subject, body, attachment=None, 
                    attach_name=None):
        try:
            if is_fake:
                logging.info("""Sending (DRYRUN) email to {0}. Subject: {1}
                Body:
                {2}
                Attachment file name: {3}
                """.format(to, subject, body, attach_name))
                return

            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = "AcadStack System <{}>".format(sender)
            msg['To'] = to
            if attachment:
                msg.add_attachment(attachment, filename=(attach_name or "attached_file"))

            with smtplib.SMTP(host, port) as s:
                s.starttls()
                s.login(sender, password)
                s.send_message(msg)

        except Exception as ex:
            msg = "Error when sending Email."
            logging.exception(msg)