from django.conf.urls import url,include
from KB_notebookSearch import views,models
from django.conf.urls.static import static


urlpatterns = [
    url(r'^genericsearch', views.genericsearch, name='genericsearch')


]


