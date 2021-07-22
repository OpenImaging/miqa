import re


class Re:
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def __eq__(self, other):
        return self.pattern.fullmatch(other) is not None

    def __str__(self):
        return self.pattern.pattern

    def __repr__(self):
        return repr(self.pattern.pattern)


PATH_RE = Re(r'\/.+')
