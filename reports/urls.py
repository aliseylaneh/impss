from django.urls import path
from reports import views
from django.views.decorators.csrf import csrf_exempt

app_name = 'reports'

urlpatterns = [

    path('report', views.report_home, name='report')

]