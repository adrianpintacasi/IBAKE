from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='%(class)s_updated')

    class Meta:
        abstract = True

class BaseProduct(TimeStampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=20)  # kg, pieces, etc.
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

class BaseAccount(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    account_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.code} - {self.name}"

class BaseTransaction(TimeStampedModel):
    date = models.DateField()
    reference = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='draft')

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.reference} - {self.date}" 