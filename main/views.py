import json
import logging
import unittest
from datetime import date

import django
import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.handlers import exception
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseNotFound
from django.urls import reverse
from xlwt.Bitmap import ObjBmpRecord

from account.decorators import *
from main.models import *
from .extra_validation import deactivated_suppliers, checkStatus, getProductUnit, set_user_signatures, \
    check_user_signatures, check_manager_signatures
from .serializers import *

logger = logging.getLogger('django')


# REQUEST CRUD
@allowed_users(allowed_roles=['user'])
@login_required(login_url='account:login')
def new_request(request):
    branches = PrisonBranch.objects.filter(prison=Prison.objects.get(deputy=request.user))
    products = Product.objects.all()
    suppliers = Supplier.objects.all().order_by('company_name')
    brands = Brand.objects.all()
    categories_nr = Category.objects.all()
    paginator = Paginator(products, 21)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    context = {'products': products,
               'page_obj': page_obj,
               'suppliers': suppliers,
               'categories': categories_nr,
               'brands': brands,
               'prisonbranches': branches
               }
    return render(request, 'main/user/new_request.html', context)


@allowed_users(allowed_roles=['user'])
@login_required(login_url='account:login')
def review_request(request):
    if request.method == 'POST':
        user = UserProfile.objects.get(user=request.user)
        prison = Prison.objects.get(deputy=request.user)
        branch = PrisonBranch.objects.get(name=list(json.loads(request.body).keys())[0])
        request_n = Request.objects.create(user=request.user, prison=prison, branch=branch)
        request_n.number = get_request_id(prison, request_n)
        request_n.save()

        for order in list(json.loads(request.body).values())[0].values():
            brand = Brand.objects.get(company_name=order['product_brand'])
            supplier = Supplier.objects.get(company_name=order['product_supplier'])
            product = Product.objects.get(id=order['id'])
            Order.objects.create(request=request_n,
                                 supplier=supplier,
                                 brand=brand,
                                 product=product,
                                 quantity=order['product_quantity'],
                                 price=order['product_price'] if order['product_price'] != '' else 0,
                                 price_2m=order['product_2month_price'] if order['product_2month_price'] != '' else 0
                                 )

        submitted_request = {'number': request_n.number, 'status': request_n.request_status,
                             'shipping_status': request_n.shipping_status,
                             'request_datetime': request_n.get_created_date}
        user_profile = {'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone_number': user.phone_number, 'national_id': user.national_id, 'email': request.user.email}
        prison_profile = {'id': prison.id, 'name': prison.name, 'address': branch.address,
                          'phone_number': branch.phone_number, 'branch_deputy': branch.branch_deputy}
        data = {
            'userprofile': user_profile,
            'prisonprofile': prison_profile,
            'request_orders': list(list(json.loads(request.body).values())[0].values()),
            'request': submitted_request
        }
        return JsonResponse(data, safe=False)


@login_required(login_url='account:login')
@allowed_users(['user', 'ceo', 'commercial_manager'])
def requests(request):
    if request.user.groups.all()[0].name == 'user':
        requests_r = Request.objects.filter(user__email__exact=request.user.email).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'ceo':
        requests_r = Request.objects.filter(shipping_status=ShippingStatus.requested,
                                            request_status=Status.ceo_review).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'commercial_manager':
        requests_r = Request.objects.filter(request_status=Status.cm_review).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'commercial_expert':
        requests_r = Request.objects.filter(request_status=Status.ce_review).order_by('-created_date')

    context = {
        'requests_r': requests_r
    }
    return render(request, 'main/user/requests.html', context)


@login_required(login_url='account:login')
@allowed_users(['ceo', 'commercial_manager', 'commercial_expert'])
def declined_request(request):
    if request.user.groups.all()[0].name == 'ceo':
        requests_r = Request.objects.filter(request_status=Status.ceo_dreview).order_by(
            '-created_date') | Request.objects.filter(request_status=Status.cm_dreview).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'commercial_manager':
        requests_r = Request.objects.filter(request_status=Status.cm_dreview).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'commercial_expert':
        requests_r = Request.objects.filter(request_status=Status.cm_dreview, expert=request.user).order_by(
            '-created_date')

    context = {
        'requests_r': requests_r
    }
    return render(request, 'main/user/requests.html', context)


@login_required(login_url='account:login')
@allowed_users(['ceo', 'commercial_expert', 'commercial_manager'])
def finalized_requests(request):
    if request.user.groups.all()[0].name == 'commercial_expert':
        requests_r = Request.objects.filter(shipping_status=ShippingStatus.requested, request_status=Status.ceo_review,
                                            expert=request.user).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'commercial_manager':
        finalized_r = Request.objects.filter(shipping_status=ShippingStatus.requested,
                                             request_status=Status.ceo_review).order_by('-created_date')
        requests_r = []
        for request_r in finalized_r:
            if check_manager_signatures(request_r.user_signatures):
                requests_r.append(request_r)

    context = {
        'requests_r': requests_r
    }
    return render(request, 'main/user/requests.html', context)


@login_required(login_url='account:login')
@allowed_users(['ceo', 'commercial_expert', 'commercial_manager'])
def completed_requests(request):
    if request.user.groups.all()[0].name == 'commercial_expert':
        requests_r = Request.objects.filter(shipping_status=ShippingStatus.supplier,
                                            request_status=Status.completed, expert=request.user).order_by(
            '-created_date')

    elif request.user.groups.all()[0].name == 'commercial_manager':
        requests_r = Request.objects.filter(shipping_status=ShippingStatus.supplier,
                                            request_status=Status.completed).order_by('-created_date')
    elif request.user.groups.all()[0].name == 'ceo':
        requests_r = Request.objects.filter(shipping_status=ShippingStatus.supplier,
                                            request_status=Status.completed).order_by('-created_date')

    context = {
        'requests_r': requests_r
    }
    return render(request, 'main/user/requests.html', context)


@login_required(login_url='account:login')
@allowed_users(['ceo'])
def reviewing_requests(request):
    requests_r = Request.objects.filter(shipping_status=ShippingStatus.requested,
                                        request_status=Status.cm_review).order_by(
        '-created_date') | Request.objects.filter(shipping_status=ShippingStatus.requested,
                                                  request_status=Status.ce_review).order_by('-created_date')
    context = {
        'requests_r': requests_r
    }
    return render(request, 'main/user/requests.html', context)


@login_required(login_url='account:login')
@allowed_users(['ceo', 'commercial_expert', 'commercial_manager'])
def accept_request(request, pk):
    if request.method == "POST":
        request_or = Request.objects.get(number=pk)
        if request.user.groups.all()[0].name == 'commercial_manager':
            request_or.request_status = Status.ceo_review
            request_or.shipping_status = ShippingStatus.requested
            request_or.user_signatures = set_user_signatures(request.user, request_or.user_signatures)
            request_or.save()
            return redirect('main:requests')
        elif request.user.groups.all()[0].name == 'commercial_expert':
            request_or.request_status = Status.cm_review
            request_or.shipping_status = ShippingStatus.requested
            request_or.user_signatures = set_user_signatures(request.user, request_or.user_signatures)
            request_or.save()
            return redirect('main:expert_request')
        elif request.user.groups.all()[0].name == 'ceo':
            if check_user_signatures(request_or.user_signatures) is False:
                request_or.request_status = Status.cm_review
                request_or.shipping_status = ShippingStatus.requested
                request_or.save()
                return redirect('main:requests')
            else:
                request_or.request_status = Status.completed
                request_or.shipping_status = ShippingStatus.supplier
                request_or.user_signatures = set_user_signatures(request.user, request_or.user_signatures)
                request_or.save()
                return redirect('main:completed_request')


@login_required(login_url='account:login')
@allowed_users(['ceo', 'commercial_manager'])
def decline_request(request, pk):
    if request.method == "POST":
        if request.user.groups.all()[0].name == 'ceo':
            request_or = Request.objects.get(number=pk)
            if check_manager_signatures(request_or.user_signatures):
                request_or.request_status = Status.cm_review
                request_or.user_signatures = init_user_signatures()
            else:
                request_or.request_status = Status.ceo_dreview
                request_or.shipping_status = ShippingStatus.declined
                request_or.expert.clear()
                request_or.user_signatures = init_user_signatures()
        elif request.user.groups.all()[0].name == 'commercial_manager':
            request_or = Request.objects.get(number=pk)
            request_or.request_status = Status.cm_dreview
            request_or.shipping_status = ShippingStatus.declined
            request_or.user_signatures = init_user_signatures()
        request_or.save()
    return redirect('main:get_request', pk)


@login_required(login_url='account:login')
@allowed_users(['ceo'])
def return_declined_request(request, pk):
    if request.method == "POST":
        if request.user.groups.all()[0].name == 'ceo':
            request_or = Request.objects.get(number=pk)
            request_or.request_status = Status.ceo_review
            request_or.shipping_status = ShippingStatus.requested
            request_or.user_signatures = init_user_signatures()
            request_or.save()
            return redirect('main:get_request', pk)


@login_required(login_url='account:login')
@allowed_users(['user', 'ceo', 'commercial_manager', 'commercial_expert'])
def get_request(request, pk):
    context = {}
    request_r = None
    orders_r = None
    signed_r = False
    categories_r = None
    if request.user.groups.all()[0].name == 'commercial_manager':

        request_r = Request.objects.get(number=pk)
        orders_r = Order.objects.filter(request=request_r)
        if check_user_signatures(request_r.user_signatures) is True:
            signed_r = True

    elif request.user.groups.all()[0].name == 'commercial_expert':
        request_r = Request.objects.get(number=pk)
        if request_r.request_status == Status.cm_review or request_r.request_status == Status.ceo_review:
            if not check_user_signatures(request_r.user_signatures):
                return Http404()
        category = Category.objects.filter(user_expert=request.user)
        orders_r = Order.objects.filter(product__category__user_expert=request.user, request=request_r).distinct()

        if check_user_signatures(request_r.user_signatures) is True:
            signed_r = True

    elif request.user.groups.all()[0].name == 'ceo':
        request_r = Request.objects.get(number=pk)
        orders_r = Order.objects.filter(request=request_r)
        if check_user_signatures(request_r.user_signatures) is True:
            signed_r = True
    else:
        request_r = Request.objects.get(number=pk)
        orders_r = Order.objects.filter(request=request_r)

    categories_r = Order.objects.filter(request=request_r).values('product__category',
                                                                  'product__category__user_expert_id').distinct()
    tickets_r = Ticket.objects.filter(request=request_r).order_by('-created_date')
    conversations_r = []
    for ticket in tickets_r:
        conversations = Conversation.objects.filter(ticket=ticket)
        for conversation in conversations:
            conversations_r.append(conversation)

    context = {
        'conversations_r': conversations_r,
        'tickets_r': tickets_r,
        'request_r': request_r,
        'orders_r': orders_r,
        'request_user': request_r.get_user,
        'categories_r': categories_r,
        'signed_r': signed_r
    }
    return render(request, 'main/user/view_request.html', context)


def submit_request_ticket(request):
    if request.method == 'POST':
        request_number_r = json.loads(request.body).get('request_number')
        ticket_title = json.loads(request.body).get('ticket_title')
        ticket_con = json.loads(request.body).get('ticket_con')

        request_r = Request.objects.get(number=request_number_r)
        ticket_r = Ticket.objects.create(request=request_r, title=ticket_title)
        Conversation.objects.create(ticket=ticket_r, comment_user=request.user, comment=ticket_con)
        return JsonResponse({}, safe=False)


def submit_request_conversation(request):
    user_email = json.loads(request.body).get('user_email')
    conversation_id = json.loads(request.body).get('conversation_id')
    reply = json.loads(request.body).get('reply')
    conversation = Conversation.objects.get(id=conversation_id)
    user = User.objects.get(email=user_email)
    if reply != '': conversation.reply = reply
    if user_email != '': conversation.reply_user = user
    conversation.save()
    return JsonResponse({}, safe=False)


@login_required(login_url='account:login')
@allowed_users(['commercial_expert', 'commercial_manager'])
def expert_requests(request):
    if request.user.groups.all()[0].name == 'commercial_expert':
        requests_r = Request.objects.filter(expert=request.user, request_status=Status.ce_review).order_by(
            '-created_date')
    else:
        requests_r = Request.objects.filter(request_status=Status.ce_review).order_by(
            '-created_date')
    context = {
        'requests_r': requests_r
    }
    return render(request, 'main/user/requests.html', context)


def supplier_orders(request, pk):
    request_r = Request.objects.get(number=pk)
    if request.user.groups.all()[0].name == 'commercial_expert':
        if request_r.request_status == Status.cm_review or request_r.request_status == Status.ceo_review:
            return Http404()
        supplier_orders_r = Order.objects.filter(request=request_r,
                                                 product__category__user_expert=request.user).values_list(
            'supplier_id', 'supplier__company_name').distinct()

    else:
        supplier_orders_r = Order.objects.filter(request=request_r).values_list('supplier_id',
                                                                                'supplier__company_name').distinct()

    context = {
        'supplier_orders': supplier_orders_r,
        'request_r': request_r
    }
    return render(request, 'main/user/supplier_orders.html', context)


@login_required(login_url='account:login')
def get_rs_orders_factor(request, pk, ord):
    request_r = Request.objects.get(number=pk)
    # if request_r.request_status != Status.ce_review and request.user.groups.all()[0].name == 'user':
    #     return Http404()
    supplier_r = Supplier.objects.get(id=ord)
    try:
        deliver_date = DeliverDate.objects.get(request=request_r, supplier=supplier_r)
    except DeliverDate.DoesNotExist:
        messages.error(request, f"امکان مشاهده رسید تحویل کالا برای این تامین کننده وجود ندارد")
        return redirect(reverse('main:supplier_orders', kwargs={'pk': pk}))
    orders_r = Order.objects.filter(request__number=pk, supplier_id=ord)

    context = {
        'orders_r': orders_r,
        'request_r': request_r,
        'supplier_r': supplier_r,
        'deliver_date': deliver_date
    }
    return render(request, 'main/user/view_factor.html', context)


@login_required(login_url='account:login')
@allowed_users(['user'])
def edit_get_rs_orders_factor(request, pk, ord):
    request_r = Request.objects.get(number=pk)
    # if request_r.request_status != Status.ce_review and request.user.groups.all()[0].name == 'user':
    #     return Http404()
    supplier_r = Supplier.objects.get(id=ord)
    deliver_date = DeliverDate.objects.get(request=request_r, supplier=supplier_r)
    if deliver_date.date > date2jalali(datetime.now()):
        messages.error(request, f"امکان ویرایش رسید تحویل کالا فقط در تاریخ موعد آن دردسترس است")
        return redirect(reverse('main:get_rs_orders_factor', kwargs={'pk': pk, 'ord': ord}))
    orders_r = Order.objects.filter(request__number=pk, supplier_id=ord)

    context = {
        'orders_r': orders_r,
        'request_r': request_r,
        'supplier_r': supplier_r,
        'deliver_date': deliver_date
    }
    return render(request, 'main/user/edit_factor.html', context)


@login_required(login_url='account:login')
@allowed_users(['user'])
def submit_delivered_factor(request, req, sup):
    # request_number = json.loads(request.body).get('request_number')
    # supplier_id = json.loads(request.body).get('supplier_id')
    request_r = Request.objects.get(number=req)
    supplier_r = Supplier.objects.get(id=sup)
    deliver_date = DeliverDate.objects.get(request=request_r, supplier=supplier_r)

    if deliver_date.date > date2jalali(datetime.now()):
        messages.error(request, f"امکان ثبت رسید تحویل کالا فقط در تاریخ موعد آن دردسترس است")
        return redirect(reverse('main:get_rs_orders_factor', kwargs={'pk': req, 'ord': sup}))
    orders = Order.objects.filter(request=request_r, supplier=supplier_r, delivered_quantity=0)
    for order in orders:
        order.delivered_quantity = order.quantity

    Order.objects.bulk_update(orders, ['delivered_quantity'])
    deliver_date.status = 1
    deliver_date.save()
    return redirect(reverse('main:get_rs_orders_factor', kwargs={'pk': req, 'ord': sup}))
    # return JsonResponse({}, safe=False)


@login_required(login_url='account:login')
@allowed_users(['commercial_expert', 'commercial_manager', 'ceo'])
def get_rs_orders(request, pk, ord):
    request_r = Request.objects.get(number=pk)
    if request_r.request_status != Status.ce_review and request.user.groups.all()[0].name == 'user':
        return Http404()
    supplier_r = Supplier.objects.get(id=ord)
    final_list = []
    orders_r = Order.objects.filter(request__number=pk, supplier_id=ord)
    for order in orders_r:
        price = SupplierProduct.objects.filter(supplier=supplier_r, brand=order.brand, product=order.product).order_by(
            '-created_date')[0].price
        print(price)
        order.price = price
    try:
        deliver_date = DeliverDate.objects.get(supplier=supplier_r, request=request_r).get_deliver_date
    except DeliverDate.DoesNotExist:
        deliver_date = None
    context = {
        'orders_r': orders_r,
        'request_r': request_r,
        'supplier_r': supplier_r,
        'deliver_date': deliver_date
    }
    return render(request, 'main/user/view_orders.html', context)


def change_request_cexpert(request):
    category_ce = json.loads(request.body).get('ce_category_email')
    request_number = json.loads(request.body).get('request_number')

    request_r = Request.objects.get(number=request_number)
    expert = User.objects.get(id=category_ce)
    request_r.expert.add(expert)
    request_r.user_signatures = init_user_signatures()
    request_r.request_status = Status.ce_review
    request_r.save()

    return JsonResponse({}, safe=False)


@login_required(login_url='account:login')
@allowed_users(['user', 'ceo', 'commercial_expert', 'commercial_manager'])
def update_request(request, pk):
    orders_r = None
    request_r = Request.objects.get(number=pk)
    if request.user.groups.all()[0].name == 'user' and request_r.request_status != Status.ceo_review:
        return Http404()
    if request.user.groups.all()[0].name == 'commercial_expert':
        category = Category.objects.filter(user_expert=request.user)
        orders_r = Order.objects.filter(request=request_r, product__category__user_expert=request.user).distinct()
    else:
        orders_r = Order.objects.filter(request=request_r)

    products = Product.objects.all()
    brands = Brand.objects.all()
    suppliers = Supplier.objects.all().order_by('company_name')
    categories_r = Category.objects.all()
    paginator = Paginator(products, 21)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    context = {

        'request_r': request_r,
        'orders_r': orders_r,
        'request_user': request_r.get_user,
        'products': products,
        'suppliers': suppliers,
        'page_obj': page_obj,
        'brands': brands,
        'categories': categories_r
    }
    return render(request, 'main/user/edit_request.html', context)


def get_request_id(prison, request_n):
    return f"{date2jalali(request_n.created_date).strftime('%Y')}{date2jalali(request_n.created_date).strftime('%m')}{prison.province.code}{request_n.id}"


def add_product_to_request(request):
    brand_r = None
    supplier_r = None
    if request.method == 'POST':
        request_id = json.loads(request.body).get('request_id')
        product_id = json.loads(request.body).get('product_id')
        product_supplier = json.loads(request.body).get('product_supplier')
        product_brand = json.loads(request.body).get('product_brand')
        product_quantity = json.loads(request.body).get('product_quantity')
        product_2m_price = json.loads(request.body).get('product_2month_price')
        product_price = json.loads(request.body).get('product_price')
        suppliers = [supplier['company_name'] for supplier in
                     Supplier.objects.all().values()]
        request_r = Request.objects.get(number=request_id)
        if product_brand != '': brand_r = Brand.objects.get(company_name=product_brand)
        if product_supplier != '': supplier_r = Supplier.objects.get(company_name=product_supplier)
        product_r = Product.objects.get(id=product_id)
        order = Order.objects.create(request=request_r, supplier=supplier_r, brand=brand_r, quantity=product_quantity,
                                     product=product_r,
                                     price=product_price if product_price != '' else 0,
                                     price_2m=product_2m_price if product_2m_price != '' else 0)
        brands = [brand['company_name'] for brand in
                  Category.objects.get(name=product_r.category.name).suppliers.values()]
        print(brands)
        data = {
            'order': order.get_dict(),
            'brands_r': brands,
            'suppliers_r': suppliers
        }
        return JsonResponse(data, safe=False)


def remove_order_request(request):
    if request.method == 'DELETE':
        order_id = json.loads(request.body).get('order_id')
        Order.objects.get(id=order_id).delete()
        data = {
            'message': 'سفارش شما از این درخواست با موفقیت حذف شد'
        }
        return JsonResponse(data, safe=False)


def update_order_request(request):
    if request.method == 'PUT':
        order_id = json.loads(request.body).get('order_id')
        supplier = json.loads(request.body).get('supplier')
        brand = json.loads(request.body).get('brand')
        quantity = json.loads(request.body).get('quantity')
        price = json.loads(request.body).get('price')
        price_2m = json.loads(request.body).get('price_2m')
        order = Order.objects.get(id=order_id)
        if supplier != '' and order.supplier.company_name != supplier: order.supplier = Supplier.objects.get(
            company_name=supplier)
        if Brand != 0 and order.brand.company_name != brand: order.brand = Brand.objects.get(
            company_name=brand)
        if quantity != '' and order.quantity != quantity: order.quantity = quantity
        if price != '' and order.price != price: order.price = price
        if price_2m != '' and order.price_2m != price_2m: order.price_2m = price_2m
        order.save()
        data = {
            'message': 'سفارش شما با موفقیت ویرایش شد'
        }
        return JsonResponse(data, safe=False)


# USER CRUD
@login_required(login_url='account:login')
@allowed_users(allowed_roles=['administrator'])
def add_user(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if request.POST.get("password1") == request.POST.get("password2"):
            password = request.POST.get("password1")
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        national_id = request.POST.get('national_id')
        phone_number = request.POST.get('phone_number')
        postal_code = request.POST.get('postal_code')
        province = request.POST.get('province-selector')
        city = request.POST.get('city-selector')
        address = request.POST.get('address')
        role = request.POST.get('role-selector')

        user = User.objects.create_user(email=email, password=password, is_active=True, is_admin=False,
                                        is_staff=True)
        group = Group.objects.get(name=role)
        group.user_set.add(user)
        print(user)
        UserProfile.objects.create(user=user,
                                   first_name=first_name,
                                   last_name=last_name,
                                   national_id=national_id,
                                   phone_number=phone_number,
                                   postal_code=postal_code,
                                   province=province,
                                   address=address,
                                   city=city)
        messages.success(request, f"ثبت نام با موفقیت انجام شد")
        return redirect('main:users')
    if request.method == "GET":
        return render(request, 'main/admin/register_user.html', {})


@login_required(login_url='account:login')
@allowed_users(['administrator'])
def update_user(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.get(email=email)
        userprofile = UserProfile.objects.get(user=user.id)
        if request.POST.get("password1") is not None:
            if request.POST.get("password1") == request.POST.get("password2"):
                user.password = make_password(request.POST.get("password1"), hasher='pbkdf2_sha256')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        national_id = request.POST.get('national_id')
        phone_number = request.POST.get('phone_number')
        postal_code = request.POST.get('postal_code')
        province = request.POST.get('province-selector')
        city = request.POST.get('city-selector')
        address = request.POST.get('address')
        role = request.POST.get('role-selector')

        if role is not None:
            groups = Group.objects.get(name=user.groups.all()[0])
            groups.user_set.remove(user)
            groups = Group.objects.get(name=role)
            groups.user_set.add(user)

        if first_name != '': userprofile.first_name = first_name
        if last_name != '': userprofile.last_name = last_name
        if national_id != '': userprofile.national_id = national_id
        if phone_number != '': userprofile.phone_number = phone_number
        if postal_code != '': userprofile.postal_code = postal_code
        if province != '': userprofile.province = province
        if city != '': userprofile.city = city
        if address != '': userprofile.address = address
        user.save()
        userprofile.save()
        logger.info(
            f"SESSION:[USER: {request.user}, ROLE: {request.user.groups.all()[0].name}, LAST_LOGIN:{request.user.last_login}, ACTION: 'EDITING USER'], CHANGES ON:[ EMAIL: {email}, NID: {userprofile.national_id}, LAST_LOGIN: {user.last_login}]  ")
        messages.success(request, 'اطلاعات کاربر مورد نظر ویرایش و با موفقیت ثبت شد')
        return redirect('main:users')


@login_required(login_url='account:login')
@allowed_users(['administrator'])
def delete_user(request):
    user_id = request.GET.get('id')
    User.objects.get(id=user_id).delete()
    data = {
        'deleted': True
    }
    return JsonResponse(data)


@login_required(login_url='account:login')
@allowed_users(['administrator'])
def get_user(request, pk):
    user = User.objects.get(id=pk)
    userprofile = UserProfile.objects.get(user=user)
    context = {
        'user_e': user,
        'userprofile_e': userprofile
    }
    return render(request, 'main/admin/edit_user.html', context)


@login_required(login_url='account:login')
@allowed_users(['administrator'])
def get_users(request):
    users = User.objects.all().order_by('-timestamp')
    groups = Group.objects.all()
    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)

    context = {'users': users,
               'page_obj': page_obj,
               'groups': groups,
               }
    return render(request, "main/admin/users.html", context)


@login_required(login_url='account:login')
@allowed_users(['administrator'])
def search_users(request):
    if request.method == 'POST':
        search_name = json.loads(request.body).get('nameText')
        search_category = json.loads(request.body).get('categoryValue')

        if search_name is None:
            users = User.objects.filter(
                groups__name__contains=search_category).order_by('-timestamp')
        elif search_category is None:
            users = User.objects.filter(userprofile__first_name__icontains=search_name).order_by(
                '-timestamp') | User.objects.filter(
                userprofile__last_name__icontains=search_name).order_by('-timestamp')
        else:
            users = (User.objects.filter(userprofile__first_name__icontains=search_name).order_by(
                '-timestamp') & User.objects.filter(
                groups__name__contains=search_category)).order_by('-timestamp') | \
                    (User.objects.filter(
                        userprofile__last_name__icontains=search_name).order_by('-timestamp') & User.objects.filter(
                        groups__name=search_category)).order_by('-timestamp')
    data = []
    for user in users:
        userprofile = UserProfile.objects.get(user=user)
        data.append({'id': user.id, 'user_email': user.email, 'first_name': userprofile.first_name,
                     'last_name': userprofile.last_name,
                     'phone_number': userprofile.phone_number, 'province': userprofile.province,
                     'city': userprofile.city, 'group': f'{user.groups.all()[0]}'})
    return JsonResponse({'data': data, '': ''}, safe=False)


# Supplier CRUD
@allowed_users(['site_admin'])
@login_required(login_url='account:login')
def get_suppliers(request):
    suppliers = Supplier.objects.all()
    paginator = Paginator(suppliers, 21)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)

    context = {'suppliers': suppliers,
               'page_obj': page_obj,
               }
    return render(request, "main/admin/supplier/suppliers.html", context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def delete_supplier(request):
    supplier_id = request.GET.get('id')
    Supplier.objects.get(id=supplier_id).delete()
    data = {
        'deleted': True
    }
    return JsonResponse(data)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def search_suppliers(request):
    if request.method == 'POST':
        search_name = json.loads(request.body).get('nameText')

        suppliers = Supplier.objects.filter(company_name__contains=search_name)

    data = []
    for supplier in suppliers:
        data.append({'id': supplier.id, 'name': supplier.company_name, 'province': supplier.province,
                     'fax': supplier.province, 'address': supplier.address,
                     'status': supplier.__status__(), 'margin': supplier.margin
                     })
    return JsonResponse({'data': data, '': ''}, safe=False)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def get_supplier(request, pk):
    supplier = Supplier.objects.get(id=pk)
    province = Province.objects.all()
    context = {
        'supplier_e': supplier,
        'provinces': province
    }
    return render(request, 'main/admin/supplier/edit_supplier.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def update_supplier(request):
    if request.method == "POST":
        id = request.POST.get("supplier-id")
        company_name = request.POST.get('name')
        fax = request.POST.get('fax')
        province = request.POST.get('province-selector')
        city = request.POST.get('city-selector')
        address = request.POST.get('address')
        status = request.POST.get('status-selector')
        margin = request.POST.get('margin')
        supplier = Supplier.objects.get(id=id)

        if company_name != '': supplier.company_name = company_name
        if fax != '': supplier.fax = fax
        if province != '': supplier.province = province
        if city != '': supplier.city = city
        if address != '': supplier.address = address
        if status != '': supplier.is_active = checkStatus(status)
        if margin != '': supplier.margin = margin
        supplier.save()

        logger.info(
            f"SESSION:[USER: {request.user}, ROLE: {request.user.groups.all()[0].name}, LAST_LOGIN:{request.user.last_login}, ACTION: 'EDITING SUPPLIER'], CHANGES ON:[ SUPPLIER NAME: {supplier.company_name}")
        messages.success(request, 'اطلاعات تامین کننده مورد نظر ویرایش و با موفقیت ثبت شد')
        return redirect('main:suppliers')


@login_required(login_url='account:login')
@allowed_users(allowed_roles=['site_admin'])
def add_supplier(request):
    if request.method == "POST":
        try:
            company_name = request.POST.get('company_name')
            fax = request.POST.get('fax')
            province = request.POST.get('province-selector')
            city = request.POST.get('city-selector')
            address = request.POST.get('address')
            status = request.POST.get('status-selector')
            margin = request.POST.get('margin')
            if margin == '':
                Supplier.objects.create(company_name=company_name, fax=fax, is_active=checkStatus(status),
                                        address=address,
                                        city=city, province=province, margin=0)
            else:
                Supplier.objects.create(company_name=company_name, fax=fax, is_active=checkStatus(status),
                                        address=address,
                                        city=city, province=province, margin=margin)
            messages.success(request, f"ثبت تامین کنند جدید با موفقیت انجام شد")
            return redirect('main:suppliers')
        except Exception:
            messages.success(request, f"تامین کننده مورد نظر در سیستم موجود میباشد")
            return redirect('main:suppliers')
    if request.method == "GET":
        provinces = Province.objects.all()
        return render(request, 'main/admin/supplier/register_supplier.html', {'provinces': provinces})


# Product CRUD

@allowed_users(allowed_roles=['site_admin', 'user'])
@login_required(login_url='account:login')
def search_products(request):
    if request.method == 'POST':
        search_name = json.loads(request.body).get('nameText')
        search_category = json.loads(request.body).get('categoryValue')

        if search_name is None:
            products = Product.objects.filter(
                category=search_category)
        elif search_category is None:
            products = Product.objects.filter(name__contains=search_name)
        else:
            products = Product.objects.filter(name__contains=search_name) & Product.objects.filter(
                category=search_category)

        data = []
        suppliers = Supplier.objects.all().values()
        for product in products:
            data.append({'id': product.id, 'name': product.name, 'category_id': product.category.name,
                         'product_unit': product.based_quantity, 'description': product.description,
                         'product_ordered_quantity': product.ordered_quantity,
                         'product_suppliers': {f"{supplier['id']}": supplier['company_name'] for supplier in
                                               suppliers},
                         'product_brands': {f"{brand['id']}": brand['company_name'] for brand in
                                            product.category.suppliers.values()}})
        suppliers = deactivated_suppliers()
        return JsonResponse({'products': data, 'deactivated_suppliers': suppliers}, safe=False)


@allowed_users(['site_admin', 'user'])
@login_required(login_url='account:login')
def get_products(request):
    products = Product.objects.all()
    suppliers = Brand.objects.all()
    categories = Category.objects.all()
    o_suppliers = Supplier.objects.all()
    paginator = Paginator(products, 21)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)

    context = {'products': products,
               'page_obj': page_obj,
               'brands': suppliers,
               'categories': categories,
               'suppliers': o_suppliers
               }
    return render(request, "main/site_admin/products.html", context)


@allowed_users(['site_admin'])
@login_required(login_url='account:login')
def add_product(request):
    if request.method == "POST":
        name = request.POST.get('name')
        category = request.POST.get('category-selector')
        quantity_unit = request.POST.get('unit-selector')
        description = request.POST.get("description")
        product = Product.objects.create(name=name, description=description,
                                         based_quantity=getProductUnit(quantity_unit))

        category = Category.objects.get(name=category)
        category.product_set.add(product)
        messages.success(request, f"کالای جدید با موفقیت ثبت شد")
        return redirect('main:products')
    if request.method == "GET":
        categories = Category.objects.all()
        units = Unit.choices
        return render(request, 'main/site_admin/register_product.html', {'categories': categories, 'units': units})


@login_required(login_url='account:login')
@allowed_users(['site_admin', 'user'])
def get_product(request, pk):
    product = Product.objects.get(id=pk)
    categories_g = Category.objects.all()
    units = Unit.choices
    context = {
        'product_e': product, 'categories': categories_g, 'units': units
    }
    return render(request, 'main/site_admin/edit_product.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def update_product(request):
    if request.method == "POST":
        product_id = request.POST.get('product-id')
        name = request.POST.get('name')
        category = request.POST.get('category-selector')
        quantity_unit = request.POST.get('unit-selector')
        description = request.POST.get("description")
        product = Product.objects.get(id=product_id)
        if name != '': product.name = name
        if quantity_unit != '': product.based_quantity = getProductUnit(quantity_unit)
        if description != '': product.description = description
        if category != '' and category != product.category.name:
            Category.objects.get(name=product.category.name).product_set.remove(product)
            Category.objects.get(name=category).product_set.add(product)

        product.save()

        logger.info(
            f"SESSION:[USER: {request.user}, ROLE: {request.user.groups.all()[0].name}, LAST_LOGIN:{request.user.last_login}, ACTION: 'EDITING PRODUCT'], CHANGES ON:[ SUPPLIER NAME: {product.name}")
        messages.success(request, 'اطلاعات کالای مورد نظر ویرایش و با موفقیت ثبت شد')
        return redirect('main:products')


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def categories(request):
    if request.method == "POST":
        category_name = request.POST.get('name')
        category_description = request.POST.get('description')
        category_suppliers = request.POST.getlist('supplier-selector')
        sc = Category.objects.create(name=category_name, description=category_description)
        for supplier in category_suppliers:
            cp = Brand.objects.get(company_name=supplier)
            cp.category_set.add(sc)

        return redirect('main:categories')
    if request.method == 'GET':
        suppliers = Brand.objects.all()
        categories_r = Category.objects.all()
        return render(request, 'main/site_admin/categories.html', {'suppliers': suppliers, 'categories': categories_r})


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def delete_category(request):
    category_name = request.GET.get('name')
    Category.objects.get(name=category_name).delete()
    data = {
        'deleted': True
    }
    return JsonResponse(data)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def get_category(request, pk):
    category = Category.objects.get(name=pk)
    suppliers = Brand.objects.all()
    data = []
    for supplier in category.suppliers.values():
        data.append(supplier['company_name'])
    context = {
        'category_e': category, 'suppliers_c': suppliers, 'category_suppliers': data
    }
    return render(request, 'main/site_admin/edit_category.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def update_category(request):
    if request.method == "POST":
        category_name = request.POST.get('name')
        category_description = request.POST.get('description')
        category_suppliers = request.POST.getlist('supplier-selector')
        category = Category.objects.get(name=category_name)
        if category_description != '': category.description = category_description
        if category_name != '': category.name = category_name
        category_rs_data = []
        for csv in category.suppliers.values():
            category_rs_data.append(csv['company_name'])
        if len(category_suppliers) > 0:
            for cc in category_suppliers:
                if cc not in category_rs_data:
                    cp = Brand.objects.get(company_name=cc)
                    category.suppliers.add(cp)

            for value in category_rs_data:
                if value not in category_suppliers:
                    cp = Brand.objects.get(company_name=value)
                    category.suppliers.remove(cp)
        category.save()

        return redirect('main:categories')

    return redirect(request, 'main:categories', {})


# Brand


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def get_brands(request):
    brands = Brand.objects.all()
    paginator = Paginator(brands, 21)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)

    context = {'brands': brands,
               'page_obj': page_obj,
               }
    return render(request, "main/admin/brand/brands.html", context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def delete_brands(request):
    brand_id = request.GET.get('id')
    Supplier.objects.get(id=brand_id).delete()
    data = {
        'deleted': True
    }
    return JsonResponse(data)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def search_brands(request):
    if request.method == 'POST':
        search_name = json.loads(request.body).get('nameText')

        brands = Brand.objects.filter(company_name__contains=search_name)

    data = []
    for brand in brands:
        data.append({'id': brand.id, 'name': brand.company_name})
    return JsonResponse({'data': data, '': ''}, safe=False)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def get_brand(request, pk):
    brand = Brand.objects.get(id=pk)
    context = {
        'brand_e': brand,
    }
    return render(request, 'main/admin/brand/edit_brand.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def update_brand(request, pk):
    if request.method == "POST":
        brand = Brand.objects.get(id=pk)
        name = request.POST.get('name')
        if name != '': brand.company_name = name
        brand.save()

        logger.info(
            f"SESSION:[USER: {request.user}, ROLE: {request.user.groups.all()[0].name}, LAST_LOGIN:{request.user.last_login}, ACTION: 'EDITING BRAND'], CHANGES ON:[ BRAND NAME: {brand.company_name}")
        messages.success(request, 'اطلاعات برند مورد نظر ویرایش و با موفقیت ثبت شد')
        return redirect('main:brands')


@login_required(login_url='account:login')
@allowed_users(allowed_roles=['site_admin'])
def add_brand(request):
    if request.method == "POST":
        try:
            name = request.POST.get('name')
            Brand.objects.create(company_name=name)
            messages.success(request, f"ثبت برند جدید با موفقیت انجام شد")
            return redirect('main:brands')
        except Exception:
            messages.warning(request, "برند مورد نظر در سیستم موجود است")
            return redirect('main:brands')

    if request.method == "GET":
        return render(request, 'main/admin/brand/register_brand.html', {})


# Prison and PrisonBranch Crud
# PrisonBranch
@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def get_prisonbranch(request, pk):
    branch_r = PrisonBranch.objects.get(id=pk)

    context = {
        'branch': branch_r
    }

    return render(request, 'main/site_admin/prison/edit_prisonbranch.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def prisonbranches(request):
    if request.method == "POST":
        name = request.POST.get('name')
        number = request.POST.get('number')
        deputy = request.POST.get('deputy')
        address = request.POST.get('address')
        PrisonBranch.objects.create(name=name, phone_number=number, address=address, branch_deputy=deputy)
        return redirect('main:prisonbranches')

    if request.method == 'GET':
        prisonbranches_r = PrisonBranch.objects.all()
        return render(request, 'main/site_admin/prison/prisonbranches.html', {'prisonbranches': prisonbranches_r})


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def update_prisonbranch(request, pk):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone_number = request.POST.get('number')
        deputy = request.POST.get('deputy')
        address = request.POST.get('address')
        branch_r = PrisonBranch.objects.get(id=pk)
        if name != '' and name != branch_r.name:
            branch_r.name = name
        if phone_number != '' and phone_number != branch_r.phone_number:
            branch_r.phone_number = phone_number
        if address != '' and address != branch_r.address:
            branch_r.address = address
        if deputy != '' and deputy != branch_r.branch_deputy:
            branch_r.branch_deputy = deputy

        branch_r.save()
        return redirect('main:prisonbranches')


# Prison
@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def get_prison(request, pk):
    prison_r = Prison.objects.get(id=pk)
    users = User.objects.filter(groups__name='user')
    branches = PrisonBranch.objects.all()
    provinces_r = Province.objects.all()
    data = []
    for prisonbranch in prison_r.prisons.values():
        data.append(prisonbranch['name'])
    context = {
        'prison': prison_r,
        'users': users,
        'branches': branches,
        'prisonbranches': data,
        'provinces': provinces_r
    }

    return render(request, 'main/site_admin/prison/edit_prison.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def prisons(request):
    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('number')
        user = request.POST.get('user-selector')
        branches = request.POST.getlist('branch-selector')
        province_r = request.POST.get('province-selector')
        address = request.POST.get('address')
        user_r = User.objects.get(email=user)
        province = Province.objects.get(code=province_r)
        prison = Prison.objects.create(name=name, address=address, phone_number=phone, deputy=user_r, province=province)
        for branch in branches:
            pb = PrisonBranch.objects.get(id=branch)
            pb.prison_set.add(prison)

        return redirect('main:prisons')
    if request.method == 'GET':
        provinces_r = Province.objects.all()
        prisons_r = Prison.objects.all()
        branch_r = PrisonBranch.objects.all()
        users = User.objects.filter(groups__name='user')
        context = {
            'prisons': prisons_r,
            'branch_r': branch_r,
            'users': users,
            'provinces': provinces_r
        }
        return render(request, 'main/site_admin/prison/prisons.html', context)


@login_required(login_url='account:login')
@allowed_users(['site_admin'])
def update_prison(request, pk):
    if request.method == "POST":
        name = request.POST.get('name')
        address = request.POST.get('address')
        user = request.POST.get('user-selector')
        province_r = request.POST.get('province-selector')

        branches = [int(i) for i in request.POST.getlist('branch-selector')]
        prison = Prison.objects.get(id=pk)
        if name != '': prison.name = name
        if user != '': prison.deputy = User.objects.get(email=user)
        if address != '': prison.address = address
        if province_r != '':
            province = Province.objects.get(code=province_r)
            prison.province = province
        prison_rb_data = []
        for pbsv in prison.prisons.values():
            prison_rb_data.append(pbsv['id'])
        if len(branches) > 0:
            for pb in branches:
                if pb not in prison_rb_data:
                    pbba = PrisonBranch.objects.get(id=pb)
                    pbba.prison_set.add(prison)
            for value in prison_rb_data:
                if value not in branches:
                    pbbd = PrisonBranch.objects.get(id=value)
                    pbbd.prison_set.remove(prison)
        else:
            pbb = PrisonBranch.objects.all()
            for pbbg in pbb:
                pbbg.prison_set.remove(prison)
        prison.save()
        return redirect('main:prisons')
    return redirect(request, 'main:prisons', {})


def delete_prison():
    pass


# Supplier
@login_required(login_url='account:login')
@allowed_users(['commercial_manager', 'ceo', 'commercial_expert'])
def get_supplier_price(request):
    product_id = json.loads(request.body).get('product_id')
    supplier_id = json.loads(request.body).get('supplier_id')
    brand_id = json.loads(request.body).get('brand_id')
    brand = Brand.objects.get(company_name=brand_id)
    product = Product.objects.get(id=product_id)
    supplier = Supplier.objects.get(company_name=supplier_id)
    if supplier.company_name != 'بدون تامین کننده':
        supplier_products = SupplierProduct.objects.filter(product=product, supplier=supplier, brand=brand).order_by(
            '-created_date')[:5]
    else:
        supplier_products = SupplierProduct.objects.filter(product=product, brand=brand).order_by(
            '-created_date')[:5]

    data = []
    for supplier in supplier_products:
        data.append({'product_name': supplier.product.name, 'supplier_name': supplier.supplier.company_name,
                     'brand_name': supplier.brand.company_name,
                     'price': supplier.price, 'price2m': supplier.price2m,
                     'created_date': f'{supplier.get_created_time} {supplier.get_created_date}'})
    return JsonResponse({'data': data}, safe=False)


@login_required(login_url='account:login')
@allowed_users(['commercial_manager', 'ceo', 'commercial_expert'])
def add_supplier_price(request):
    product_id = json.loads(request.body).get('product_id')
    request_number = json.loads(request.body).get('request_id')
    supplier_id = json.loads(request.body).get('supplier_name')
    brand_id = json.loads(request.body).get('brand_name')
    price = json.loads(request.body).get('price')
    price2m = json.loads(request.body).get('price2m')

    product = Product.objects.get(id=product_id)
    supplier = Supplier.objects.get(company_name=supplier_id)
    brand = Brand.objects.get(company_name=brand_id)
    request_r = Request.objects.get(number=request_number)

    SupplierProduct.objects.create(request=request_r, product=product, supplier=supplier, brand=brand, price=price,
                                   price2m=price2m, created_date=datetime.now())

    data = {
        'message': 'قیمت جدید برای تامین کننده مورد نظر به همراه برند آن ثبت شد'
    }
    return JsonResponse(data, safe=False)


@login_required(login_url='account:login')
def add_sdeliver_date(request):
    request_number = json.loads(request.body).get('request_number')
    supplier_id = json.loads(request.body).get('supplier_id')
    deliver_date = json.loads(request.body).get('deliver_date')

    request_r = Request.objects.get(number=request_number)
    supplier_r = Supplier.objects.get(id=supplier_id)
    deliver_date_r = jdatetime.datetime.strptime(deliver_date, '%Y/%m/%d').togregorian()
    try:
        DeliverDate.objects.create(request=request_r, supplier=supplier_r, date=deliver_date_r)
    except IntegrityError:
        deliver_date_ec = DeliverDate.objects.get(request=request_r, supplier=supplier_r)
        deliver_date_ec.date = deliver_date_r
        deliver_date_ec.save()

    return JsonResponse({}, safe=False)


def set_delivered_quantity(request):
    if request.method == "POST":
        order_id = json.loads(request.body).get('order_id')
        delivered_quantity = json.loads(request.body).get('delivered_quantity')
        order_r = Order.objects.get(id=order_id)
        order_r.delivered_quantity = delivered_quantity
        order_r.save()
    return JsonResponse({}, safe=False)
