class ScanDecision:
    """
    Attributes:
      id, name, decision_code, creator, creation_time, note,
      user_identified_artifacts, location
    Functions:

    """

    def __init__(
        self,
        id: str,
        decision: str,
        creator: dict,
        created: str,
        note: str,
        user_identified_artifacts: dict,
        location: dict,
        **kwargs,
    ):
        self.id = id
        self.decision_code = decision
        self.creator = creator
        self.creation_time = created
        self.note = note
        self.user_identified_artifacts = user_identified_artifacts
        self.location = location

    def __repr__(self):
        return f"Scan Decision {self.decision_code}"
