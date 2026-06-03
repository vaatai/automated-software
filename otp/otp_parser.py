"""Robust OTP extraction engine with configurable patterns."""

import re
from dataclasses import dataclass


@dataclass
class OTPPattern:
    """A single OTP extraction pattern with metadata."""

    name: str
    pattern: str
    priority: int = 0
    flags: int = re.IGNORECASE


# Regex to strip CSS style attributes and their values from HTML
_STYLE_ATTR_RE = re.compile(r'\bstyle\s*=\s*"[^"]*"', re.IGNORECASE)
# Regex to strip entire <style> blocks
_STYLE_BLOCK_RE = re.compile(r'<style[^>]*>.*?</style>', re.IGNORECASE | re.DOTALL)


def _strip_html_noise(text: str) -> str:
    """Remove style attributes and blocks that contain CSS hex colors like #000000."""
    text = _STYLE_BLOCK_RE.sub('', text)
    text = _STYLE_ATTR_RE.sub('', text)
    return text


# Default patterns ordered by specificity (most specific first)
DEFAULT_PATTERNS: list[OTPPattern] = [
    OTPPattern(
        name="labeled_code",
        pattern=r"(?:verification\s*code|otp|pin|code)[:\s]*(\d{4,8})",
        priority=10,
    ),
    OTPPattern(
        name="code_is_your",
        pattern=r"(\d{4,8})\s*(?:is your|is the|is)",
        priority=9,
    ),
    OTPPattern(
        name="use_code",
        pattern=r"(?:use|enter|type|input)[:\s]*(\d{4,8})",
        priority=8,
    ),
    OTPPattern(
        name="code_in_p_tag",
        pattern=r"<p[^>]*>(\d{4,8})</p>",
        priority=7,
    ),
    OTPPattern(
        name="code_in_bold",
        pattern=r"<b>(\d{4,8})</b>",
        priority=7,
    ),
    OTPPattern(
        name="code_in_strong",
        pattern=r"<strong>(\d{4,8})</strong>",
        priority=7,
    ),
    OTPPattern(
        name="standalone_6digit",
        pattern=r"(?<!#)\b(\d{6})\b",
        priority=3,
    ),
    OTPPattern(
        name="standalone_4digit",
        pattern=r"(?<!#)\b(\d{4})\b",
        priority=1,
    ),
]


@dataclass
class OTPResult:
    """Result of an OTP extraction attempt."""

    otp: str | None
    pattern_name: str | None = None
    source: str | None = None
    confidence: float = 0.0


class OTPParser:
    """Configurable OTP extraction from email/SMS text.

    Supports custom patterns per website via ``add_pattern`` or
    by passing ``custom_patterns`` at init.
    """

    def __init__(
        self,
        custom_patterns: list[OTPPattern] | None = None,
        min_digits: int = 4,
        max_digits: int = 8,
    ) -> None:
        self._patterns: list[OTPPattern] = list(custom_patterns or DEFAULT_PATTERNS)
        self._patterns.sort(key=lambda p: p.priority, reverse=True)
        self.min_digits = min_digits
        self.max_digits = max_digits

    def add_pattern(self, pattern: OTPPattern) -> None:
        self._patterns.append(pattern)
        self._patterns.sort(key=lambda p: p.priority, reverse=True)

    def extract(self, text: str, source: str = "body") -> OTPResult:
        """Extract OTP from text using all registered patterns.

        Returns the first match from the highest-priority pattern.
        Strips CSS style attributes from HTML to avoid matching hex colors.
        """
        if not text:
            return OTPResult(otp=None)

        cleaned = _strip_html_noise(text)

        for pat in self._patterns:
            match = re.search(pat.pattern, cleaned, pat.flags)
            if match:
                code = match.group(1)
                if self.min_digits <= len(code) <= self.max_digits:
                    confidence = min(1.0, pat.priority / 10.0)
                    return OTPResult(
                        otp=code,
                        pattern_name=pat.name,
                        source=source,
                        confidence=confidence,
                    )
        return OTPResult(otp=None)

    def extract_from_email(
        self,
        body: str | None = None,
        subject: str | None = None,
        html_body: str | None = None,
    ) -> OTPResult:
        """Try extracting OTP from multiple email fields in priority order."""
        for text, source in [
            (body, "body"),
            (subject, "subject"),
            (html_body, "html_body"),
        ]:
            if text:
                result = self.extract(text, source=source)
                if result.otp:
                    return result
        return OTPResult(otp=None)
