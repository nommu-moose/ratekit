import email
import shutil
from email.header import decode_header
from email.utils import parsedate_tz, mktime_tz
from pathlib import Path
from typing import List, Optional
import pandas as pd
from datetime import datetime
import re
from bs4 import BeautifulSoup


class EmailData:
    def __init__(self, session, email_id, download_folder: Path, email_folder, download_filetypes: List[str] = None,
                 delete_files_afterwards: bool = False):
        if download_filetypes is None:
            self.download_filetypes = ['*']
        else:
            self.download_filetypes = download_filetypes
        self._session = session
        self.attachments: List[Path] = []
        # a list of pathlib.Paths to the attachment download directories - only downloaded files listed
        self.email_id = email_id
        # the id of the email the attachment came from
        self.sender: Optional[str] = None
        # the email sender
        self.subject = ''
        # the email subject
        self.message = ''
        # the email body contents
        self.date: Optional[datetime] = None
        # the datetime of the email
        self.dataframes = {}
        # dict of dataframes from the relevant compatible email attachments, filenames as keys
        self.download_folder = download_folder
        self.email_folder = email_folder
        self.delete_files_afterwards = delete_files_afterwards
        self.retrieve_data()

    def grab_date_pattern(self, pattern):
        match = re.search(pattern, self.message)
        date = None
        if match:
            date = match.group(1)
            time = match.group(2)
        return date

    def __repr__(self):
        return f"\nEmailData Object from sender: {self.sender}\nsubject: {self.subject}\nattachments: {self.attachments}"

    def __str__(self):
        return repr(self)

    def delete_files(self):
        filedir = (Path(self.download_folder).joinpath(self.email_folder).
                   joinpath(self.email_id.decode('utf-8', errors='replace')))
        try:
            shutil.rmtree(filedir)
        except FileNotFoundError:
            pass

    def retrieve_data(self):
        self.populate_object()
        self.get_dataframes()

    def populate_object(self):
        result, data = self._session.fetch(self.email_id.decode('utf-8', errors='replace'), "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        """
        # Debug: Print raw email headers
        headers = msg.items()
        for header, value in headers:
            print(f"{header}: {value}")
        """

        # Decode email sender
        sender = msg.get("From")
        if sender:
            sender = decode_header(sender)[0][0]
            if isinstance(sender, bytes):
                sender = sender.decode('utf-8', errors='replace')
        self.sender = sender

        # Decode email subject
        subject = msg.get("Subject")
        if subject:
            subject = decode_header(subject)[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode('utf-8', errors='replace')
        self.subject = subject

        # Get email date - I actually want datetime here
        date_tuple = parsedate_tz(msg.get("Date"))
        self.date = datetime.fromtimestamp(mktime_tz(date_tuple)) if date_tuple else None

        # Get email body
        if msg.is_multipart():
            message_parts = []
            for part in msg.walk():
                disposition = str(part.get("Content-Disposition"))
                content_type = part.get_content_type()
                if content_type in ["text/plain",
                                    "text/html"] and "attachment" not in disposition:
                    part_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    if content_type == "text/html":
                        part_text = BeautifulSoup(part_text, 'html.parser').get_text()
                    message_parts.append(part_text)
            self.message = "\n".join(message_parts)
        else:
            self.message = msg.get_payload(decode=True).decode('utf-8', errors='replace')

        # Collect attachments
        attachments = []
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            # todo: don't download everything straight up, get names first and download elsewhere with path matches
            if filename:
                filepath = (Path(self.download_folder).joinpath(self.email_folder).
                            joinpath(self.email_id.decode('utf-8', errors='replace')).joinpath(filename))
                if (any(filepath.suffix == filetype for filetype in self.download_filetypes)
                        or '*' in self.download_filetypes):
                    attachments.append(filepath)
                    filepath.parent.mkdir(exist_ok=True, parents=True)

                    # Save attachment
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))

        self.attachments = attachments

    def get_dataframes(self):
        for filepath in self.attachments:
            df = None
            if filepath.suffix == '.csv':
                df = pd.read_csv(filepath)
            elif filepath.suffix == '.xlsx' or filepath.suffix == '.xls':
                df = pd.read_excel(filepath)
            if df is not None:
                self.dataframes[filepath.name] = df
            if self.delete_files_afterwards:
                filepath.unlink()

    def get_filetype(self, filetype):
        return_dict = self.get_filetype_multi(filetype, multi=False)
        if not return_dict:
            return None
        else:
            return list(return_dict.values())[0]

    def get_filetype_multi(self, filetype, multi=True):
        return_dict = {}
        for key, item in self.dataframes.items():
            suffix = Path(key).suffix
            if suffix == filetype and not multi:
                return {key: item}
            return_dict[key] = item
        return return_dict

    def get_matching_attachment(self, txt):
        return_dict = self.get_matching_attachments(txt, multi=False)
        if not return_dict:
            return None
        else:
            return list(return_dict.values())[0]

    def get_matching_attachments(self, txt, complete_match=False, multi=True):
        return_dict = {}
        for key, item in self.dataframes.items():
            if (complete_match and txt == key.name) or (not complete_match and txt in key.name):
                if not multi:
                    return {key: item}
                return_dict[key] = item
        return return_dict

    import re

    def get_regex_attachments(self, regex, complete_match=False, multi=True):
        return_dict = {}
        for key, item in self.dataframes.items():
            if complete_match:
                # Match the entire string with start (^) and end ($) anchors
                regex = f"^{regex}$"
                re_func = re.search
            else:
                re_func = re.match
            if re_func(regex, key.name):
                if not multi:
                    return {key: item}
                return_dict[key] = item
        return return_dict

    def copy_email_and_delete(self, new_folder: str):
        # Fallback to COPY and delete if MOVE is not supported
        # Copy the email to the new folder
        result = self._session.copy(self.email_id.decode('utf-8', errors='replace'), new_folder)
        if result[0] != 'OK':
            raise Exception(f"Failed to copy email to {new_folder}.")

        # Mark the original email for deletion
        self._session.store(self.email_id.decode('utf-8', errors='replace'), '+FLAGS', '\\Deleted')
        self._session.expunge()  # This removes all emails marked for deletion

        """
        # Retrieve the new email's ID from the new folder by searching for emails with the same date
        self._session.select(new_folder)
        result, data = self._session.search(None, f'SENTON "{self.date.strftime("%d-%b-%Y")}"')
        if result != 'OK':
            raise Exception(f"Failed to search for emails in {new_folder} on {self.date.strftime('%d-%b-%Y')}.")

        # Assuming the latest email with the same date is the one copied
        new_email_id = data[0].split()[-1]

        # Fetch the new email's body to compare with the original email's body
        result, fetched_data = self._session.fetch(new_email_id, '(RFC822)')
        if result != 'OK':
            raise Exception(f"Failed to fetch the new email's content.")

        new_email = email.message_from_bytes(fetched_data[0][1])
        new_email_body = self._get_email_body(new_email)

        # Compare the original and new email bodies
        if self.message != new_email_body:
            raise Exception("The body of the copied email does not match the original email.")

        # Update the email ID in the EmailData object
        self.email_id = new_email_id.encode('utf-8')
        """

    def move_email(self, new_folder: str):
        """
        Move the email to a new folder and update the email ID in the EmailData object.
        Additionally, verify that the body of the copied email matches the original one.

        :param new_folder: The name of the folder to move the email to.
        :raises Exception: If moving the email or verifying the body fails.
        """
        """
        # Check if the server supports MOVE command
        if 'MOVE' in self._session.capabilities:
            # Use the IMAP MOVE command
            result = self._session.move(self.email_id.decode('utf-8', errors='replace'), new_folder)
            if result[0] != 'OK':
                raise Exception(f"Failed to move email to {new_folder}.")
            # After moving, the email should retain the same ID, so no need to update it.
        else:
            """
        self.copy_email_and_delete(new_folder)

        # Update the folder path
        self.email_folder = new_folder
