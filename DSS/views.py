from django.shortcuts import render
import json
import os
from django.http import JsonResponse
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Index

# Create your views here.
decisionModels = open(os.getcwd()+'/DSS/decisionModels.json',"r")
decisionModels = json.loads(r''+decisionModels.read())
#-------------------------------------------------------------------------------------------------------------
def listOfSolutions(request):
    page=1
    featureRequirements={
        "decisionModel": "realestate",
        "featureRequirements":{
            "offer_type":{
                "value": "koop",
                "priority": "must-have"
            },
            "energy_label":{
                "value": "A",
                "priority": "could-have"
            },
            "number_of_rooms":{
                "value": "4",
                "priority": "should-have"
            },
            "volume_in_cubic_meters":{
                "value": "400",
                "priority": "could-have"
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
            },
            "neighborhood":{
                "value": "scheepskwartier",
                "priority": "should-have"
            },
            "city":{
                "value": "utrecht",
                "priority": "should-have"
            }
        }
    }

    numHits,featureImpactFactores,solutions=getSolutions(featureRequirements, page)

    return JsonResponse(solutions)
#-------------------------------------------------------------------------------------------------------------
def numberOfSolutions(request):
    page=1
    featureRequirements={
    "decisionModel": "realestate",
    "featureRequirements":{
        "offer_type":{
            "value": "koop",
            "priority": "must-have"
        },
        "number_of_rooms":{
            "value": "4",
            "priority": "must-have"
        },
        "volume_in_cubic_meters":{
            "value": "400",
            "priority": "could-have"
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
            "priority": "must-have"
        }
    }
}
    numHits,featureImpactFactores,result=getSolutions(featureRequirements, page)
    return JsonResponse({'number of results': numHits})
#-------------------------------------------------------------------------------------------------------------
def detailedSolution(request):
    return JsonResponse({'status': 'Invalid request'}, status=400)
#-------------------------------------------------------------------------------------------------------------
def getSolutions(featureRequirements, page):
    solutions={}
    decisionModel=decisionModels[featureRequirements["decisionModel"]]
    featureImpactFactores,query=queryBilder(featureRequirements)
    page=(page-1)*10

    es = Elasticsearch("http://localhost:9200")
    index = Index(featureRequirements["decisionModel"], es)

    if not es.indices.exists(index=featureRequirements["decisionModel"]):
        return {}
    user_request = "some_param"
    query_body = {
        "query": query,
        "from": page,
        "size": 10
    }

    result = es.search(index=featureRequirements["decisionModel"], body=query_body)
    numHits=result['hits']['total']['value']

    return numHits,featureImpactFactores,result
#-------------------------------------------------------------------------------------------------------------
def queryBilder(featureRequirements):
    fields={}
    shouldHaveQueries=[]
    mustHaveQueries=[]
    decisionModel=decisionModels[featureRequirements["decisionModel"]]

    featureImpactFactores=[]
    qualityRequirement={}
    cntQualities=0

    ShouldHaveWeight=0.9
    CouldHaveWeight=0.1

    for feature in featureRequirements["featureRequirements"]:
        for quality in decisionModel[feature]["qualities"]:
            if quality not in qualityRequirement:
                qualityRequirement[quality]=1
            else:
                qualityRequirement[quality]=qualityRequirement[quality]+1
            cntQualities=cntQualities+1
    for quality in qualityRequirement:
        qualityRequirement[quality]=qualityRequirement[quality]/cntQualities

    totalImpactFactor=0
    for feature in featureRequirements["featureRequirements"]:

        datatype=decisionModel[feature]["datatype"]
        value= featureRequirements["featureRequirements"][feature]["value"]
        priority= featureRequirements["featureRequirements"][feature]["priority"]

        impactFactor=0

        for quality in decisionModel[feature]["qualities"]:
            impactFactor=impactFactor+qualityRequirement[quality]

        if priority=="should-have":
            impactFactor=impactFactor*ShouldHaveWeight
        elif priority=="could-have":
            impactFactor=impactFactor*CouldHaveWeight


        query={}
        if datatype=="int":
            query={"range": { feature: {"gte": value} }}
        elif datatype=="currency":
            query={"range": { feature: {"lte": value} }}
        else:
            query={"term": { feature: value }}

        if priority=="must-have":
            mustHaveQueries.append(query)
        else:
            shouldHaveQueries.append(query)
            featureImpactFactores.append({"feature":feature, "priority": priority, "datatype": datatype, "value":value, "impactFactor": impactFactor})
            totalImpactFactor=totalImpactFactor+impactFactor

    for featureIF in featureImpactFactores:
        featureIF["impactFactor"]= (featureIF["impactFactor"]/totalImpactFactor)

    query={
            "bool" : {
                "must": mustHaveQueries,
                "should": shouldHaveQueries,
                "minimum_should_match" : 1,
                "boost" : 1.0
            }
        }

    return featureImpactFactores,query