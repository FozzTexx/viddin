from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class Chapter:
  position: float
  name: str
