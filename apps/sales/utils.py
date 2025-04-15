from django.utils import timezone
from apps.products.models import PricePlan, ProductPrice

def get_product_price(product, seller, date=None):
    """Get the price for a product for a specific seller on a specific date"""
    if date is None:
        date = timezone.now().date()

    # First, try to find a special price plan for the seller
    special_price = ProductPrice.objects.filter(
        price_plan__seller=seller,
        price_plan__is_general=False,
        price_plan__valid_from__lte=date,
        price_plan__valid_to__gte=date,
        price_plan__is_active=True,
        product=product
    ).first()

    if special_price:
        return special_price.price

    # If no special price found, get the general price  
    general_price = ProductPrice.objects.filter(
        price_plan__is_general=True,
        price_plan__valid_from__lte=date,
        price_plan__valid_to__gte=date,
        price_plan__is_active=True,
        product=product
    ).first()

    if general_price:
        return general_price.price

    return None


def get_opening_balance(seller, delivery_date):
    from apps.delivery.models import DeliveryOrder
    from decimal import Decimal
    last_order = DeliveryOrder.objects.filter(
            seller=seller,
            delivery_date__lt=delivery_date
        ).order_by('-delivery_date', '-delivery_time').first()

    # Handle the case where there's no previous order
    if last_order:
        opening_balance = last_order.total_balance
        print(f"SUCCESS: Found previous order #{last_order.pk} with balance: {opening_balance}")
    else:
        opening_balance = Decimal('0.00')
    return opening_balance