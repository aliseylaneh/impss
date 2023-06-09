from django.urls import path
from main import views
from django.views.decorators.csrf import csrf_exempt

app_name = 'main'

urlpatterns = [
    path("products", views.get_products, name="products"),
    path("add_user", views.add_user, name="add_user"),
    path('search_products', csrf_exempt(views.search_products), name='search_products'),
    path('new_request', views.new_request, name='new_request'),
    path('users', views.get_users, name='users'),
    path('delete_user', views.delete_user, name='delete_user'),
    path('search_users', csrf_exempt(views.search_users), name='search_users'),
    path('get_user/<str:pk>/', views.get_user, name='get_user'),
    path('update_user', views.update_user, name='update_user'),
    path('update_profile/<str:pk>/', views.update_profile, name='update_profile'),
    path('review_request', csrf_exempt(views.review_request), name='review_request'),
    path('suppliers', views.get_suppliers, name="suppliers"),
    path('delete_supplier', views.delete_supplier, name='delete_supplier'),
    path('search_suppliers', csrf_exempt(views.search_suppliers), name='search_suppliers'),
    path('update_supplier', views.update_supplier, name='update_supplier'),
    path('get_supplier/<str:pk>/', views.get_supplier, name='get_supplier'),
    path('add_supplier', views.add_supplier, name='add_supplier'),
    path('add_product', views.add_product, name='add_product'),
    path('get_product/<str:pk>', views.get_product, name='get_product'),
    path('update_product', views.update_product, name='update_product'),
    path('categories', views.categories, name='categories'),
    path('delete_category', views.delete_category, name='delete_category'),
    path('get_category/<str:pk>', views.get_category, name='get_category'),
    path('update_category', views.update_category, name='update_category'),
    path('user/requests', views.requests, name='requests'),
    path('get_request/<str:pk>', views.get_request, name='get_request'),
    path('update_request/<str:pk>', views.update_request, name='update_request'),
    path('accept/request/<str:pk>', csrf_exempt(views.accept_request), name='accept_request'),
    path('decline/request/<str:pk>', csrf_exempt(views.decline_request), name='decline_request'),
    path('user/declined_request', views.declined_request, name='declined_request'),
    path('user/finalized_request', views.finalized_requests, name='finalized_request'),
    path('add_product_to_request', csrf_exempt(views.add_product_to_request), name='add_product_to_request'),
    path('remove_order_request', csrf_exempt(views.remove_order_request), name='remove_order_request'),
    path('update_order_request', csrf_exempt(views.update_order_request), name='update_order_request'),
    path('update_order_request_staff', csrf_exempt(views.update_order_request_staff),
         name='update_order_request_staff'),
    path('change_request_cexpert', csrf_exempt(views.change_request_cexpert), name='change_request_cexpert'),
    path('change_request_cexpertrn', csrf_exempt(views.change_request_cexpertrn), name='change_request_cexpertrn'),

    path('user/expert_requests', views.expert_requests, name='expert_request'),
    path('user/returned_requests', views.returned_requests, name='returned_requests'),
    path('submit_request_conversation', csrf_exempt(views.submit_request_conversation),
         name='submit_request_conversation'),
    path('submit_request_ticket', csrf_exempt(views.submit_request_ticket), name='submit_request_ticket'),
    path('get_request/<str:pk>/supplier_orders', csrf_exempt(views.supplier_orders), name='supplier_orders'),
    path('get_request/<str:pk>/supplier_orders/<str:ord>', csrf_exempt(views.get_rs_orders), name='get_rs_orders'),
    path('get_request/<str:pk>/supplier_orders/<str:ord>/factor', csrf_exempt(views.get_rs_orders_factor),
         name='get_rs_orders_factor'),

    # Prison
    path('prisonbranches', views.prisonbranches, name='prisonbranches'),
    path('update_branch/<str:pk>', csrf_exempt(views.update_prisonbranch), name='update_branch'),
    path('get_prisonbranch/<str:pk>', views.get_prisonbranch, name='get_prisonbranch'),
    path('prisons', views.prisons, name='prisons'),
    path('update_prison/<str:pk>', csrf_exempt(views.update_prison), name='update_prison'),
    path('get_prison/<str:pk>', views.get_prison, name='get_prison'),

    # Brand
    path('brands', views.get_brands, name="brands"),
    path('delete_brand', views.delete_brands, name='delete_brands'),
    path('search_brands', csrf_exempt(views.search_brands), name='search_brands'),
    path('update_brand/<str:pk>', views.update_brand, name='update_brand'),
    path('get_brand/<str:pk>/', views.get_brand, name='get_brand'),
    path('add_brand', views.add_brand, name='add_brand'),

    path('get_product_price', csrf_exempt(views.get_supplier_price), name='get_product_price'),
    path('add_supplier_price', csrf_exempt(views.add_supplier_price), name='add_supplier_price'),

    path('user/completed_request', views.completed_requests, name='completed_request'),
    path('user/reviewing_request', views.reviewing_requests, name='reviewing_request'),
    path('supplier/set_deliver_date', csrf_exempt(views.add_sdeliver_date), name='set_deliver_date'),
    path('decline/request/return_declined_request/<str:pk>', csrf_exempt(views.return_declined_request),
         name='return_declined_request'),

    path('set_delivered_quantity', csrf_exempt(views.set_delivered_quantity), name='set_delivered_quantity'),
    path('get_request/<str:pk>/supplier_orders/<str:ord>/edit_factor', csrf_exempt(views.edit_get_rs_orders_factor),
         name='edit_get_rs_orders_factor'),
    path('request/<str:req>/submit_factor/<str:sup>', csrf_exempt(views.submit_delivered_factor),
         name='submit_delivered_factor'),

    path('export_order_report', views.export_order_report, name='export_order_report'),
    path('get_request/<str:pk>/supplier_orders/<str:ord>/hamifactor', views.hami_factor, name='hamifactor'),

    path('request_factors', views.request_factors, name='request_factors'),

    path('search_requests', csrf_exempt(views.search_requests), name='search_requests'),
    path('user/all_requests', views.all_requests, name='all_request'),
    path('request/<str:req>/return_delivered_factor/<str:sup>',
         csrf_exempt(views.return_delivered_factor), name='return_delivered_factor'),

    path('request/<str:req>/submit_paid_factor/<str:sup>',
         csrf_exempt(views.submit_paid_factor), name='submit_paid_factor'),
    path('request/<str:req>/return_paid_factor/<str:sup>',
         csrf_exempt(views.return_paid_factor), name='return_paid_factor')
]
