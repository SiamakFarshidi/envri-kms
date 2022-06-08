from django.conf.urls import url,include
from KB import views,models
from django.conf.urls.static import static


urlpatterns = [
    url(r'^genericsearch', views.genericsearch, name='genericsearch'),
    url(r'^searchNotebooks', views.searchNotebooks, name='searchNotebooks'),
    url(r'^searchDatasets', views.searchDatasets, name='searchDatasets'),
    url(r'^searchWebsites', views.searchWebsites, name='searchWebsites'),
    url(r'^searchWebAPIs', views.searchWebAPIs, name='searchWebAPIs'),



]


