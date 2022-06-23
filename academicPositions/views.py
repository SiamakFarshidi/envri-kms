from django.shortcuts import render

# Create your views here.
#-------------------------------------------------------------------------------------------------------------
def main(request):
    searchResults={}
    print("siamak")
    return render(request,'main.html',searchResults )
#-------------------------------------------------------------------------------------------------------------
