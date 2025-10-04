from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Category, Product, Order, OrderItem
import razorpay

# Flag to toggle Razorpay integration
USE_RAZORPAY = False  # Set True when you have real Razorpay keys

# Only initialize Razorpay client if using Razorpay
if USE_RAZORPAY:
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'categories': categories})


def products_by_category(request, category_id):
    products = Product.objects.filter(category_id=category_id)
    return render(request, 'store/products.html', {'products': products})


@login_required
def cart(request):
    order, _ = Order.objects.get_or_create(user=request.user, complete=False)
    return render(request, 'store/cart.html', {'order': order})


@login_required
def add_to_cart(request, product_id):
    order, _ = Order.objects.get_or_create(user=request.user, complete=False)
    product = Product.objects.get(id=product_id)
    item, created = OrderItem.objects.get_or_create(order=order, product=product)
    if not created:
        item.quantity += 1
    item.save()
    return redirect('cart')


@login_required
def checkout(request):
    order, _ = Order.objects.get_or_create(user=request.user, complete=False)

    payment_data = None
    if USE_RAZORPAY:
        amount = int(order.grand_total * 100)  # paise
        payment_data = client.order.create({
            'amount': amount,
            'currency': 'INR',
            'payment_capture': '1',
            'notes': {'django_order_id': str(order.id)}
        })

    return render(request, 'store/checkout.html', {
        'order': order,
        'payment': payment_data,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID if USE_RAZORPAY else "",
        'USE_RAZORPAY': USE_RAZORPAY
    })


@login_required
def payment_success(request):
    order_id = request.GET.get('order_id')
    razorpay_order_id = request.GET.get('razorpay_order_id')
    razorpay_payment_id = request.GET.get('razorpay_payment_id')

    if not order_id:
        return HttpResponse("No order ID provided.", status=400)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Mark order as paid
    order.complete = True
    order.status = 'Paid'
    order.razorpay_payment_id = razorpay_payment_id or "test_payment_id"
    order.save()

    return render(request, 'store/payment_success.html', {'order': order})



@login_required
def generate_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template_path = 'store/invoice.html'
    context = {'order': order}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    html = render_to_string(template_path, context)
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/invoice.html', {'order': order})

@login_required
def increase_quantity(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user, order__complete=False)
    item.quantity += 1
    item.save()
    return redirect('cart')


@login_required
def decrease_quantity(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user, order__complete=False)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()  # Remove item if quantity reaches 0
    return redirect('cart')
