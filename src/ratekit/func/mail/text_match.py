from ratekit.func.types import enforce_types_object, enforce_types_functional
import re

from typing import Optional, List, Union


class StringMatch:
    """
    Attributes:
        found (bool): Whether a match was found.
        index (Optional[int]): The starting index of the match, if found.
        matched_string (Optional[str]): The matched string, if found.
        matched_groups (List[str]): A list of matched groups, if any.
    """
    @enforce_types_object
    def __init__(self, pattern: str, match_against: str, is_regex: bool = False, complete_match: bool = False):
        """
        Initializes a StringMatch instance to find and store match details between a pattern and a target string.

        Args:
            pattern (str): The pattern to search for.
            match_against (str): The string to search within.
            is_regex (bool, optional): Whether the pattern is a regular expression. Defaults to False.
            complete_match (bool, optional): Whether to require a complete match (as opposed to a partial match).
                Defaults to False.

        Attributes:
            pattern (str): The pattern to search for.
            match_against (str): The string to search within.
            is_regex (bool): Whether the pattern is a regular expression.
            complete_match (bool): Whether a complete match is required.
        """
        self.found: bool = False
        self.index: Optional[int] = None
        self.matched_string: Optional[str] = None
        self.matched_groups: List[str] = []
        self.pattern: str = pattern
        self.match_against: str = match_against
        self.is_regex: bool = is_regex
        self.complete_match: bool = complete_match
        self.match_string_main()

    def match_string_main(self) -> None:
        """
        Performs the string matching based on the initialized parameters. Delegates to either the regex matching
            function
        or the standard string matching function depending on the is_regex flag.
        """
        if self.is_regex:
            self.match_regex()
        else:
            self.match_standard()

    def match_regex(self) -> None:
        """
        Performs regex-based string matching and updates instance attributes with match details.
        """
        if self.complete_match:
            match = re.fullmatch(self.pattern, self.match_against)
            if match:
                self.found = True
                self.index = 0
                self.matched_string = self.match_against
                self.matched_groups = [self.match_against]
        else:
            match = re.search(self.pattern, self.match_against)
            if match:
                self.found = True
                self.index = match.start()
                self.matched_string = ''.join(match.groups()) if match.groups() else match.group()
                self.matched_groups = list(match.groups())

    def match_standard(self) -> None:
        """
        Performs standard string matching and updates instance attributes with match details.
        """
        if self.complete_match:
            self.found = self.pattern == self.match_against
            if self.found:
                self.index = 0
                self.matched_string = self.match_against
                self.matched_groups = [self.match_against]
        else:
            self.found = self.pattern in self.match_against
            if self.found:
                self.index = self.match_against.find(self.pattern)
                self.matched_string = self.match_against
                self.matched_groups = [self.match_against]

    def __bool__(self) -> bool:
        """
        Returns whether a match was found.

        Returns:
            bool: True if a match was found, otherwise False.
        """
        return self.found

    def __eq__(self, other: Union[str, 'StringMatch']) -> bool:
        """
        Compares the matched string to another string or StringMatch instance.

        Args:
            other (Union[str, StringMatch]): The string or StringMatch instance to compare against.

        Returns:
            bool: True if the matched strings are equal, otherwise False.
        """
        return self.matched_string == other

    def __ne__(self, other: Union[str, 'StringMatch']) -> bool:
        """
        Checks if the matched string is not equal to another string or StringMatch instance.

        Args:
            other (Union[str, StringMatch]): The string or StringMatch instance to compare against.

        Returns:
            bool: True if the matched strings are not equal, otherwise False.
        """
        return not self.__eq__(other)
