from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Order

@receiver(post_save, sender=Order)
def reduce_stock(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        for item in instance.items.all():
            product = item.product

            # 🛡️ Prevent negative stock
            if product.stock < item.quantity:
                raise ValidationError(
                    f"Insufficient stock for {product.name}"
                )

            product.stock -= item.quantity
            product.save()
