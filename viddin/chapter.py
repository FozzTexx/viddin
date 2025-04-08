from dataclasses import dataclass

@dataclass(frozen=True)
class Chapter:
  position: float
  name: str
