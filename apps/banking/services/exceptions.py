class BankingError(Exception):
    pass


class InvalidTransfer(BankingError):
    pass


class InsufficientFunds(BankingError):
    pass

