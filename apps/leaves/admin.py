from django.contrib import admin
from .models import LeaveRequest, LeaveBalance
# Register your models here.
admin.site.register(LeaveRequest)
admin.site.register(LeaveBalance)