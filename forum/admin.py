from django.contrib import admin
from .models import Question, Reply, Like
 
admin.site.register(Question)
admin.site.register(Reply)
admin.site.register(Like)