from django.shortcuts import render
import json
import os
from django.http import JsonResponse


# Create your views here.
decisionModels = open(os.getcwd()+'/DSS/decisionModels.json',"r")
decisionModels = json.loads(r''+decisionModels.read())
#-------------------------------------------------------------------------------------------------------------
def listOfSolutions(request):
    page=1
    decisionModel=decisionModels["realestate"]
    featureRequirements={
        "offer_type":{
            "value": "koop",
            "priority": "must-have"
        },
        "number_of_rooms":{
            "value": "4",
            "priority": "should-have"
        },
        "number_of_bedrooms":{
            "value": "2",
            "priority": "should-have"
        },
        "number_of_bedrooms":{
            "value": "2",
            "priority": "should-have"
        },
        "asking_price":{
            "value": "200000",
            "priority": "should-have"
        }

    }
    solutions=getSolutions(decisionModel, featureRequirements, page)
    rankedSolutions = scoreCalculation(decisionModel, featureRequirements, solutions)

    return JsonResponse(rankedSolutions)
#-------------------------------------------------------------------------------------------------------------
def numberOfSolutions(request):
    decisionModel=decisionModels["realestate"]
    featureRequirements={}

    return JsonResponse({'results': getNumberOfSolutions(decisionModel, featureRequirements)})
#-------------------------------------------------------------------------------------------------------------
def detailedSolution(request):
    return JsonResponse({'status': 'Invalid request'}, status=400)
#-------------------------------------------------------------------------------------------------------------
def scoreCalculation(decisionModel, featureRequirements, solutions):
    rankedSolutions={}

    return rankedSolutions
#-------------------------------------------------------------------------------------------------------------
def getSolutions(decisionModel, featureRequirements, page):
    solutions={}

    return solutions
#-------------------------------------------------------------------------------------------------------------
def getNumberOfSolutions(decisionModel, featureRequirements):
    numberOfSolutions=0


    return numberOfSolutions
#-------------------------------------------------------------------------------------------------------------
