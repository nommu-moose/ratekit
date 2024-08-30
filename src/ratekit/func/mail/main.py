import imaplib
import os
import email
import shutil
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parsedate_tz, mktime_tz
from pathlib import Path
from typing import List, Optional
import pandas as pd
from datetime import datetime
import re
from bs4 import BeautifulSoup


class EmailGrabber:
    def __init__(self, email_address: str, password: str, imap_url: str, start_date: datetime = None,
                 end_date: datetime = None, folder: str = 'inbox'):
        """
        Class containing email search info/funcs for searching/retrieving attachments.

        Args:
            email_address (str): The email address to log in to.
            password (str): The password for the email account.
            imap_url (str): The IMAP URL of the email provider.
            start_date (Optional[datetime]): The start date of the search range.
            end_date (Optional[datetime]): The end date of the search range.
            folder (str): The email folder to search (default 'inbox').
        """

        self.email_address = email_address
        self.password = password
        self.imap_url = imap_url
        self.start_date = start_date
        self.end_date = end_date
        self.folder = folder
        self.session = None
        self.keywords = []
        self.attachment_filetypes = []
        self.search_attachment_name = False
        self.search_subject = True
        self.search_body = False
        self.include_emails_without_attachments = False
        self.no_of_matches = 0  # Max no. of EmailData objects to return in a search, 0 is unlimited.
        self.search_results = []
        self.delete_downloads_after_search = False
        self.sender_filter = []  # List of email addresses to match against
        self.download_folder = Path(__file__).parent.joinpath('downloads')
        self.sort_direction = 'recent_first'  # 'recent_last' is the alternative
        self.accurate_search = True  # slower, downloads everything first and searches contents locally for a match.
        self.move_after_search = False

    def logout(self):
        self.session.logout()

    def search(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
               keywords: List[str] = None, folder: str = None, search_body: bool = None,
               search_subject: bool = None, search_attachment_name: bool = None,
               attachment_filetypes: List[str] = None, no_of_matches: int = None,
               include_emails_without_attachments: bool = None, connection_timeout: int = None):
        """
        Searches for emails within the specified criteria.

        Args:
            connection_timeout (int): the number of seconds that an imap ssl connection will last
            include_emails_without_attachments (bool): Whether to include emails without attachments in the results.
            start_date (Optional[datetime]): The start date of the search range.
            end_date (Optional[datetime]): The end date of the search range.
            keywords (Optional[List[str]]): List of keywords to search for.
            folder (str): The email folder to search (default 'inbox').
            search_body (Optional[bool]): Flag to indicate if the body should be searched.
            search_subject (Optional[bool]): Flag to indicate if the subject should be searched.
            search_attachment_name (Optional[bool]): Flag to indicate if attachment names should be searched.
            attachment_filetypes (Optional[List[str]]): List of attachment file types to search for.
            no_of_matches (Optional[int]): Max number of EmailData objects to return in a search, 0 for unlimited.

        Returns:
            Dict[str, EmailData]: A dictionary of EmailData objects containing info and dataframes from the matching email attachments.
                                  The key for the dictionary is the email_id for each email.
        """

        if not connection_timeout:
            connection_timeout = 60

        self.session = login_to_email(self.email_address, self.password, self.imap_url, timeout=connection_timeout)

        if not start_date:
            start_date = self.start_date
        if not end_date:
            end_date = self.end_date
        if not keywords:
            keywords = self.keywords
        if not folder:
            folder = self.folder
        if search_body is None:
            search_body = self.search_body
        if search_subject is None:
            search_subject = self.search_subject
        if search_attachment_name is None:
            search_attachment_name = self.search_attachment_name
        if not attachment_filetypes:
            attachment_filetypes = self.attachment_filetypes
        if no_of_matches is None:
            no_of_matches = self.no_of_matches
        if include_emails_without_attachments is None:
            include_emails_without_attachments = self.include_emails_without_attachments

        results = search_emails(self.session, keywords, self.download_folder, search_subject=search_subject,
                                search_body=search_body, search_attachment_name=search_attachment_name,
                                attachment_filetypes=attachment_filetypes, folder=folder,
                                start_date=start_date, end_date=end_date,
                                no_of_matches=no_of_matches, accurate_search=self.accurate_search,
                                sender_list=self.sender_filter,
                                include_emails_without_attachments=include_emails_without_attachments)

        self.search_results = results

        return results


def get_emails(session: imaplib.IMAP4_SSL, email_ids: List[str], attachment_filetypes: List[str], download_folder: Path,
               include_emails_without_attachments: bool, email_folder: str, sort_direction: str):
    """
    Retrieves email objects based on the provided email IDs.
    todo: finish docstring
    Args:
        sort_direction:
        download_folder:
        attachment_filetypes:
        include_emails_without_attachments:
        email_folder:
        email_ids (List[str]): List of email IDs to retrieve.

    Returns:
        List[EmailData]: A list of EmailData objects.
    """
    mail_objects = get_desired_email_objects(
        session=session, email_ids=email_ids, download_filetypes=attachment_filetypes,
        download_folder=download_folder,
        include_emails_without_attachments=include_emails_without_attachments, email_folder=email_folder,
        sort_direction=sort_direction
    )

    return mail_objects


def login_to_email(email_address: str, password: str, imap_url: str, timeout: int = 60) -> imaplib.IMAP4_SSL:
    """
    Logs into the email account.

    Args:
        timeout (int): the time in seconds to time out a connection
        email_address (str): The email address to log in to.
        password (str): The password for the email account.
        imap_url (str): The IMAP URL of the email provider.

    Returns:
        imaplib.IMAP4_SSL: The logged in IMAP session.
    """
    try:
        mail = imaplib.IMAP4_SSL(imap_url, 993, timeout=timeout)
        mail.login(email_address, password)
        return mail
    except Exception as e:
        raise ConnectionError(f"Failed to login: {e}")


def search_emails(mail: imaplib.IMAP4_SSL, keywords: List[str], download_folder: Path,
                  start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, folder: str = 'inbox',
                  search_body: bool = True, search_subject: bool = True, search_attachment_name: bool = False,
                  include_emails_without_attachments: bool = True,
                  attachment_filetypes: List[str] = None, no_of_matches: int = 0, accurate_search: bool = False,
                  sender_list: Optional[List[str]] = None) -> List[EmailData]:
    """
    Searches for emails containing a specific keyword in the subject or body within a date range.

    Args:
        include_emails_without_attachments (bool): whether to include email objects that don't have attachments
        mail (imaplib.IMAP4_SSL): The logged in IMAP session.
        keywords (List[str]): The keyword to search for.
        download_folder (Path): the folder to download to.
        start_date (Optional[datetime]): The start date for the search. Defaults to None.
        end_date (Optional[datetime]): The end date for the search. Defaults to None.
        folder (str): The email folder to search in. Defaults to 'inbox'.
        search_body (bool): Whether to search the body text of an email.
        search_subject (bool): Whether to search the subject text of an email.
        search_attachment_name (bool): Whether to search the attachment names of an email.
        attachment_filetypes (List[str]): The list of filetypes allowed to be returned.
        no_of_matches (int): The number of emails to return. Defaults to 0 (unlimited).
        accurate_search (bool): download all and search emails locally (slower).
        sender_list (Optional[List[str]]): the list of senders to limit search to.

    Returns:
        List[int]: List of email IDs containing the keyword in subject or body within the date range.
    """
    if sender_list is None:
        sender_list = []
    if search_attachment_name or accurate_search:
        return search_emails_slow(mail=mail, keywords=keywords, folder=folder, download_folder=download_folder,
                                  search_body=search_body,
                                  search_subject=search_subject, start_date=start_date, end_date=end_date,
                                  sender_list=sender_list,
                                  include_emails_without_attachments=include_emails_without_attachments)
    try:
        mail.select(folder)
        criteria_str = build_overall_criteria(keywords=keywords, search_body=search_body, search_subject=search_subject,
                                              start_date=start_date, end_date=end_date)

        result, data = mail.search(None, criteria_str)
        email_ids = data[0].split()

        return email_ids
    except Exception as e:
        raise RuntimeError(f"Failed to search emails: {e}")


def fetch_emails_in_date_range(mail: imaplib.IMAP4_SSL, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None, folder: str = 'inbox',
                               sender_list: Optional[List[str]] = None) -> List[str]:
    """
    Fetches email IDs within a specific date range.

    Args:
        mail (imaplib.IMAP4_SSL): The logged in IMAP session.
        start_date (Optional[datetime]): The start date for the search. Defaults to None.
        end_date (Optional[datetime]): The end date for the search. Defaults to None.
        folder (str): The email folder to search in. Defaults to 'inbox'.
        sender_list (Optional[List[str]]): the list of senders to limit search to.

    Returns:
        List[int]: List of email IDs within the date range.
    """
    try:
        mail.select(folder)
        date_criteria_str = build_date_criteria(start_date=start_date, end_date=end_date)
        sender_criteria_str = build_sender_criteria(sender_list=sender_list)
        criteria_str = date_criteria_str
        if sender_criteria_str:
            criteria_str = f'{date_criteria_str} {sender_criteria_str}'
        if criteria_str and criteria_str[0] == ' ':
            criteria_str = criteria_str[1:]

        result, data = mail.search(None, criteria_str)
        email_ids = data[0].split()
        return email_ids
    except Exception as e:
        raise RuntimeError(f"Failed to fetch email IDs: {e}")


def fetch_email_message(mail: imaplib.IMAP4_SSL, email_id: int) -> EmailMessage:
    """
    Fetches the email message by ID.

    Args:
        mail (imaplib.IMAP4_SSL): The logged in IMAP session.
        email_id (int): The ID of the email.

    Returns:
        EmailMessage: The email message.
    """
    try:
        result, data = mail.fetch(str(email_id), "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        return msg
    except Exception as e:
        raise RuntimeError(f"Failed to fetch email message: {e}")


def keywords_in_subject(msg: EmailMessage, keywords: List[str]) -> bool:
    """
    Checks if the keyword is in the subject of the email.

    Args:
        msg (EmailMessage): The email message.
        keywords (List[str]): The keywords to search for.

    Returns:
        bool: True if the keyword is in the subject, False otherwise.
    """
    try:
        subject = decode_header(msg["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode('utf-8', errors='replace')
        return any(keyword in subject for keyword in keywords)
    except Exception as e:
        raise RuntimeError(f"Failed to check keyword in subject: {e}")


def keywords_in_body(msg: EmailMessage, keywords: List[str]) -> bool:
    """
    Checks if the keyword is in the body of the email.

    Args:
        msg (EmailMessage): The email message.
        keywords (List[str]): The keyword to search for.

    Returns:
        bool: True if the keyword is in the body, False otherwise.
    """
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    if any(keyword in body for keyword in keywords):
                        return True
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
            if any(keyword in body for keyword in keywords):
                return True
        return False
    except Exception as e:
        raise RuntimeError(f"Failed to check keyword in body: {e}")


def keywords_in_attachment_names(msg: EmailMessage, keywords: List[str]) -> bool:
    """
    Checks if the keyword is in the attachment filenames of the email.

    Args:
        msg (EmailMessage): The email message.
        keywords (List[str]): The keyword to search for.

    Returns:
        bool: True if the keyword is in the attachment filenames, False otherwise.
    """
    try:
        for part in msg.walk():
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            if filename and any(keyword in filename for keyword in keywords):
                return True
        return False
    except Exception as e:
        raise RuntimeError(f"Failed to check keyword in attachment filenames: {e}")


def search_emails_slow(mail: imaplib.IMAP4_SSL, keywords: List[str], download_folder: Path, folder: str = 'inbox',
                       search_body: bool = True, search_subject: bool = True, search_attachment: bool = False,
                       start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                       sender_list: Optional[List[str]] = None, download_filetypes: Optional[List[str]] = None,
                       include_emails_without_attachments: bool = False, sort_direction: str = 'recent_first') \
        -> List[EmailData]:
    """
    Loads each email individually within a certain timeframe and searches each string manually for the contents.

    Args:
        mail (imaplib.IMAP4_SSL): The logged in IMAP session.
        keywords (List[str]): The keyword to search for.
        download_folder (Path): The path to download the attachments to.
        folder (str): The email folder to search in. Defaults to 'inbox'.
        search_body (bool): Whether to search the body text of an email.
        search_subject (bool): Whether to search the subject text of an email.
        search_attachment (bool): Whether to search the filename of the attachment.
        start_date (Optional[datetime]): The start date for the search. Defaults to None.
        end_date (Optional[datetime]): The end date for the search. Defaults to None.
        sender_list (Optional[List[str]]): the list of senders to limit search to.
        download_filetypes (Optional[List[str]]): the filetypes of attachment that should be downloaded.
        include_emails_without_attachments (bool): whether to omit from the returned results emails without attachments
        sort_direction (str): sort results by recent_first or recent_last, defaults to first.

    Returns:
        List[int]: List of email IDs containing the keyword in the body, subject,
            or attachment names within the date range.
    """
    if sender_list is None:
        sender_list = []
    if download_filetypes is None:
        download_filetypes = ['*']
    # try:
    email_ids = fetch_emails_in_date_range(mail, start_date, end_date, folder, sender_list)

    mail_objects = get_desired_email_objects(mail, email_ids, download_filetypes, download_folder,
                                             include_emails_without_attachments, email_folder=folder,
                                             sort_direction=sort_direction)

    mail_objects_to_return = []

    if (type(keywords) is list and '*' in keywords) or keywords == '*':
        mail_objects_to_return = [m_obj for m_obj in mail_objects]
    else:
        for m_obj in mail_objects:
            if search_subject and any(keyword in m_obj.subject for keyword in keywords):
                mail_objects_to_return.append(m_obj)
            elif search_body and any(keyword in m_obj.message for keyword in keywords):
                mail_objects_to_return.append(m_obj)
            elif search_attachment and any(any(
                    keyword in attachment.name for attachment in m_obj.attachments
            ) for keyword in keywords):
                mail_objects_to_return.append(m_obj)
            else:
                m_obj.delete_files()

    return mail_objects_to_return


def get_desired_email_objects(session: imaplib.IMAP4_SSL, email_ids: List[str], download_filetypes: List[str],
                              download_folder: Path, include_emails_without_attachments: bool, email_folder: str = '',
                              sort_direction: str = 'recent_first') -> List[EmailData]:
    """
    Retrieves email objects based on a list of email IDs and downloads their attachments.

    Args:
        session (imaplib.IMAP4_SSL): The IMAP session object for interacting with the email server.
        email_ids (List[str]): A list of email IDs to retrieve.
        download_filetypes (List[str]): A list of file types to download from the email attachments.
        download_folder (Path): The folder where attachments will be downloaded.
        include_emails_without_attachments (bool): Whether to include email objects that have no attachments fitting the criteria.
        email_folder (str, optional): The email folder to search in (default is '').
        sort_direction (str, optional): The direction to sort the emails. 'recent_first' sorts with the most recent emails first.
                                        'recent_last' sorts with the oldest emails first.

    Returns:
        List[EmailData]: A sorted list of EmailData objects based on the provided criteria.

    Raises:
        ValueError: If sort_direction is not 'recent_first' or 'recent_last'.
    """
    email_objects = []
    for email_id in email_ids:
        email_object = EmailData(session, email_id, download_folder, email_folder,
                                 download_filetypes=download_filetypes)
        email_objects.append(email_object)
    email_objects = sort_email_objects(email_objects, include_emails_without_attachments, sort_direction=sort_direction)
    return email_objects


def sort_email_objects(emails: List[EmailData], include_emails_without_attachments: bool,
                       sort_direction: str = 'recent_first', no_of_matches: int = 0) -> List[EmailData]:
    """
    Sorts a list of email objects by their date attribute.

    Args:
        emails (List[EmailData]): A list of EmailData objects to be sorted.
        sort_direction (str): The direction to sort the emails.
                              'recent_first' sorts with the most recent emails first.
                              'recent_last' sorts with the oldest emails first.
        include_emails_without_attachments (bool): whether email objects with no attachments fitting the criteria will
                              be deleted from the returned list.
        no_of_matches (int): how many emails to return before truncating the list (0 is infinite).

    Returns:
        List[EmailData]: The sorted list of EmailData objects.

    Raises:
        ValueError: If sort_direction is not 'recent_first' or 'recent_last'.
    """
    if sort_direction not in ['recent_first', 'recent_last']:
        raise ValueError("sort_direction must be 'recent_first' or 'recent_last'")

    # Optionally filter out emails without attachments
    if not include_emails_without_attachments:
        emails = [mail for mail in emails if mail.attachments]

    if no_of_matches:
        emails = emails[:no_of_matches]

    reverse = sort_direction == 'recent_first'

    email_list = sorted(emails, key=lambda mail: mail.date, reverse=reverse)

    return email_list

# todo: oauth to work with gmail etc
# todo: test no dates
