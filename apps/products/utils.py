import pandas as pd
from datetime import date
import logging
from django.db import transaction
from .models import Product, ProductPrice

logger = logging.getLogger(__name__)

def process_price_plan_excel(price_plan):
    """
    Process the uploaded Excel file and create ProductPrice entries
    """
    try:
        logger.info(f"Starting to process Excel file for price plan {price_plan.id}")
        
        # Ensure the file exists and is readable
        if not price_plan.excel_file:
            logger.error("No excel file found")
            return False

        # Read the Excel file using pandas
        try:
            df = pd.read_excel(price_plan.excel_file.path)
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            return False
        
        # Validate columns
        required_columns = ['product_code', 'price']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Missing required columns. Found columns: {df.columns.tolist()}")
            return False

        with transaction.atomic():
            # Delete existing prices
            ProductPrice.objects.filter(price_plan=price_plan).delete()
            
            # Process each row
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    product_code = str(row['product_code']).strip()
                    price = float(row['price'])
                    
                    product = Product.objects.get(code=product_code)
                    
                    ProductPrice.objects.create(
                        price_plan=price_plan,
                        product=product,
                        price=price
                    )
                    success_count += 1
                    
                except Product.DoesNotExist:
                    logger.error(f"Product with code {product_code} not found")
                    error_count += 1
                except Exception as e:
                    logger.error(f"Error processing row {index}: {str(e)}")
                    error_count += 1

            logger.info(f"Processed {success_count} prices successfully, {error_count} errors")
            
            return success_count > 0

    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
        return False

def get_product_price(product, seller, date=None):
    """
    Get the price for a product for a specific seller on a specific date
    If no date is provided, use current date
    """
    if date is None:
        date = date.today()

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
