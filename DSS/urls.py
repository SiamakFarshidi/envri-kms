from django.conf.urls import url,include
from DSS import views,models
from django.conf.urls.static import static


urlpatterns = [
    url(r'^numberOfSolutions', views.numberOfSolutions, name='numberOfSolutions'),
    url(r'^listOfSolutions', views.listOfSolutions, name='listOfSolutions'),
    url(r'^detailedSolution', views.detailedSolution, name='detailedSolution'),
    url(r'^getDecisionModel', views.getDecisionModel, name='getDecisionModel'),
    url(r'^getPrioritizableFeatures', views.getPrioritizableFeatures, name='getPrioritizableFeatures'),
    url('signin/', views.api_signin, name='api_signin'),
    url('assetSearch', views.assetSearch, name='assetSearch'),
]
