from datetime import datetime, timedelta
from django.utils import timezone

def sync_price_cache():
    """Sync pricing data for offline use"""
    today = timezone.now().date()
    
    # Sync seller-specific prices
    for seller_price in SellerProductPrice.objects.filter(
        valid_to__gte=today,
        is_active=True
    ):
        SellerPriceCache.objects.update_or_create(
            seller=seller_price.seller,
            product=seller_price.product,
            valid_from=seller_price.valid_from,
            defaults={
                'price': seller_price.price,
                'valid_to': seller_price.valid_to,
                'is_active': seller_price.is_active
            }
        )

    # Sync general prices
    for price_plan in PricePlan.objects.filter(
        is_general=True,
        valid_to__gte=today,
        is_active=True
    ):
        for product_price in price_plan.product_prices.all():
            GeneralPriceCache.objects.update_or_create(
                product=product_price.product,
                valid_from=price_plan.valid_from,
                defaults={
                    'price': product_price.price,
                    'valid_to': price_plan.valid_to,
                    'is_active': price_plan.is_active
                }
            )

def clean_old_price_cache():
    """Remove expired cache entries"""
    today = timezone.now().date()
    SellerPriceCache.objects.filter(valid_to__lt=today).delete()
    GeneralPriceCache.objects.filter(valid_to__lt=today).delete()