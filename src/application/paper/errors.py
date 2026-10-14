"""Finite local owning denials; never arbitrary exception text or authority."""

QUALIFICATION_DENIALS=frozenset(('OWNING_SOFTWARE_QUALIFICATION_STORE_MISSING',
    'OWNING_SOFTWARE_QUALIFICATION_RECEIPT_MISSING'))


class NativePaperReleaseUnavailable(ValueError):
    def __init__(self,reason_code):
        if type(reason_code) is not str or reason_code not in QUALIFICATION_DENIALS:
            raise ValueError('Finite native Paper qualification denial required')
        self.reason_code=reason_code
        super().__init__(reason_code)
