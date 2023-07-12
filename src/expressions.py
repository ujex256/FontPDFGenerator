class WeightNotFoundError(Exception):
    pass


class FontNotFoundError(Exception):
    pass


class DownloadFailed(Exception):
    status_code: int
