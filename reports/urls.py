from django.urls import path
from reports import views
from django.views.decorators.csrf import csrf_exempt

app_name = 'reports'

urlpatterns = [

    path('report', views.report_home, name='report'),
    path('category_report', csrf_exempt(views.search_category), name='category_report'),
    path('review_request_report', csrf_exempt(views.review_request), name='review_request_report'),
    path('product_report', views.product_report, name='product_report'),
    path('product_search_report', csrf_exempt(views.search_product), name='product_search_report'),
    path('product_detailed_report', views.product_detailed_report, name='product_detailed_report'),
    path('search_detailed_product', csrf_exempt(views.search_detailed_product), name='search_detailed_product'),
    path('req-status-report', views.request_status_report, name='req-status-report'),
    path('request-search-report', csrf_exempt(views.search_request), name='request-search-report'),
    path('prison-report', views.prison_report, name='prison-report'),
    path('pris-order-report', views.prison_order_report, name='pris-order-report'),
    path('pris-ordered-report', views.prison_orderd_report, name='pris-ordered-report'),
    path('prison-date-report', csrf_exempt(views.prison_date_report), name='prison-date-report'),
    path('prison-deliver-report', csrf_exempt(views.prison_deliver_report), name='prison-deliver-report'),
    path('time-deliver-report', views.time_deliver_report, name='time-deliver-report'),
    path('time-dsearch-report', csrf_exempt(views.time_dsearch_report), name='time-dsearch-sreport'),
    path('request-time-search', csrf_exempt(views.request_time_search), name='request-time-search'),
    # path('group-report', views.group_report, name='group-report'),
    # path('group-search-report', csrf_exempt(views.group_search_report), name='group-search-report'),
    # path('por_xls', csrf_exempt(views.por_xls), name='por_xls')

]
