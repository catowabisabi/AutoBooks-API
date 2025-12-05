from enum import Enum
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.db import models
from hrms.models import Designation, Department
from core.models import BaseModel


class EmployeeType(str, Enum):
    ADMIN = 'ADMIN'
    FULL_TIME = 'FULL_TIME'
    PART_TIME = 'PART_TIME'
    CONTRACTOR = 'CONTRACTOR'
    INTERN = 'INTERN'

    @classmethod
    def choices(cls):
        return [(tag, tag.value) for tag in cls]


class UserManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN'
        USER = 'USER'

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    manager = models.ForeignKey('User', on_delete=models.PROTECT, related_name='subordinates', null=True, blank=True)
    employee_type = models.CharField(
        max_length=20,
        choices=EmployeeType.choices(),
        default=EmployeeType.FULL_TIME.value,
        help_text='Type of employee (e.g., Full-Time, Part-Time, Contractor, Intern)'
    )

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
