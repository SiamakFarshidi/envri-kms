from django.shortcuts import render
import json
import os
from django.http import JsonResponse
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Index
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from googletrans import Translator

# Create your views here.
decisionModels = open(os.getcwd()+'/DSS/config/decisionModels.json',"r")
decisionModels = json.loads(r''+decisionModels.read())
#-------------------------------------------------------------------------------------------------------------
def getPrioritizableFeatures(request):
    try:
        decisionModel = request.GET['decisionModel']
    except:
        decisionModel = ''

    if decisionModel in decisionModels:
        features={}
        decisionModel=decisionModels[decisionModel]

        for feature in decisionModel:
            if decisionModel[feature]['UI']['prioritizable']:
                datatype=decisionModel[feature]['scoreCalculation']['datatype']
                potentialValues= decisionModel[feature]['UI']['potentialValues']
                caption=decisionModel[feature]['UI']['caption']
                category=decisionModel[feature]['UI']['category']
                subfeatures=decisionModel[feature]['UI']['subfeatures']
                description= decisionModel[feature]['UI']['description']

                if datatype=='int':
                    potentialValues='An integer number greater than or equal to zero.'
                elif datatype=='currency':
                    potentialValues='A decimal number greater than or equal to zero.'
                elif datatype=='date':
                    potentialValues='A date value based on YYYY-MM-DD template. For example, 2022-03-01'
                elif datatype=='geo_point':
                    potentialValues='A latitude-longitude pair or coordinate of a place based on [longitude,latitude] template. For example, [4.63392,52.37038]'
                elif datatype=='boolean':
                    potentialValues='A boolean value (true/false).'

                features[feature]= {"caption": caption, "category": category, "subfeatures":subfeatures , "datatype":datatype, "potentialValues": potentialValues , "description": description}

        return HttpResponse(json.dumps(features,  indent=3), content_type="application/json")
    else:
        return JsonResponse({"Message": "I cannot find the decision model for you!"})
#-------------------------------------------------------------------------------------------------------------
def getDecisionModel(request):
    try:
        decisionModel = request.GET['decisionModel']
    except:
        decisionModel = ''

    if decisionModel in decisionModels:
        return HttpResponse(json.dumps(decisionModels[decisionModel],  indent=3), content_type="application/json")
    else:
        return JsonResponse({"Message": "I cannot find the decision model for you!"})
 #-------------------------------------------------------------------------------------------------------------
def listOfSolutions(request):
    featureRequirements={
        "parameters":{
            "decisionModel": "realestate",
            "page":1
        },       
        "featureRequirements":{
            "offer_type":{
                "value": "koop",
                "priority": "must-have"
            },
            "energy_label":{
                "value": "B",
                "priority": "should-have"
            },
             "number_of_bathrooms":{
                  "value": "2",
                  "priority": "should-have"
            },
            "number_of_rooms":{
                "value": "3",
                "priority": "could-have"
            },
            "volume_in_cubic_meters":{
                "value": "100",
                "priority": "must-have"
            },
            "number_of_bedrooms":{
                "value": "3",
                "priority": "could-have"
            },
            "asking_price":{
                "value": "300000",
                "priority": "should-have"
            },
            "city":{
                "value": "utrecht",
                "priority": "must-have"
            }
        },
        "case":"Family"
    }

    page = featureRequirements["parameters"]["page"]
    numHits,solutions=getSolutions(featureRequirements, page)
    #print(translate("en","fa","hello Dear Siamak "))

    return JsonResponse({"hits": numHits,"solutions": solutions})
#-------------------------------------------------------------------------------------------------------------
@csrf_exempt
def numberOfSolutions(request):
    if request.method == "POST":
        print("ok")


    featureRequirements={
        "parameters":{
            "decisionModel": "realestate",
            "page":1
        },
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

    page = featureRequirements["parameters"]["page"]
    numHits,solutions=getSolutions(featureRequirements, page)

    return JsonResponse({'hits': numHits, "solutions":{}})
#-------------------------------------------------------------------------------------------------------------
def detailedSolution(request):

    solution={
        "decisionModel": "realestate",
        "id":"https://www.funda.nl/koop/hippolytushoef/huis-42501003-elft-13/"
    }

    numHits,solutions=getSolutionByID(solution)
    return JsonResponse({"hits": numHits,"solutions": solutions})
#-------------------------------------------------------------------------------------------------------------
def scoreCalculation(featureImpactFactores, solutions):

    rankedSolutions=[]

    maxValue=0
    for solution in solutions:
        score=0
        alternativeSolution=solution["_source"]
        alternativeSolution['id']=solution["_id"]
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
    featureImpactFactores,query, sort=queryBilder(featureRequirements)
    page=(page-1)*20
    es = Elasticsearch("http://localhost:9200")
    index = Index(featureRequirements["parameters"]["decisionModel"], es)
    decisionModel=decisionModels[featureRequirements["parameters"]["decisionModel"]]

    if not es.indices.exists(index=featureRequirements["parameters"]["decisionModel"]):
        return {}
    user_request = "some_param"
    query_body = {
        "query": query,
        "sort": sort,
        "from": page,
        "size": 20
    }

    result = es.search(index=featureRequirements["parameters"]["decisionModel"], body=query_body)
    numHits=result['hits']['total']['value']
    solutions=scoreCalculation(featureImpactFactores, result['hits']['hits'])

    for solution in solutions:
        for feature in solution:
            print(feature)
            if feature in decisionModel and decisionModel[feature]['scoreCalculation']['datatype']=="enumeration":
                lookup=decisionModel[feature]['schemaMapping']['mappingScript']['lookup']
                for candidateValue in lookup:
                    if lookup[candidateValue]==solution[feature]:
                        solution[feature]=candidateValue
    return numHits, solutions
#-------------------------------------------------------------------------------------------------------------
def getQualityWeights(featureRequirements):
    decisionModel=decisionModels[featureRequirements["parameters"]["decisionModel"]]
    qualityRequirement={}
    cntQualities=0

    for feature in featureRequirements["featureRequirements"]:
        for quality in decisionModel[feature]["scoreCalculation"]["qualities"]:
            if quality not in qualityRequirement:
                qualityRequirement[quality]=1
            else:
                qualityRequirement[quality]=qualityRequirement[quality]+1
            cntQualities=cntQualities+1

    for quality in qualityRequirement:
        qualityRequirement[quality]=qualityRequirement[quality]/cntQualities

    return qualityRequirement
#-------------------------------------------------------------------------------------------------------------
def getFeaturesImpactFactors(featureRequirements):
    ShouldHaveWeight=0.9
    CouldHaveWeight=0.1
    totalImpactFactor=0
    featureImpactFactores=[]

    qualityRequirement=getQualityWeights(featureRequirements)
    decisionModel=decisionModels[featureRequirements["parameters"]["decisionModel"]]

    for feature in featureRequirements["featureRequirements"]:

        datatype=decisionModel[feature]["scoreCalculation"]["datatype"]
        value= featureRequirements["featureRequirements"][feature]["value"]
        priority= featureRequirements["featureRequirements"][feature]["priority"]
        impactFactor=0

        if datatype=='enumeration':
            value=decisionModel[feature]['schemaMapping']['mappingScript']['lookup'][value]

        if priority!="must-have":
            for quality in decisionModel[feature]["scoreCalculation"]["qualities"]:
                impactFactor=impactFactor+qualityRequirement[quality]

        if priority=="should-have":
            impactFactor=impactFactor*ShouldHaveWeight
        elif priority=="could-have":
            impactFactor=impactFactor*CouldHaveWeight

        totalImpactFactor=totalImpactFactor+impactFactor

        featureImpactFactores.append({"feature":feature, "priority": priority, "datatype": datatype, "value":value, "impactFactor": impactFactor})

    for featureIF in featureImpactFactores:
        featureIF["impactFactor"]= (featureIF["impactFactor"]/totalImpactFactor)

    return featureImpactFactores
#-------------------------------------------------------------------------------------------------------------
def queryBilder(featureRequirements):
    featureImpactFactores=getFeaturesImpactFactors(featureRequirements)

    must_queries=[]
    could_should_queries=[]
    sort=[]

    for reqFeature in featureImpactFactores:
        feature=reqFeature['feature']
        value=reqFeature['value']
        priority=reqFeature['priority']
        datatype=reqFeature['datatype']
        impactFactor=reqFeature['impactFactor']+1

        if priority=='must-have':
            if  datatype=='string':
                must_queries.append({"term": {feature: value}})
            elif datatype=='currency':
                must_queries.append({"range": {feature: {"lte": value}}})
            elif datatype=='int' or datatype=='enumeration':
                must_queries.append({"range": {feature: {"gte": value}}})
        elif priority=='should-have':
            if  datatype=='string':
                could_should_queries.append( {"constant_score": {"filter": {"match": {feature:value}}, "boost": impactFactor}})
            elif datatype=='currency':
                could_should_queries.append({"constant_score": {"filter": {"range": {feature: {"lte": value}}}, "boost": impactFactor}})
                sort.append( { feature: { "order": "asc",  "mode" : "min" }})
            elif datatype=='int' or datatype=='enumeration':
                could_should_queries.append({"constant_score": {"filter": {"range": {feature: {"gte": value}}}, "boost": impactFactor}})
                sort.append( { feature: { "order": "desc",  "mode" : "max"}})

    query={
        "bool": {
            "must":must_queries,
            "should":could_should_queries
        }
    }

    return featureImpactFactores,query, sort
#-------------------------------------------------------------------------------------------------------------
def getSolutionByID(Solution):
    es = Elasticsearch("http://localhost:9200")
    index = Index(Solution["decisionModel"], es)

    if not es.indices.exists(index=Solution["decisionModel"]):
        return {}

    user_request = "some_param"
    query_body = {
        "query": {
            "bool": {
                "must": [{
                    "match_phrase": {
                        "_id": Solution["id"]
                    }
                }]
            }
        },
        "from": 0,
        "size": 1
    }
    result = es.search(index=Solution["decisionModel"], body=query_body)
    numHits=result['hits']['total']['value']
    if not numHits:
        return 0,{}

    return numHits,result['hits']['hits'][0]
#-------------------------------------------------------------------------------------------------------------
def translate(source, target, text):
    translator = Translator()
    result = translator.translate(text, src=source, dest=target)

    #print(result.src)
    #print(result.dest)
    #print(result.text)

    return result.text


#-------------------------------------------------------------------------------------------------------------
