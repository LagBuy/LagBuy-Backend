#!/usr/bin/env python3
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid


class Role(models.Model):
    '''Define user roles. Can be either or all of `user`, `seller`, `rider`'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, null=False)
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    """User manager for the custom user"""
    def create_user(self, email, password=None, **extra_fields):
        """Create a custom user"""
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        # user_role = Role.objects.get_or_create(name='user')[0]
        # user.roles.add(user_role)
        user.set_password(password)  # Stores hashed password
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create a super user"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user class"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, null=False)
    email = models.EmailField(max_length=100, unique=True)
    password_hash = models.CharField(max_length=225)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Relationships
    # wallet = models.OneToOneField('Wallet', on_delete=models.CASCADE, related_name='user')
    roles = models.ManyToManyField(Role, related_name='users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    """Custom default fields"""
    USERNAME_FIELD = 'email'

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        """object return string"""
        return f'User: [{self.email}]'

