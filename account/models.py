from django.db import models, connection
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, AbstractUser
from django.contrib.auth import get_user_model


class User(AbstractUser):
    if 'auth_user' in connection.introspection.table_names():
        class Meta:
            db_table = 'auth_user'
    else:
        pass


User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    first_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    national_id = models.BigIntegerField(null=True)
    phone_number = models.CharField(max_length=11, null=True)
    postal_code = models.BigIntegerField(null=True)
    address = models.CharField(max_length=255, null=True)

    @property
    def get_full_name(self):
        return self.first_name + " " + self.last_name

    def __str__(self):
        return f"{self.national_id} {self.user.email}"
