from django.db import models
from core.models import BaseModel


class Currency(BaseModel):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)


class Country(BaseModel):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)
    phone_code = models.CharField(max_length=10)


class Timezone(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    utc_offset = models.CharField(max_length=10)
