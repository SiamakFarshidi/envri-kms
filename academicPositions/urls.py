from django.conf.urls import url,include
from academicPositions import views,models
from django.conf.urls.static import static

urlpatterns = [
    url('main', views.main, name='main'),
]
