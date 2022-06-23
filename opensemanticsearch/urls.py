from django.conf.urls import include, url
from django.contrib import admin
from django.contrib import auth
from django.urls import path
from django.conf.urls.i18n import i18n_patterns

urlpatterns = i18n_patterns(
	path('admin/', admin.site.urls),
	url(r'^dataset_elastic/', include(('dataset_elastic.urls', 'dataset_elastic'), namespace="dataset_elastic")),
	url(r'^notebookSearch/', include(('notebookSearch.urls', 'notebookSearch'), namespace="notebookSearch")),
	url(r'^KB/', include(('KB.urls', 'KB'), namespace="KB")),
	url(r'^servicCatalogSearch/', include(('servicCatalogSearch.urls', 'servicCatalogSearch'), namespace="servicCatalogSearch")),
	url(r'^toolSearch/', include(('toolSearch.urls', 'toolSearch'), namespace="toolSearch")),
	url(r'^webSearch/', include(('webSearch.urls', 'webSearch'), namespace="webSearch")),
	url(r'^genericpages/', include(('genericpages.urls', 'genericpages'), namespace="genericpages")),
	url(r'^webAPI/', include(('webAPI.urls', 'webAPI'), namespace="webAPI")),
	url(r'^DSS/', include(('DSS.urls', 'DSS'), namespace="DSS")),
	url(r'^academicPositions/', include(('academicPositions.urls', 'academicPositions'), namespace="academicPositions")),
	url(r'^accountManagement/', include(('accountManagement.urls', 'accountManagement'), namespace="accountManagement")),
	path('', include(('genericpages.urls', 'genericpages'), namespace="genericpages")),
	prefix_default_language=False
)
