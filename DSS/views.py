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
    page=2
    featureRequirements={
        "decisionModel": "realestate",
        "featureRequirements":{
            "offer_type":{
                "value": "koop",
                "priority": "must-have"
            },
            "energy_label":{
                "value": "C",
                "priority": "could-have"
            },
            "number_of_rooms":{
                "value": "3",
                "priority": "should-have"
            },
            "volume_in_cubic_meters":{
                "value": "100",
                "priority": "must-have"
            },
            "number_of_bedrooms":{
                "value": "3",
                "priority": "should-have"
            },
            "asking_price":{
                "value": "4000000",
                "priority": "must-have"
            },
            "city":{
                "value": "utrecht",
                "priority": "must-have"
            }
        }
    }

    numHits,solutions=getSolutions(featureRequirements, page)

    return JsonResponse({"hits": numHits,"solutions": solutions})
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
            "asking_price":{
                "value": "200000",
                "priority": "could-have"
            },
            "neighborhood":{
                "value": "scheepskwartier",
                "priority": "should-have"
            },
            "city":{
                "value": "utrecht",
                "priority": "must-have"
            }
        }
    }
    numHits,solutions=getSolutions(featureRequirements, page)
    return JsonResponse({'hits': numHits})
#-------------------------------------------------------------------------------------------------------------
def detailedSolution(request):
    return JsonResponse({'status': 'Invalid request'}, status=400)
#-------------------------------------------------------------------------------------------------------------
def scoreCalculation(featureImpactFactores, solutions):

    rankedSolutions=[]

    maxValue=0
    for solution in solutions:
        score=0
        alternativeSolution=solution["_source"]

        for feature in featureImpactFactores:
            featureTitle=feature['feature']
            if alternativeSolution[featureTitle]!="N/A" and feature["datatype"]=="int" and int(alternativeSolution[featureTitle]) >= int(feature["value"]):
                score=score+feature["impactFactor"]
            elif alternativeSolution[featureTitle]!="N/A" and  feature["datatype"]=="currency" and int(alternativeSolution[featureTitle]) <= int(feature["value"]) :
                score=score+feature["impactFactor"]
            elif alternativeSolution[featureTitle]!="N/A" and  str(feature["value"]) in str(alternativeSolution[featureTitle]):
                score=score+feature["impactFactor"]

        if not featureImpactFactores:
            score=1

        if score == 1:
            alternativeSolution['score']= 100
        else:
            alternativeSolution['score']= "{:.2f}".format(score*100)

        rankedSolutions.append(alternativeSolution)

    #rankedSolutions.sort(key=lambda k:k['score'], reverse=True)

    return rankedSolutions
#-------------------------------------------------------------------------------------------------------------
def getSolutions(featureRequirements, page):
    solutions={}
    decisionModel=decisionModels[featureRequirements["decisionModel"]]
    featureImpactFactores,query=queryBilder(featureRequirements)
    page=(page-1)*20

    es = Elasticsearch("http://localhost:9200")
    index = Index(featureRequirements["decisionModel"], es)

    if not es.indices.exists(index=featureRequirements["decisionModel"]):
        return {}
    user_request = "some_param"
    query_body = {
        "query": query,
        "from": page,
        "size": 20
    }
    result = es.search(index=featureRequirements["decisionModel"], body=query_body)
    numHits=result['hits']['total']['value']

    solutions=scoreCalculation(featureImpactFactores, result['hits']['hits'])

    return numHits, solutions
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

    MustBooster=10
    ShouldBooster=7
    CouldBooster=3


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

        impactFactor=0
        datatype=decisionModel[feature]["datatype"]
        value= featureRequirements["featureRequirements"][feature]["value"]
        priority= featureRequirements["featureRequirements"][feature]["priority"]

        query={}
        if datatype=="int":
            query= {"range": {feature: {"gte": value  , "boost": 2} }}
        elif datatype=="currency":
            query={"range": {  feature: {"lte": value , "boost": 2} }}
        else:
            query={"match": {feature: {"query": value, "boost": 2}}}

        for quality in decisionModel[feature]["qualities"]:
            impactFactor=impactFactor+qualityRequirement[quality]

        if not query:
            if priority=="should-have":
                impactFactor=impactFactor*ShouldHaveWeight
                query["match"][feature]["boost"]=ShouldBooster
            elif priority=="could-have":
                impactFactor=impactFactor*CouldHaveWeight
                query["match"][feature]["boost"]=CouldBooster
            elif priority=="must-have":
                query["match"][feature]["boost"]=MustBooster

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
                "minimum_should_match" : 0,
                "boost" : 4
            }
        }

    return featureImpactFactores,query
#-------------------------------------------------------------------------------------------------------------
