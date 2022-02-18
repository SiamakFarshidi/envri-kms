from django.shortcuts import render

# Create your views here.

def genericsearch(request):

    return render(request,'servicecatalogs_results.html',searchResults )
