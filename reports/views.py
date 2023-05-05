from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Sum
# Create your views here.
from account.decorators import allowed_users
from account.models import UserProfile
from main.models import Category, Order
import csv
import io
import json
import logging
import unittest
from datetime import date
from datetime import datetime
from django.db.models import Q, Avg, Count
import django
import jdatetime
import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.handlers import exception
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseNotFound, HttpResponse, FileResponse
from django.urls import reverse
from io import StringIO
from datetime import datetime

from account.decorators import *
from main.models import *


# Category Report
@login_required(login_url='account:login')
def report_home(request):
    category = Category.objects.get(name='دخانیات')
    categories = Category.objects.all()
    prisons = Prison.objects.all()
    orders = Order.objects.filter(product__category=category).count()
    requests = Order.objects.filter(product__category=category).values('request').count()
    orders_price = Order.objects.filter(product__category=category).aggregate(Sum('quantity'))
    context = {
        'categories': categories,
        'orders': orders,
        'orders_price': orders_price['quantity__sum'],
        'category': category,
        'requests': requests,
        'prisons': prisons
    }
    return render(request, 'reports/category_report.html', context)


@login_required(login_url='account:login')
def search_category(request):
    if request.method == 'POST':
        category_name = json.loads(request.body).get('category_name')
        prison_id = json.loads(request.body).get('prison_id')
        start_date = json.loads(request.body).get('start_date')
        end_date = json.loads(request.body).get('end_date')
        category = Category.objects.get(name=category_name)
        brand_count = category.suppliers.all().count()
        expert_fullname = category.user_expert.userprofile.first_name + ' ' + category.user_expert.userprofile.last_name

        if start_date != '' and end_date != '':
            start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            orders_count = Order.objects.filter(product__category=category,
                                                created_date__range=[start_date, end_date])
            requests_count = Order.objects.filter(product__category=category,
                                                  created_date__range=[start_date, end_date])
        elif start_date != '' and end_date == '':
            start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            orders_count = Order.objects.filter(product__category=category,
                                                created_date__gte=start_date)
            requests_count = Order.objects.filter(product__category=category,
                                                  created_date__gte=start_date)
        elif start_date == '' and end_date != '':
            end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            orders_count = Order.objects.filter(product__category=category,
                                                created_date__lte=end_date)
            requests_count = Order.objects.filter(product__category=category,
                                                  created_date__lte=end_date)


        else:
            orders_count = Order.objects.filter(product__category=category)
            requests_count = Order.objects.filter(product__category=category)
        if prison_id != '0':
            print(prison_id)
            prison = Prison.objects.get(id=prison_id)
            orders_count = orders_count.filter(request__prison=prison)
            requests_count = requests_count.filter(request__prison=prison).values('request__number',
                                                                                  'request__request_status',
                                                                                  'request__shipping_status',
                                                                                  'request__prison__name',
                                                                                  'request__branch__name').distinct().order_by(
                'created_date')
        else:
            requests_count = requests_count.values('request__number',
                                                   'request__request_status',
                                                   'request__shipping_status',
                                                   'request__prison__name',
                                                   'request__branch__name').distinct().order_by(
                'created_date')
        orders_count_quantity = orders_count.aggregate(Sum('quantity'))['quantity__sum']
    data = {
        'orders_count': orders_count.count(),
        'requests_count': requests_count.count(),
        'orders_count_quantity': orders_count_quantity,
        'expert': expert_fullname,
        'brand_count': brand_count,
        'requests': list(requests_count),
        'category': category.name
    }
    return JsonResponse(data, safe=False)


@login_required(login_url='account:login')
def review_request(request):
    if request.method == 'POST':
        request_number = json.loads(request.body).get('request_number')
        request_n = Request.objects.get(number=request_number)
        user = UserProfile.objects.get(user__email=request_n.user)

        retrieved_request = {'number': request_n.number, 'status': request_n.request_status,
                             'shipping_status': request_n.shipping_status,
                             'request_datetime': request_n.get_created_date}
        user_profile = {'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone_number': user.phone_number, 'national_id': user.national_id, 'email': request.user.email}
        prison_profile = {'id': request_n.prison.id, 'name': request_n.prison.name, 'address': request_n.branch.address,
                          'phone_number': request_n.branch.phone_number,
                          'branch_deputy': request_n.branch.branch_deputy}
        orders = Order.objects.filter(request=request_n)

        request_orders = []
        for order in orders:

            supplier_product_price = SupplierProduct.objects.filter(request=request_n, product=order.product,
                                                                    supplier=order.supplier,
                                                                    brand=order.brand).order_by("-created_date")
            if len(supplier_product_price) == 0:
                supplier_product_price = SupplierProduct.objects.filter(product=order.product,
                                                                        supplier=order.supplier,
                                                                        brand=order.brand).order_by("-created_date")
                if len(supplier_product_price) != 0:
                    sellprice = supplier_product_price[0].price2m
                    buyprice = supplier_product_price[0].price
                else:
                    sellprice = 0
                    buyprice = 0
            else:
                sellprice = supplier_product_price[0].price2m
                buyprice = supplier_product_price[0].price

            request_orders.append({'product_name': order.product.name, 'product_category': order.product.category.name,
                                   'product_supplier': order.supplier.company_name,
                                   'product_brand': order.brand.company_name, 'product_quantity': order.quantity,
                                   'product_quantity_unit': order.product.based_quantity, 'sellprice': sellprice,
                                   'buyprice': buyprice})

        data = {
            'userprofile': user_profile,
            'prisonprofile': prison_profile,
            'request_orders': request_orders,
            'branch': request_n.branch.name,
            'request': retrieved_request
        }
        return JsonResponse(data, safe=False)


# Product Report
def product_report(request):
    categories = Category.objects.all()

    context = {
        'categories': categories
    }
    return render(request, "reports/product_report.html", context)


def search_product(request):
    product_id = json.loads(request.body).get('product_id')
    supplier_id = json.loads(request.body).get('supplier_id')
    start_date = json.loads(request.body).get('start_date')
    end_date = json.loads(request.body).get('end_date')
    product = Product.objects.get(id=product_id)
    supplier = Supplier.objects.get(company_name=supplier_id)
    if supplier.company_name != 'بدون تامین کننده':
        supplier_products = SupplierProduct.objects.filter(product=product, supplier=supplier)
    else:
        supplier_products = SupplierProduct.objects.filter(product=product)

    if start_date != '' and end_date != '':
        start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
        end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
        supplier_products = supplier_products.filter(created_date__range=[start_date, end_date])
    elif start_date != '' and end_date == '':
        start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
        supplier_products = supplier_products.filter(created_date__gte=start_date)
    elif start_date == '' and end_date != '':
        end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
        supplier_products = supplier_products.filter(created_date__lte=end_date)

    supplier_products = supplier_products.order_by("-created_date")
    supplier_count = supplier_products.values('supplier').distinct().count()
    brand_count = supplier_products.values('brand').exclude(brand__company_name='بدون برند').distinct().count()
    request_count = supplier_products.values('request').distinct().count()
    buy_price_avg = supplier_products.aggregate(Avg('price'))['price__avg']
    sell_price_avg = supplier_products.aggregate(Avg('price2m'))['price2m__avg']
    most_supplier = supplier_products.values_list('supplier', 'supplier__company_name').annotate(
        supplier_count=Count('supplier')).order_by(
        '-supplier_count')
    if len(supplier_products) == 0:
        return JsonResponse({"data": []}, safe=False)
    most_supplier_count = most_supplier[0][2]
    most_supplier = most_supplier[0][1]
    latest_supplier = supplier_products[0].supplier.company_name

    data = []
    for supplier in supplier_products:
        data.append({'product_name': supplier.product.name, 'supplier_name': supplier.supplier.company_name,
                     'brand_name': supplier.brand.company_name,
                     'price': supplier.price, 'price2m': supplier.price2m,
                     'created_date': f'{supplier.get_created_time} {supplier.get_created_date}',
                     'last_edition': supplier.last_edition.userprofile.first_name + ' ' + supplier.last_edition.userprofile.last_name if supplier.last_edition is not None else 'نامعلوم'})

    context = {
        'data': data,
        'supplier_count': supplier_count,
        'brand_count': brand_count,
        'request_count': request_count,
        'buy_price_avg': buy_price_avg,
        'sell_price_avg': sell_price_avg,
        'most_supplier': most_supplier,
        'latest_supplier': latest_supplier

    }
    return JsonResponse(context, safe=False)


def product_detailed_report(request):
    categories = Category.objects.all()
    prisons = Prison.objects.all()

    context = {
        'categories': categories,
        'prisons': prisons
    }
    return render(request, "reports/product_detailed_report.html", context)


def search_detailed_product(request):
    product_id = json.loads(request.body).get('product_id')
    start_date = json.loads(request.body).get('start_date')
    end_date = json.loads(request.body).get('end_date')
    product = Product.objects.get(id=product_id)
    prisons = Prison.objects.all()
    suppliers = Supplier.objects.all()

    orders = Order.objects.filter(product=product)
    if start_date != '' and end_date != '':
        start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
        end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
        orders = orders.filter(request__created_date__range=[start_date, end_date])
    elif start_date != '' and end_date == '':
        start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
        orders = orders.filter(request__created_date__gte=start_date)
    elif start_date == '' and end_date != '':
        end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
        orders = orders.filter(request__created_date__lte=end_date)

    orders = orders.order_by("-created_date")
    product_name = product.name
    product_category = product.category.name
    product_unit = product.based_quantity
    orders_count = orders.count()
    orders_quantity = orders.aggregate(Sum("quantity"))
    dq_sum = orders.aggregate(Sum('delivered_quantity'))
    sdp_avg = orders.aggregate(Avg('sell_deliver_price'))
    supplier_count = orders.values('supplier').distinct().count()
    with_brand_count = orders.values('brand').exclude(brand__company_name='بدون برند').distinct().count()
    no_brand_count = orders.filter(brand__company_name='بدون برند').count()
    if orders.count == 0:
        return JsonResponse({'orders_count': 0}, safe=False)
    prison_response = []
    for prison in prisons:
        prison_orders = orders.filter(request__prison=prison)
        if len(prison_orders) != 0:
            prison_response.append({'prison_name': prison.name,
                                    'order_quantity': prison_orders.aggregate(
                                        Sum("quantity"))['quantity__sum'], 'order_counter': prison_orders.count()})

    suppliers_response = []
    for supplier in suppliers:
        supplier_orders = orders.filter(supplier=supplier)
        if len(supplier_orders) != 0:
            suppliers_response.append(
                {'supplier_name': supplier.company_name,
                 'order_quantity': supplier_orders.aggregate(Sum("quantity"))['quantity__sum'],
                 'order_counter': supplier_orders.count()})

    requests_response = []
    for order in orders:
        supplier_product_price = SupplierProduct.objects.filter(request=order.request, product=order.product,
                                                                supplier=order.supplier,
                                                                brand=order.brand).order_by("-created_date")
        if len(supplier_product_price) == 0:
            supplier_product_price = SupplierProduct.objects.filter(product=order.product,
                                                                    supplier=order.supplier,
                                                                    brand=order.brand).order_by("-created_date")
            if len(supplier_product_price) != 0:
                sellprice = supplier_product_price[0].price2m
                buyprice = supplier_product_price[0].price
            else:
                sellprice = 0
                buyprice = 0
        else:
            sellprice = supplier_product_price[0].price2m
            buyprice = supplier_product_price[0].price

        requests_response.append(
            {'request_number': order.request.number, 'request_prison': order.request.prison.name,
             'request_branch': order.request.branch.name,
             'order_supplier': order.supplier.company_name, 'order_brand': order.brand.company_name,
             'order_quantity': order.quantity, 'order_delivered_quantity': order.delivered_quantity,
             'order_dsell_price': order.sell_deliver_price, 'order_sell_price': sellprice})

    context = {
        'supplier_count': supplier_count,
        'product_name': product_name,
        'product_category': product_category,
        'product_unit': product_unit,
        'orders_count': orders_count,
        'dq_sum': dq_sum['delivered_quantity__sum'],
        'sdp_avg': sdp_avg['sell_deliver_price__avg'],
        'with_brand_count': with_brand_count,
        'no_brand_count': no_brand_count,
        'prisons_response': prison_response,
        'suppliers_response': suppliers_response,
        'requests_response': requests_response,
        'orders_quantity': orders_quantity['quantity__sum']

    }
    return JsonResponse(context, safe=False)


@login_required(login_url='account:login')
def request_status_report(request):
    request_status = Status.values
    shipping_status = ShippingStatus.values

    context = {
        "request_status": request_status,
        "shipping_status": shipping_status
    }
    return render(request, 'reports/request_status_report.html', context)


@login_required(login_url='account:login')
def search_request(request):
    if request.method == 'POST':
        request_status = json.loads(request.body).get('request_status')
        shipping_status = json.loads(request.body).get('shipping_status')
        start_date = json.loads(request.body).get('start_date')
        end_date = json.loads(request.body).get('end_date')
        print(request_status, shipping_status)
        if request_status != '0':
            if start_date != '' and end_date != '':
                start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
                end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
                requests = Request.objects.filter(request_status=request_status,
                                                  created_date__range=[start_date, end_date])


            elif start_date != '' and end_date == '':
                start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
                requests = Request.objects.filter(request_status=request_status,
                                                  created_date__gte=start_date)

            elif start_date == '' and end_date != '':
                end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
                requests = Request.objects.filter(request_status=request_status,
                                                  created_date__lte=end_date)
            else:
                requests = Request.objects.filter(request_status=request_status)

        if shipping_status != '0' and request_status != '0':
            requests = requests.filter(shipping_status=shipping_status)
        elif shipping_status != '0' and request_status == '0':
            if start_date != '' and end_date != '':
                start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
                end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
                requests = Request.objects.filter(shipping_status=shipping_status,
                                                  created_date__range=[start_date, end_date])

            elif start_date != '' and end_date == '':
                start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
                requests = Request.objects.filter(shipping_status=shipping_status,
                                                  created_date__gte=start_date)

            elif start_date == '' and end_date != '':
                end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
                requests = Request.objects.filter(shipping_status=shipping_status,
                                                  created_date__lte=end_date)
            else:
                requests = Request.objects.filter(shipping_status=shipping_status)
        elif shipping_status == '0' and request_status == '0':
            requests = []
        request_count = Request.objects.all().count()
        accepted_requests = Request.objects.filter(request_status='اتمام تاییدیه').count()
        rejected_requests = Request.objects.filter(shipping_status='تایید نشده').count()
        if len(requests) == 0:
            data = {
                'rc': request_count,
                'arc': accepted_requests,
                'rrc': rejected_requests,
                'requests': []
            }
            return JsonResponse(data, safe=False)
        request_status_count = requests.count()
        requests = list(requests.values('number', 'prison__name', 'branch__name', 'request_status', 'created_date',
                                        'shipping_status').order_by('-created_date'))
        for requestf in requests:
            requestf['created_date'] = datetime2jalali(requestf['created_date']).strftime("%X") + ' ' + date2jalali(
                requestf['created_date']).strftime("%Y/%m/%d")
        data = {
            'rc': request_count,
            'arc': accepted_requests,
            'rsc': request_status_count,
            'rrc': rejected_requests,
            "requests": requests
        }
    return JsonResponse(data, safe=False)


def prison_report(request):
    prisons = Prison.objects.all()
    branches = PrisonBranch.objects.all()
    orders = []
    for prison in prisons:
        orders.append(
            list(Order.objects.filter(request__prison=prison).values_list('request__prison__name',
                                                                          'product__name',
                                                                          'product__based_quantity').annotate(
                prison_quantity=Sum('quantity')).order_by('-prison_quantity')[:1]))
    final_orders = []
    for order_f in orders:
        for order in order_f:
            final_orders.append(
                {'prison_name': order[0], 'product_name': order[1], 'unit': order[2], 'quantity': order[3]})
    print(order)
    request_count = Request.objects.all().count()
    orders_count = Order.objects.all().count()
    orders_full_count = Order.objects.all().aggregate(Sum('quantity'))
    context = {
        'orders': final_orders,
        'prison_count': prisons.count(),
        'branch_count': branches.count(),
        'request_count': request_count,
        'orders_count': orders_count,
        'orders_full_count': orders_full_count['quantity__sum'],
        'date': date2jalali(timezone.now()).strftime("%Y/%m/%d"),
        'time': datetime2jalali(timezone.now()).strftime("%X")
    }
    return render(request, "reports/prison_report.html", context)


def prison_order_report(request):
    return render(request, "reports/prison_order_report.html", {})


def prison_orderd_report(request):
    return render(request, "reports/prison_ordered_report.html", {})


def prison_date_report(request):
    prisons = Prison.objects.all().order_by('-name')
    prisons_r = []
    total_quantity = 0
    total_price = 0
    for prison in prisons:
        start_date = json.loads(request.body).get('start_date')
        end_date = json.loads(request.body).get('end_date')
        if start_date != '' and end_date != '':
            start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed,
                                          created_date__range=[start_date, end_date])

        elif start_date != '' and end_date == '':
            start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed,
                                          created_date__gte=start_date)

        elif start_date == '' and end_date != '':
            end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed,
                                          created_date__lte=end_date)
        else:
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed)
        price = 0
        if len(orders) != 0:
            for order in orders:
                supplierproduct = \
                    SupplierProduct.objects.filter(request=order.request, supplier=order.supplier,
                                                   brand=order.brand,
                                                   product=order.product).order_by('-created_date')
                if len(supplierproduct) == 0:
                    supplierproduct = SupplierProduct.objects.filter(supplier=order.supplier,
                                                                     brand=order.brand,
                                                                     product=order.product).order_by('-created_date')
                    if len(supplierproduct) != 0:
                        price += supplierproduct[0].price * order.quantity
                else:
                    price += supplierproduct[0].price * order.quantity
        if len(orders) != 0:
            total_price += price
            total_quantity += orders.aggregate(Sum('quantity'))['quantity__sum']
            prisons_r.append({
                'prison_name': prison.name,
                'orders_count': orders.aggregate(Sum('quantity'))['quantity__sum'],
                'orders_price': price

            })
    report_date = datetime2jalali(timezone.now()).strftime("%X") + " " + date2jalali(timezone.now()).strftime(
        "%Y/%m/%d")

    data = {
        'total_price': total_price,
        'total_quantity': total_quantity,
        'prisons': prisons_r,
        'report_date': report_date
    }
    return JsonResponse(data, safe=False)


def prison_deliver_report(request):
    prisons = Prison.objects.all().order_by('-name')
    prisons_r = []
    total_quantity = 0
    total_price = 0
    for prison in prisons:
        price = 0
        deliver_quantity = 0
        start_date = json.loads(request.body).get('start_date')
        end_date = json.loads(request.body).get('end_date')
        if start_date != '' and end_date != '':
            start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed,
                                          created_date__range=[start_date, end_date], delivered_quantity__gt=0)

        elif start_date != '' and end_date == '':
            start_date = jdatetime.datetime.strptime(start_date, '%Y/%m/%d').togregorian()
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed,
                                          created_date__gte=start_date, delivered_quantity__gt=0)

        elif start_date == '' and end_date != '':
            end_date = jdatetime.datetime.strptime(end_date, '%Y/%m/%d').togregorian()
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed,
                                          created_date__lte=end_date, delivered_quantity__gt=0)
        else:
            orders = Order.objects.filter(request__prison=prison,
                                          request__request_status=Status.completed, delivered_quantity__gt=0)

        if len(orders) != 0:
            for order in orders:
                order_dd = DeliverDate.objects.filter(request=order.request, supplier=order.supplier).order_by(
                    '-received_date')
                if len(order_dd) != 0:
                    if order_dd[0].status == 1:
                        supplierproduct = \
                            SupplierProduct.objects.filter(request=order.request, supplier=order.supplier,
                                                           brand=order.brand,
                                                           product=order.product).order_by('-created_date')
                        if len(supplierproduct) == 0:
                            supplierproduct = SupplierProduct.objects.filter(supplier=order.supplier,
                                                                             brand=order.brand,
                                                                             product=order.product).order_by(
                                '-created_date')
                            if len(supplierproduct) != 0:
                                price += supplierproduct[0].price * order.delivered_quantity
                        else:
                            price += supplierproduct[0].price * order.delivered_quantity
                        deliver_quantity += order.delivered_quantity
                        total_quantity += order.delivered_quantity
            total_price += price
            prisons_r.append({
                'prison_name': prison.name,
                'delivered_quantity': deliver_quantity,
                'orders_price': price

            })
    report_date = datetime2jalali(timezone.now()).strftime("%X") + " " + date2jalali(timezone.now()).strftime(
        "%Y/%m/%d")

    data = {
        'total_price': total_price,
        'total_quantity': total_quantity,
        'prisons': prisons_r,
        'report_date': report_date
    }
    return JsonResponse(data, safe=False)


def time_deliver_report(request):
    return render(request, "reports/time_report.html", {})


def time_dsearch_report(request):
    orders_suppliers = []
    supplier_deliver_count = 0
    request_number = json.loads(request.body).get('request_number')
    if request_number != '':
        try:
            request_r = Request.objects.get(number=request_number)
            orders = Order.objects.filter(request=request_r)
            orders_suppliers = orders.values('supplier',
                                             'supplier__company_name').distinct()
            orders_brands = orders.values('brand').distinct()
        except Request.DoesNotExist:
            data = {
                'orders_suppliers': [],
                'messsage': 'درخواست مورد نظر وجود ندارد'
            }
            return JsonResponse(data, safe=False)

    deliver_dates = []
    if len(orders_suppliers) != 0:
        for supplier in orders_suppliers:
            try:
                deliver_date = DeliverDate.objects.get(request=request_r, supplier_id=supplier['supplier'])
                if deliver_date is not None:

                    avg_receive_requested = (
                            deliver_date.received_date - request_r.created_date.date()).days if deliver_date.received_date and request_r.created_date is not None else 0
                    avg_receive_final = (
                            deliver_date.received_date - request_r.acceptation_date.date()).days if deliver_date.received_date and request_r.acceptation_date is not None else 0
                    avg_requested_final = (
                            request_r.acceptation_date.date() - request_r.created_date.date()).days if request_r.acceptation_date and request_r.created_date is not None else 0

                    deliver_dates.append(
                        {'request_date': request_r.get_created_date,
                         'supplier_name': supplier['supplier__company_name'],
                         'recieved_date': deliver_date.get_recieved_date if deliver_date.received_date is not None else 'بدون تاریخ',
                         'final_date': request_r.get_acceptations_date if request_r.acceptation_date is not None else 'بدون تاریخ',
                         'avg_receive_requested': avg_receive_requested, 'avg_receive_final': avg_receive_final,
                         'avg_requested_final': avg_requested_final})
                    if deliver_date.received_date is not None:
                        supplier_deliver_count += 1


            except DeliverDate.DoesNotExist:
                deliver_dates.append(
                    {'request_date': request_r.get_created_date,
                     'supplier_name': supplier['supplier__company_name'],
                     'recieved_date': 'بدون تاریخ',
                     'final_date': 'بدون تاریخ',
                     'avg_receive_requested': 0, 'avg_receive_final': 0,
                     'avg_requested_final': 0})

    # deliver_quantity = 0
    # price = 0
    # if len(orders) != 0:
    #     for order in orders:
    #         order_dd = DeliverDate.objects.filter(request=order.request, supplier=order.supplier).order_by(
    #             '-received_date')
    #         if len(order_dd) != 0:
    #             if order_dd[0].status == 1:
    #                 supplierproduct = \
    #                     SupplierProduct.objects.filter(request=order.request, supplier=order.supplier,
    #                                                    brand=order.brand,
    #                                                    product=order.product).order_by('-created_date')
    #                 if len(supplierproduct) == 0:
    #                     supplierproduct = SupplierProduct.objects.filter(supplier=order.supplier,
    #                                                                      brand=order.brand,
    #                                                                      product=order.product).order_by(
    #                         '-created_date')
    #                     if len(supplierproduct) != 0:
    #                         price += supplierproduct[0].price * order.delivered_quantity
    #                 else:
    #                     price += supplierproduct[0].price * order.delivered_quantity
    #                 deliver_quantity += order.delivered_quantity
    #                 total_quantity += order.delivered_quantity
    #                 total_price += price
    #     prisons_r.append({
    #         'delivered_quantity': deliver_quantity,
    #         'orders_price': price
    #
    #     })
    report_date = datetime2jalali(timezone.now()).strftime("%X") + " " + date2jalali(timezone.now()).strftime(
        "%Y/%m/%d")

    data = {
        'request_number': request_r.number,
        'suppliers_count': orders_suppliers.count(),
        'brands_count': orders_brands.count(),
        'deliver_dates': deliver_dates,
        'report_date': report_date,
        'supplier_deliver_count': supplier_deliver_count,
        'orders_count': orders.count()
    }
    return JsonResponse(data, safe=False)


def request_time_search(request):
    if request.method == 'POST':
        request_number = json.loads(request.body).get('request_number')
        requests = Request.objects.filter(number__contains=request_number)
        data = []
        if requests is not None:
            for request in requests:
                data.append(
                    {'number': request.number, 'status': request.request_status, 'sstatus': request.shipping_status,
                     'created_date': request.get_created_date, 'created_date_time': request.get_created_time,
                     'submitted_date': request.get_acceptations_date,
                     'submitted_time': request.get_acceptations_time,
                     'prison': request.prison.name,
                     'branch': request.branch.name})

    data = {
        'requests': data
    }
    return JsonResponse(data, safe=False)
