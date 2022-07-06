class Frame:
    """
    Attributes:
      id, number, evaluation,
      file_extension, download_url
    Functions:

    """

    def __init__(
        self,
        id: str,
        frame_number: int,
        scan,
        frame_evaluation: dict,
        extension: str,
        download_url: str,
        **kwargs,
    ):
        self.id = id
        self.number = frame_number
        self.scan = scan
        self.evaluation = frame_evaluation
        self.file_extension = extension
        self.download_url = download_url

    def __repr__(self):
        return f"Frame {self.number}"
