from django.shortcuts import render

# Create your views here.
#-------------------------------------------------------------------------------------------------------------
def listOfSolutions(request):
    return JsonResponse({'status': 'Invalid request'}, status=400)
#-------------------------------------------------------------------------------------------------------------
def numberOfSolutions(request):
    return JsonResponse({'status': 'Invalid request'}, status=400)
#-------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------
def detailedSolution(request):
    return JsonResponse({'status': 'Invalid request'}, status=400)
#-------------------------------------------------------------------------------------------------------------
