from dataclasses import dataclass, field
from typing import List

from models.okf_file import OKFFile


@dataclass
class Repository:
    """
    Represents the complete OKF repository.
    """

    title: str

    files: List[OKFFile] = field(default_factory=list)