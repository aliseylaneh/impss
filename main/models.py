from datetime import datetime
from django.db import models
from jalali_date import date2jalali, datetime2jalali
from django.utils import timezone
from account.models import User
import pickle


class Province(models.Model):
    name = models.CharField(max_length=50, null=True)
    code = models.CharField(null=True, max_length=3, default=0)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    company_name = models.CharField(max_length=30, null=True, unique=True)
    address = models.CharField(max_length=255, null=True)
    province = models.CharField(max_length=30, null=True)
    fax = models.CharField(max_length=30, null=True)
    is_active = models.BooleanField(default=True)
    margin = models.IntegerField(default=1)

    def __status__(self):
        if self.is_active:
            return 'فعال'
        else:
            return 'غیر فعال'

    def __str__(self):
        return self.company_name or ''


class Brand(models.Model):
    company_name = models.CharField(max_length=255, null=True, unique=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=30, null=True)
    province = models.CharField(max_length=30, null=True)
    fax = models.CharField(max_length=30, null=True)
    is_active = models.BooleanField(default=True)

    def __status__(self):
        if self.is_active:
            return 'قرارداد جاری'
        else:
            return 'فاقد قرارداد'

    def __str__(self):
        return self.company_name or ''


class Category(models.Model):
    class Meta:
        verbose_name_plural = "Categories"

    name = models.CharField(max_length=100, primary_key=True)
    suppliers = models.ManyToManyField(Brand, verbose_name='suppliers')
    description = models.CharField(max_length=50, null=True)
    user_expert = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.name


class UnitTypeChoices(models.TextChoices):
    each = 'عدد'
    box = 'کارتن'
    kg = 'کیلوگرم'
    gr = 'گرم'
    tn = 'تن'
    meter = 'متر'


class Product(models.Model):
    name = models.CharField(max_length=50, null=True)
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)
    ordered_quantity = models.BigIntegerField(null=True, default=0)
    based_quantity = models.CharField(max_length=20, null=True, choices=UnitTypeChoices.choices,
                                      default=UnitTypeChoices.each)
    description = models.CharField(max_length=255, null=True)
    tax = models.FloatField(default=9)
    profit = models.FloatField(default=3)
    created_date = models.DateField(default=timezone.now)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PrisonBranch(models.Model):
    name = models.CharField(max_length=255, null=True)
    address = models.CharField(max_length=255, null=True)
    branch_deputy = models.CharField(max_length=50, null=True)
    phone_number = models.BigIntegerField(null=True)

    def __str__(self):
        return self.name


class Prison(models.Model):
    name = models.CharField(max_length=255, null=True)
    deputy = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    province = models.ForeignKey(Province, null=True, on_delete=models.SET_NULL)
    prisons = models.ManyToManyField(PrisonBranch, verbose_name='prisons')
    address = models.CharField(max_length=255, null=True)
    phone_number = models.BigIntegerField(null=True)

    def __str__(self):
        return self.name


class Status(models.TextChoices):
    ceo_review = 'درحال بررسی توسط مدیر عامل'
    fm_review = 'درحال بررسی توسط مدیر مالی'
    cm_review = 'درحال بررسی توسط مدیر بازرگانی'
    ce_review = 'درحال بررسی توسط کارشناس بازرگانی'

    ceo_dreview = 'عدم تایید توسط مدیر عامل'
    fm_dreview = 'عدم تایید توسط مدیر مالی'
    cm_dreview = 'عدم تایید توسط مدیر بازرگانی'
    ce_dreview = 'عدم تایید توسط کارشناس بازرگانی'
    completed = 'اتمام تاییدیه'


def init_user_signatures():
    context = {
        'ceo': None,
        'financial_manager': None,
        'commercial_manager': None,
        'commercial_expert': None
    }
    return pickle.dumps(context)


class ShippingStatus(models.TextChoices):
    requested = 'درحال تاییدیه'
    supplier = 'در حال ارسال به تامین کنندگان'
    gathering = 'در حال آماده سازی سفارش'
    sending = 'ارسال شده'
    delivered = 'دریافت شده'
    declined = 'تایید نشده'


class Request(models.Model):
    number = models.CharField(max_length=255, null=True, unique=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    user_signatures = models.BinaryField(null=True, default=init_user_signatures())
    prison = models.ForeignKey(Prison, null=True, on_delete=models.SET_NULL)
    branch = models.ForeignKey(PrisonBranch, null=True, on_delete=models.SET_NULL)
    request_status = models.CharField(max_length=255, choices=Status.choices, default=Status.ceo_review)
    shipping_status = models.CharField(max_length=50, choices=ShippingStatus.choices, default=ShippingStatus.requested)
    created_date = models.DateTimeField(default=timezone.now)
    acceptation_date = models.DateTimeField(null=True, blank=True)
    expert = models.ManyToManyField(User, related_name='expert')
    expert_acceptation = models.ManyToManyField(User, related_name='expert_acceptation')
    last_returned_expert = models.ManyToManyField(User, related_name='last_returned_expert', blank=True)

    @property
    def get_prison(self):
        return self.prison

    @property
    def get_acceptations_date(self):
        if self.acceptation_date is None:
            return 'تاریخ'
        return date2jalali(self.acceptation_date).strftime("%Y/%m/%d")

    @property
    def get_acceptations_time(self):
        if self.acceptation_date is None:
            return 'ساعت'
        return datetime2jalali(self.acceptation_date).strftime("%X")

    @property
    def get_created_date(self):
        return date2jalali(self.created_date).strftime("%Y/%m/%d")

    @property
    def get_created_time(self):
        return datetime2jalali(self.created_date).strftime("%X")

    @property
    def get_user(self):
        return self.user

    def __str__(self):
        return self.number


class Ticket(models.Model):
    request = models.ForeignKey(Request, null=True, on_delete=models.CASCADE)
    title = models.CharField(null=True, max_length=255)
    created_date = models.DateTimeField(default=datetime.now())

    @property
    def get_created_time(self):
        return datetime2jalali(self.created_date).strftime("%X")

    @property
    def get_created_date(self):
        return date2jalali(self.created_date).strftime("%Y/%m/%d")

    def __str__(self):
        return self.title


class Conversation(models.Model):
    ticket = models.ForeignKey(Ticket, null=True, on_delete=models.CASCADE)
    comment_user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='comment_user')
    reply_user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='reply_user')
    comment = models.CharField(max_length=255, null=True)
    reply = models.CharField(max_length=255, null=True)
    timestamp = models.DateTimeField(auto_now=True)


class Order(models.Model):
    request = models.ForeignKey(Request, null=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    brand = models.ForeignKey(Brand, null=True, on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, null=True, on_delete=models.SET_NULL)
    last_edition = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    quantity = models.IntegerField(default=0)
    sell_deliver_price = models.BigIntegerField(default=0)
    delivered_quantity = models.IntegerField(default=0)
    created_date = models.DateField(default=timezone.now)
    price = models.BigIntegerField(default=0)
    price_2m = models.BigIntegerField(default=0)
    sell_price = models.BigIntegerField(default=0)
    buy_price = models.BigIntegerField(default=0)
    profit = models.BigIntegerField(default=0)
    total_price = models.BigIntegerField(default=0)

    @property
    def set_price(self, price):
        if self.quantity != 0:
            self.price = price * self.quantity
        elif self.weight != 0:
            self.price = price * self.quantity

    def get_dict(self):
        return {
            'id': self.id,
            'request_id': self.request.id,
            'product': self.product.name,
            'category': self.product.category.name,
            'supplier': self.supplier.company_name,
            'brand': self.brand.company_name,
            'quantity_unit': self.product.based_quantity,
            'quantity': self.quantity,
            'price': self.price,
            'price_2m': self.price_2m
        }

    def __str__(self):
        return self.product.name + ' ' + self.request.number


class SupplierProduct(models.Model):
    request = models.ForeignKey(Request, null=True, on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, null=True, on_delete=models.SET_NULL)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    brand = models.ForeignKey(Brand, null=True, on_delete=models.SET_NULL)
    price = models.BigIntegerField(default=0)
    price2m = models.BigIntegerField(default=0)
    created_date = models.DateTimeField(default=datetime.now())
    last_edition = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, blank=True)

    @property
    def get_created_date(self):
        return date2jalali(self.created_date).strftime("%Y/%m/%d")

    @property
    def get_created_time(self):
        return datetime2jalali(self.created_date).strftime("%X")


class DeliverDate(models.Model):
    request = models.ForeignKey(Request, null=True, on_delete=models.CASCADE, blank=True)
    supplier = models.ForeignKey(Supplier, null=True, on_delete=models.CASCADE, blank=True)
    date = models.DateField(null=True, blank=True)
    status = models.BooleanField(default=False, blank=True)
    number = models.CharField(max_length=255, null=True, unique=True, blank=True)
    total_price = models.BigIntegerField(default=0, blank=True)
    received_date = models.DateField(null=True, blank=True)
    returned_date = models.DateField(null=True, blank=True)
    last_edition = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, blank=True)
    paid_factor = models.BooleanField(default=False, blank=True)
    paid_factor_sbd = models.DateField(null=True, blank=True)
    paid_factor_rd = models.DateField(null=True, blank=True)
    paid_factor_le = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='paid_factor_le',
                                       blank=True)

    @property
    def get_recieved_date(self):
        return date2jalali(self.received_date).strftime("%Y/%m/%d")

    class Meta:
        unique_together = [['request', 'supplier']]

    @property
    def get_deliver_date(self):
        return date2jalali(self.date).strftime("%Y/%m/%d")

    @property
    def get_received_date(self):
        if self.received_date is None:
            return None
        return date2jalali(self.received_date).strftime("%Y/%m/%d")

    def __str__(self):
        return self.request.number + ' ' + self.supplier.company_name
