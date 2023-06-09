# Generated by Django 4.2 on 2023-05-01 18:50

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=255, null=True, unique=True)),
                ('address', models.CharField(max_length=255, null=True)),
                ('city', models.CharField(max_length=30, null=True)),
                ('province', models.CharField(max_length=30, null=True)),
                ('fax', models.CharField(max_length=30, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=50, null=True)),
                ('created_date', models.DateField(default=django.utils.timezone.now)),
                ('suppliers', models.ManyToManyField(to='roms.brand', verbose_name='suppliers')),
                ('user_expert', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='Prison',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, null=True)),
                ('address', models.CharField(max_length=255, null=True)),
                ('phone_number', models.BigIntegerField(null=True)),
                ('deputy', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PrisonBranch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, null=True)),
                ('address', models.CharField(max_length=255, null=True)),
                ('branch_deputy', models.CharField(max_length=50, null=True)),
                ('phone_number', models.BigIntegerField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, null=True)),
                ('ordered_quantity', models.BigIntegerField(default=0, null=True)),
                ('based_quantity', models.CharField(choices=[('عدد', 'Each'), ('کارتن', 'Box'), ('کیلوگرم', 'Kg'), ('گرم', 'Gr'), ('تن', 'Tn'), ('متر', 'Meter')], default='عدد', max_length=20, null=True)),
                ('description', models.CharField(max_length=255, null=True)),
                ('tax', models.FloatField(default=9)),
                ('profit', models.FloatField(default=3)),
                ('created_date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.BooleanField(default=True)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.category')),
            ],
        ),
        migrations.CreateModel(
            name='Province',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, null=True)),
                ('code', models.CharField(default=0, max_length=3, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=255, null=True, unique=True)),
                ('user_signatures', models.BinaryField(default=b'\x80\x04\x95L\x00\x00\x00\x00\x00\x00\x00}\x94(\x8c\x03ceo\x94N\x8c\x11financial_manager\x94N\x8c\x12commercial_manager\x94N\x8c\x11commercial_expert\x94Nu.', null=True)),
                ('request_status', models.CharField(choices=[('درحال بررسی توسط مدیر عامل', 'Ceo Review'), ('درحال بررسی توسط مدیر مالی', 'Fm Review'), ('درحال بررسی توسط مدیر بازرگانی', 'Cm Review'), ('درحال بررسی توسط کارشناس بازرگانی', 'Ce Review'), ('عدم تایید توسط مدیر عامل', 'Ceo Dreview'), ('عدم تایید توسط مدیر مالی', 'Fm Dreview'), ('عدم تایید توسط مدیر بازرگانی', 'Cm Dreview'), ('عدم تایید توسط کارشناس بازرگانی', 'Ce Dreview'), ('اتمام تاییدیه', 'Completed')], default='درحال بررسی توسط مدیر عامل', max_length=255)),
                ('shipping_status', models.CharField(choices=[('درحال تاییدیه', 'Requested'), ('در حال ارسال به تامین کنندگان', 'Supplier'), ('در حال آماده سازی سفارش', 'Gathering'), ('ارسال شده', 'Sending'), ('دریافت شده', 'Delivered'), ('تایید نشده', 'Declined')], default='درحال تاییدیه', max_length=50)),
                ('created_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('acceptation_date', models.DateTimeField(blank=True, null=True)),
                ('branch', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.prisonbranch')),
                ('expert', models.ManyToManyField(related_name='expert', to=settings.AUTH_USER_MODEL)),
                ('expert_acceptation', models.ManyToManyField(related_name='expert_acceptation', to=settings.AUTH_USER_MODEL)),
                ('last_returned_expert', models.ManyToManyField(blank=True, related_name='last_returned_expert', to=settings.AUTH_USER_MODEL)),
                ('prison', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.prison')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=30, null=True, unique=True)),
                ('address', models.CharField(max_length=255, null=True)),
                ('province', models.CharField(max_length=30, null=True)),
                ('fax', models.CharField(max_length=30, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('margin', models.IntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, null=True)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2023, 5, 1, 23, 20, 36, 947526))),
                ('request', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='roms.request')),
            ],
        ),
        migrations.CreateModel(
            name='SupplierProduct',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.BigIntegerField(default=0)),
                ('price2m', models.BigIntegerField(default=0)),
                ('created_date', models.DateTimeField(default=datetime.datetime(2023, 5, 1, 23, 20, 36, 948525))),
                ('brand', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.brand')),
                ('last_edition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.product')),
                ('request', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.request')),
                ('supplier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.supplier')),
            ],
        ),
        migrations.AddField(
            model_name='prison',
            name='prisons',
            field=models.ManyToManyField(to='roms.prisonbranch', verbose_name='prisons'),
        ),
        migrations.AddField(
            model_name='prison',
            name='province',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.province'),
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=0)),
                ('sell_deliver_price', models.BigIntegerField(default=0)),
                ('delivered_quantity', models.IntegerField(default=0)),
                ('created_date', models.DateField(default=django.utils.timezone.now)),
                ('price', models.BigIntegerField(default=0)),
                ('price_2m', models.BigIntegerField(default=0)),
                ('sell_price', models.BigIntegerField(default=0)),
                ('buy_price', models.BigIntegerField(default=0)),
                ('profit', models.BigIntegerField(default=0)),
                ('total_price', models.BigIntegerField(default=0)),
                ('brand', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.brand')),
                ('last_edition', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.product')),
                ('request', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='roms.request')),
                ('supplier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='roms.supplier')),
            ],
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.CharField(max_length=255, null=True)),
                ('reply', models.CharField(max_length=255, null=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('comment_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='comment_user', to=settings.AUTH_USER_MODEL)),
                ('reply_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reply_user', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='roms.ticket')),
            ],
        ),
        migrations.CreateModel(
            name='DeliverDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, null=True)),
                ('status', models.BooleanField(blank=True, default=False)),
                ('number', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('total_price', models.BigIntegerField(blank=True, default=0)),
                ('received_date', models.DateField(blank=True, null=True)),
                ('returned_date', models.DateField(blank=True, null=True)),
                ('paid_factor', models.BooleanField(blank=True, default=False)),
                ('paid_factor_sbd', models.DateField(blank=True, null=True)),
                ('paid_factor_rd', models.DateField(blank=True, null=True)),
                ('last_edition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('paid_factor_le', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paid_factor_le', to=settings.AUTH_USER_MODEL)),
                ('request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='roms.request')),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='roms.supplier')),
            ],
            options={
                'unique_together': {('request', 'supplier')},
            },
        ),
    ]
