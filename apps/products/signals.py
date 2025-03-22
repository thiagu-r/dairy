from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PricePlan
from .utils import process_price_plan_excel

@receiver(post_save, sender=PricePlan)
def handle_price_plan_upload(sender, instance, created, **kwargs):
    """
    When a new PricePlan is created, process the Excel file
    """
    if created:
        process_price_plan_excel(instance)