from django.db import models

from apps.users.models import CustomUser

class Riders(CustomUser):
    """A custom user class to manage all riders specific informations"""
    phone_number2 = models.CharField(max_length=20)
    nin = models.CharField(max_length=20, null=False)
    nok = models.CharField(max_length=50) # next of kin
    nok_phonenumber = models.CharField(max_length=20)
    motorcycle_type = models.CharField(max_length=10)
    motorcycle_brand = models.CharField(max_length=20)
    plate_number = models.CharField(max_length=20)
    guarantor1 = models.CharField(max_length=50)
    guarantor1_number = models.CharField(max_length=20)
    guarantor2 = models.CharField(max_length=50)
    guarantor2_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=20)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=50)
    #status = models.CharField(max_length=10, default='inactive')

    #is_active = models.BooleanField(default=False)

    # Relationships
    # add one to many relationship to order items

    class Meta:
        verbose_name = "Rider Profile"
        verbose_name_plural = "Riders Profile"

    def __str__(self):
        """object return string"""
        return f'Rider: {self.first_name} {self.last_name} [{self.email}]'
