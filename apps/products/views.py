from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views import View
from web_project.mixins import AdminRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from web_project import TemplateLayout
from .models import Category, Product, PricePlan, Seller, ProductPrice
import json
from urllib.parse import parse_qs
import xlsxwriter
from io import BytesIO
from datetime import date
from .utils import process_price_plan_excel
import logging
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

class CategoryListView(LoginRequiredMixin, TemplateView):
    template_name = "products/category_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['categories'] = Category.objects.all().order_by('-created_at')
        return context

class CategoryCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        return render(request, 'products/category_form.html')
    
    def post(self, request):
        name = request.POST.get('name')
        code = request.POST.get('code')
        
        Category.objects.create(
            name=name,
            code=code,
            created_by=request.user
        )
        
        # Render only the table partial
        response = render(
            request,
            'products/partials/category_table.html',
            {'categories': Category.objects.all().order_by('-created_at')}
        )
        
        # Add HX-Trigger header
        response['HX-Trigger'] = 'closeModal'
        
        return response

class CategoryEditFormView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, category_id):
        category = Category.objects.get(id=category_id)
        return render(request, 'products/category_edit_form.html', {'category': category})

class CategoryEditView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def put(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
            
            # Parse the PUT data
            body = request.body.decode('utf-8')
            if request.content_type == 'application/json':
                data = json.loads(body)
            else:
                # Parse form data
                data = parse_qs(body)
                # Convert from lists to single values
                data = {k: v[0] for k, v in data.items()}
            
            # Update category fields
            if 'name' not in data or 'code' not in data:
                return HttpResponseBadRequest('Name and code are required')
                
            category.name = data['name']
            category.code = data['code']
            category.updated_by = request.user
            category.save()
            
            # Render only the table partial
            response = render(
                request,
                'products/partials/category_table.html',
                {'categories': Category.objects.all().order_by('-created_at')}
            )
            
            # Add HX-Trigger header
            response['HX-Trigger'] = 'closeModal'
            
            return response
            
        except Category.DoesNotExist:
            return HttpResponseBadRequest('Category not found')
        except Exception as e:
            return HttpResponseBadRequest(str(e))

class ProductListView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "products/product_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        # Add status filter
        status_filter = self.request.GET.get('status', 'active')
        products = Product.objects.select_related('category')
        
        if status_filter == 'active':
            products = products.filter(is_active=True)
        elif status_filter == 'inactive':
            products = products.filter(is_active=False)
            
        context['products'] = products.order_by('-created_at')
        context['categories'] = Category.objects.all().order_by('name')
        context['current_status'] = status_filter
        return context

class ProductCreateView(LoginRequiredMixin, AdminRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        categories = Category.objects.all().order_by('name')
        return render(request, 'products/product_form.html', {'categories': categories})
    
    def post(self, request):
        # Create new product
        product = Product.objects.create(
            name=request.POST.get('name'),
            code=request.POST.get('code'),
            category_id=request.POST.get('category'),
            is_liquid=request.POST.get('is_liquid') == 'on',
            is_active=request.POST.get('is_active') == 'on',
            unit_size=request.POST.get('unit_size'),
            created_by=request.user
        )
        
        # Render only the table partial
        response = render(
            request,
            'products/partials/product_table.html',
            {'products': Product.objects.all().order_by('-created_at')}
        )
        
        # Add HX-Trigger header with additional cleanup triggers
        response['HX-Trigger'] = json.dumps({
            'closeModal': True,
            'showMessage': 'Product created successfully'
        })
        
        return response

class ProductEditFormView(LoginRequiredMixin, AdminRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, product_id):
        product = Product.objects.get(id=product_id)
        categories = Category.objects.all().order_by('name')
        return render(request, 'products/product_edit_form.html', {
            'product': product,
            'categories': categories
        })

class ProductEditView(LoginRequiredMixin, AdminRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def put(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            
            # Parse the PUT data
            body = request.body.decode('utf-8')
            if request.content_type == 'application/json':
                data = json.loads(body)
            else:
                # Parse form data
                data = parse_qs(body)
                # Convert from lists to single values
                data = {k: v[0] for k, v in data.items()}
            
            # Update product fields
            product.name = data['name']
            product.code = data['code']
            product.category_id = data['category']
            product.is_liquid = data.get('is_liquid') == 'on'
            product.is_active = data.get('is_active') == 'on'
            product.unit_size = data['unit_size']
            product.updated_by = request.user
            product.save()
            
            # Render only the table partial
            response = render(
                request,
                'products/partials/product_table.html',
                {'products': Product.objects.all().order_by('-created_at')}
            )
            
            # Add HX-Trigger header
            response['HX-Trigger'] = 'closeModal'
            
            return response
            
        except Product.DoesNotExist:
            return HttpResponseBadRequest('Product not found')
        except Exception as e:
            return HttpResponseBadRequest(str(e))

class PricePlanListView(LoginRequiredMixin, TemplateView):
    template_name = "products/price_plan_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['price_plans'] = PricePlan.objects.all().order_by('-created_at')
        context['sellers'] = Seller.objects.all().order_by('first_name')
        return context

class PricePlanCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            # Debug logging
            logger.info("Received POST request for price plan creation")
            logger.info(f"POST data: {request.POST}")
            logger.info(f"Files: {request.FILES}")
            print(request.POST)
            print(request.FILES)

            # Validate required fields
            required_fields = ['name', 'valid_from', 'valid_to']
            for field in required_fields:
                if not request.POST.get(field):
                    return HttpResponseBadRequest(f"Missing required field: {field}")

            if 'excel_file' not in request.FILES:
                return HttpResponseBadRequest("Excel file is required")

            # Create the price plan
            price_plan = PricePlan.objects.create(
                name=request.POST.get('name'),
                valid_from=request.POST.get('valid_from'),
                valid_to=request.POST.get('valid_to'),
                is_general=request.POST.get('is_general') == 'on',
                seller_id=request.POST.get('seller') if request.POST.get('seller') else None,
                excel_file=request.FILES['excel_file'],
                created_by=request.user
            )
            
            logger.info(f"Created price plan with ID: {price_plan.id}")

            # Process the Excel file
            success = process_price_plan_excel(price_plan)
            if not success:
                logger.error(f"Failed to process Excel file for price plan {price_plan.id}")
                price_plan.delete()
                return HttpResponseBadRequest("Failed to process Excel file. Please check the format and try again.")
            
            logger.info(f"Successfully processed Excel file for price plan {price_plan.id}")

            response = render(
                request,
                'products/partials/price_plan_table.html',
                {'price_plans': PricePlan.objects.all().order_by('-created_at')}
            )
            
            # Add both HX-Trigger headers
            response['HX-Trigger'] = json.dumps({
                'closeModal': True,
                'showMessage': 'Price Plan created successfully'
            })
            
            return response

        except Exception as e:
            logger.error(f"Error creating price plan: {str(e)}", exc_info=True)
            return HttpResponseBadRequest(str(e))

class PricePlanEditFormView(LoginRequiredMixin, View):
    def get(self, request, price_plan_id):
        price_plan = PricePlan.objects.get(id=price_plan_id)
        sellers = Seller.objects.all().order_by('first_name')
        return render(request, 'products/price_plan_edit_form.html', {
            'price_plan': price_plan,
            'sellers': sellers
        })

class PricePlanEditView(LoginRequiredMixin, View):
    def post(self, request, price_plan_id):
        # Handle PUT requests sent as POST
        if request.POST.get('_method') == 'PUT':
            return self.put(request, price_plan_id)
        return HttpResponseBadRequest('Method not allowed')

    def put(self, request, price_plan_id):
        try:
            logger.info("Received PUT request for price plan edit")
            
            price_plan = PricePlan.objects.get(id=price_plan_id)
            
            # Get the form data
            name = request.POST.get('name')
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            is_general = request.POST.get('is_general') == 'on'
            seller_id = request.POST.get('seller')
            
            logger.info(f"Form data - name: {name}, valid_from: {valid_from}, valid_to: {valid_to}")
            
            # Validate required fields
            if not name or not valid_from or not valid_to:
                missing_fields = []
                if not name: missing_fields.append('name')
                if not valid_from: missing_fields.append('valid_from')
                if not valid_to: missing_fields.append('valid_to')
                return HttpResponseBadRequest(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Update price plan fields
            price_plan.name = name
            price_plan.valid_from = valid_from
            price_plan.valid_to = valid_to
            price_plan.is_general = is_general
            price_plan.seller_id = seller_id if not is_general and seller_id else None
            
            # Handle file upload if present
            if request.FILES.get('excel_file'):
                # Save the file first
                old_file = price_plan.excel_file
                price_plan.excel_file = request.FILES['excel_file']
                price_plan.save()
                
                try:
                    # Process the new Excel file
                    success = process_price_plan_excel(price_plan)
                    if not success:
                        # Restore the old file if processing fails
                        price_plan.excel_file = old_file
                        price_plan.save()
                        return HttpResponseBadRequest("Failed to process Excel file. Please check the format and try again.")
                except Exception as e:
                    # Restore the old file if there's an error
                    price_plan.excel_file = old_file
                    price_plan.save()
                    logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
                    return HttpResponseBadRequest(f"Error processing Excel file: {str(e)}")
            
            price_plan.updated_by = request.user
            price_plan.save()
            
            response = render(
                request,
                'products/partials/price_plan_table.html',
                {'price_plans': PricePlan.objects.all().order_by('-created_at')}
            )
            
            # Add HX-Trigger headers with proper JSON formatting
            response['HX-Trigger'] = json.dumps({
                'closeModal': True,
                'showMessage': 'Price Plan updated successfully'
            })
            
            return response

        except PricePlan.DoesNotExist:
            return HttpResponseBadRequest('Price Plan not found')
        except Exception as e:
            logger.error(f"Error updating price plan: {str(e)}", exc_info=True)
            return HttpResponseBadRequest(str(e))

def download_price_plan_template(request):
    # Create a new Excel workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add headers
    headers = ['product_code', 'price']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Add some sample data
    sample_data = [
        ['PROD001', 10.99],
        ['PROD002', 15.50],
    ]
    for row, data in enumerate(sample_data, start=1):
        for col, value in enumerate(data):
            worksheet.write(row, col, value)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=price_plan_template.xlsx'
    return response

class PricePlanPricesView(LoginRequiredMixin, View):
    def get(self, request, price_plan_id):
        try:
            price_plan = PricePlan.objects.get(id=price_plan_id)
            product_prices = ProductPrice.objects.filter(price_plan=price_plan).select_related('product')
            
            return render(request, 'products/price_plan_prices.html', {
                'price_plan': price_plan,
                'product_prices': product_prices
            })
        except PricePlan.DoesNotExist:
            return HttpResponseBadRequest('Price Plan not found')

class PricePlanUpdatePriceView(LoginRequiredMixin, View):
    def put(self, request, price_plan_id, price_id):
        try:
            body = request.body.decode('utf-8')
            data = parse_qs(body)
            new_price = float(data.get('value', ['0'])[0])
            
            price = ProductPrice.objects.get(id=price_id, price_plan_id=price_plan_id)
            price.price = new_price
            price.save()
            
            return render(request, 'products/partials/price_cell.html', {'price': price})
        except (ProductPrice.DoesNotExist, ValueError) as e:
            return HttpResponseBadRequest(str(e))

class PricePlanDeletePriceView(LoginRequiredMixin, View):
    def delete(self, request, price_plan_id, price_id):
        try:
            price = ProductPrice.objects.get(id=price_id, price_plan_id=price_plan_id)
            price.delete()
            return HttpResponse('')
        except ProductPrice.DoesNotExist:
            return HttpResponseBadRequest('Price not found')

class PricePlanAddPriceView(LoginRequiredMixin, View):
    def get(self, request, price_plan_id):
        try:
            price_plan = PricePlan.objects.get(id=price_plan_id)
            # Get products that don't have prices in this plan
            existing_product_ids = ProductPrice.objects.filter(price_plan=price_plan).values_list('product_id', flat=True)
            available_products = Product.objects.exclude(id__in=existing_product_ids)
            
            return render(request, 'products/partials/add_price_form.html', {
                'price_plan': price_plan,
                'products': available_products
            })
        except PricePlan.DoesNotExist:
            return HttpResponseBadRequest('Price Plan not found')
    
    def post(self, request, price_plan_id):
        try:
            price_plan = PricePlan.objects.get(id=price_plan_id)
            product_id = request.POST.get('product')
            price = request.POST.get('price')
            
            if not product_id or not price:
                return HttpResponseBadRequest('Product and price are required')
            
            product = Product.objects.get(id=product_id)
            product_price = ProductPrice.objects.create(
                price_plan=price_plan,
                product=product,
                price=float(price)
            )
            
            return render(request, 'products/partials/price_row.html', {'price': product_price})
            
        except (PricePlan.DoesNotExist, Product.DoesNotExist, ValueError) as e:
            return HttpResponseBadRequest(str(e))
