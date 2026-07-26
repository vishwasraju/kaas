from dataclasses import dataclass


@dataclass
class Paragraph:
    index: int
    text: str
    section_heading: str = ""