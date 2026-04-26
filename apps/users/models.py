from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class KycStatus(models.TextChoices):
        NEW = "NEW", "New"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    email = models.EmailField("email address", unique=True)
    kyc_status = models.CharField(
        max_length=16, choices=KycStatus.choices, default=KycStatus.NEW
    )

    def __str__(self) -> str:
        if self.email:
            return self.email
        return self.username
