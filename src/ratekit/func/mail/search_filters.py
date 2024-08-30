from datetime import datetime
from typing import List


def build_keyword_criteria(keywords: List[str], search_body: bool = True, search_subject: bool = True) -> str:
    """
    Builds the IMAP search criteria string for keywords.

    Args:
        keywords (List[str]): The list of keywords to search for.
        sender_list (Optional[List[str]]): The list of sender email addresses to filter using.
        search_subject (bool): Whether to search the subject text of an email.
        search_body (bool): Whether to search the body text of an email.

    Returns:
        str: The keyword criteria string.
    """
    search_criteria = []

    if search_body and keywords:
        if len(keywords) > 1:
            body_str = ' OR (' + ') ('.join([f'(BODY "{keyword}")' for keyword in keywords]) + ')'
            search_criteria.append(f'({body_str})')
        else:
            body_str = ''.join([f'BODY "{keyword}"' for keyword in keywords])
            search_criteria.append(f'{body_str}')

    if search_subject and keywords:
        if len(keywords) > 1:
            subj_str = ' OR (' + ') ('.join([f'(SUBJECT "{keyword}")' for keyword in keywords]) + ')'
            search_criteria.append(f'({subj_str})')
        else:
            subj_str = ''.join([f'SUBJECT "{keyword}"' for keyword in keywords])
            search_criteria.append(f'{subj_str}')

    if not search_criteria:
        raise ValueError("At least one of search_body or search_subject must be True.")
    if len(search_criteria) > 1:
        search_criteria_str = f"(OR ({') ('.join(search_criteria)}))"
    else:
        search_criteria_str = f"{') ('.join(search_criteria)}"

    return search_criteria_str


def build_sender_criteria(sender_list: Optional[List[str]] = None) -> str:
    """
    Builds the IMAP search criteria string for sender email addresses.

    Args:
        sender_list (Optional[List[str]]): The list of sender email addresses to filter using.

    Returns:
        str: The sender criteria string.
    """
    if not sender_list:
        return ''

    if len(sender_list) > 1:
        sender_criteria = ' '.join([f'FROM "{sender}"' for sender in sender_list])
        return f'OR ({sender_criteria})'
    else:
        return f'FROM "{sender_list[0]}"'


def build_date_criteria(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> str:
    """
    Builds the IMAP search criteria string for the date range.

    Args:
        start_date (Optional[datetime]): The start date for the search.
        end_date (Optional[datetime]): The end date for the search.

    Returns:
        str: The date criteria string.
    """
    date_criteria = []
    if start_date:
        date_criteria.append(f'SINCE {start_date.strftime("%d-%b-%Y")}')
    if end_date:
        date_criteria.append(f'BEFORE {end_date.strftime("%d-%b-%Y")}')
    return ' '.join(date_criteria)


def build_overall_criteria(keywords: List[str], search_body: bool = True, search_subject: bool = True,
                           start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                           sender_list: Optional[List[str]] = None) -> str:
    search_str = build_keyword_criteria(keywords, search_body, search_subject)
    dates_str = build_date_criteria(start_date, end_date)
    sender_str = build_sender_criteria(sender_list=sender_list)
    if sender_str:
        return f'({dates_str} {search_str} {sender_str}'
    return f'({dates_str} {search_str})'
