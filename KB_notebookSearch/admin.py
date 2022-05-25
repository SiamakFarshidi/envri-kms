from django.contrib import admin
from .models import Task1


class TaskAdmin(admin.ModelAdmin):
    list_display = [f.name for f in Task1._meta.fields]


admin.site.register(Task1, TaskAdmin)
