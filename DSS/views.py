from django.shortcuts import render
import json
import os
from django.http import JsonResponse
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Index
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from googletrans import Translator
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt


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
                    potentialValues='A triple <longitude, latitude, distance> that indicates the coordinate of the desired place and permitted distance in kilometers (km) from it and should be defined based on [longitude, latitude, distance] template. For example, [4.63392,52.37038,10]'
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
@csrf_exempt
def listOfSolutions(request):
    solutions={}
    numHits=0
    if request.method == 'POST':
        featureRequirements = json.loads(request.body) # request.raw_post_data w/ Django < 1.4
        print(featureRequirements)
        page = featureRequirements["parameters"]["page"]
        numHits,solutions=getSolutions(featureRequirements, page)
        #print(translate("en","fa","hello Dear Siamak "))
    return HttpResponse({"hits": numHits,"solutions": solutions}, content_type="application/json")
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
    return HttpResponse(json.dumps({"hits": numHits,"solutions": {}},  indent=3), content_type="application/json")

#-------------------------------------------------------------------------------------------------------------
def detailedSolution(request):

    solution={
        "decisionModel": "realestate",
        "id":"https://www.funda.nl/koop/hippolytushoef/huis-42501003-elft-13/"
    }

    numHits,solutions=getSolutionByID(solution)
    return HttpResponse(json.dumps({"hits": numHits,"solutions": solutions},  indent=3), content_type="application/json")

#-------------------------------------------------------------------------------------------------------------
def scoreCalculation(featureImpactFactores, solutions):
    rankedSolutions=[]
    for solution in solutions:
        score=0
        alternativeSolution=solution["_source"]
        alternativeSolution['id']=solution["_id"]

        if solution["_score"]>1:
            solution["_score"]=1

        if solution["_score"]==1:
            alternativeSolution['score']= "100 %"
        else:
            alternativeSolution['score']= "{:.2f} %".format(solution["_score"]*100)

        rankedSolutions.append(alternativeSolution)

    return rankedSolutions
#-------------------------------------------------------------------------------------------------------------
def getSolutions(featureRequirements, page):
    solutions={}
    featureImpactFactores,query=queryBilder(featureRequirements, page, 20)
    page=(page-1)*20
    es = Elasticsearch("http://localhost:9200")
    index = Index(featureRequirements["parameters"]["decisionModel"], es)
    decisionModel=decisionModels[featureRequirements["parameters"]["decisionModel"]]

    if not es.indices.exists(index=featureRequirements["parameters"]["decisionModel"]):
        return {}

    result = es.search(index=featureRequirements["parameters"]["decisionModel"], body=query)
    numHits=result['hits']['total']['value']
    solutions=scoreCalculation(featureImpactFactores, result['hits']['hits'])
    solutions= labelEnumerations(solutions, decisionModel)

    return numHits, solutions
#-------------------------------------------------------------------------------------------------------------
def labelEnumerations(solutions, decisionModel):

    for solution in solutions:
        for feature in solution:
            if feature in decisionModel and decisionModel[feature]['scoreCalculation']['datatype']=="enumeration":
                lookup=decisionModel[feature]['schemaMapping']['mappingScript']['lookup']
                for candidateValue in lookup:
                    if lookup[candidateValue]==solution[feature]:
                        solution[feature]=candidateValue

    return solutions
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
    ShouldHaveWeight=0.8
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
def queryBilder(featureRequirements, page, size):
    featureImpactFactores=getFeaturesImpactFactors(featureRequirements)
    page=(page-1)*size
    must_queries=[]
    could_should_queries=[]
    sort=[]
    script_score=""

    for reqFeature in featureImpactFactores:
        feature=reqFeature['feature']
        value=reqFeature['value']
        priority=reqFeature['priority']
        datatype=reqFeature['datatype']
        impactFactor=reqFeature['impactFactor']

        if priority=='must-have':
            if  datatype=='string':
                query , script= getStringQuery(value,"must-have",feature, impactFactor)
                must_queries.append(query)
                script_score=script_score+ script
            elif datatype=='currency':
                query , script= getCurrencyQuery(value,"must-have",feature,impactFactor)
                must_queries.append(query)
                script_score=script_score+ script
            elif datatype=='int' or datatype=='enumeration':
                query , script= getNumericQuery(value,"must-have", feature,impactFactor)
                must_queries.append(query)
                script_score=script_score+ script
            elif datatype=='geo_point':
                query , script= getGeoDistanceQuery(value,"must-have", feature,impactFactor)
                must_queries.append(query)
                script_score=script_score+ script
            elif datatype=='date':
                toDate=datetime.today().strftime('%Y-%m-%d')
                query , script= getDateQuery(value, toDate, priority, feature, impactFactor)
                must_queries.append(query)
                script_score=script_score+ script

        elif priority=='should-have' or priority=='could-have':
            if  datatype=='string':
                query , script= getStringQuery(value,"should-have or could-have",feature,impactFactor)
                could_should_queries.append(query)
                script_score=script_score+ script
            elif datatype=='currency':
                query , script= getCurrencyQuery(value,"should-have or could-have",feature,impactFactor)
                script_score=script_score+ script
            elif datatype=='int' or datatype=='enumeration':
                query , script= getNumericQuery(value,"should-have or could-have",feature,impactFactor)
                script_score=script_score+ script
            elif datatype=='geo_point':
                query , script= getGeoDistanceQuery(value,"should-have or could-have", feature,impactFactor)
                script_score=script_score+ script
            elif datatype=='date':
                toDate=datetime.today().strftime('%Y-%m-%d')
                query , script= getDateQuery(value, toDate, priority, feature, impactFactor)
                could_should_queries.append(query)
                script_score=script_score+ script

    query={
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": could_should_queries,
                        "filter": must_queries
                    }
                },
                "script_score": {
                    "script": {
                        "params": {
                        },
                        "inline": script_score+ "if( _score <0) {_score=0;} return _score;"
                    }
                },
                "boost_mode": "sum",
                "max_boost": 10
            }
        },
        "size": size,
        "from": page
    }

    #print(str(query).replace("\"","\\\"").replace("'","\""))

    return featureImpactFactores,query
#-------------------------------------------------------------------------------------------------------------
def getGeoDistanceQuery(geoPoint, priority, field , weight):
    query={}
    script=""
    if  geoPoint==[] or priority=="" or field=="":
        return query,script

    if priority=="must-have":
        query={
            "geo_distance": {
                "distance": str(geoPoint[2])+"km",
                field: {
                    "lat": geoPoint[1],
                    "lon": geoPoint[0]
                }
            }
        }
        lon=str(geoPoint[0])
        lat=str(geoPoint[1])
        distance=str(geoPoint[2])
        script="double origin_lon="+lon+";double origin_lat="+lat+";" \
              "double actualDistance=(Math.asin(Math.sqrt((Math.pow(Math.sin((Math.toRadians(doc[\"lat\"].value) - Math.toRadians(origin_lat)) / 2), 2)+ " \
              "Math.cos(Math.toRadians(origin_lat)) * Math.cos(Math.toRadians(doc[\"lat\"].value))* Math.pow(Math.sin((Math.toRadians(doc[\"lng\"].value) - " \
              "Math.toRadians(origin_lon)) / 2),2)))) * 12742); " \
              "_score= _score + ((1 - (actualDistance/"+distance+"))*0.001); "
    else:
        lon=str(geoPoint[0])
        lat=str(geoPoint[1])
        distance=str(geoPoint[2])
        weight=str(weight)
        script="double origin_lon="+lon+";double origin_lat="+lat+";" \
               "double actualDistance=(Math.asin(Math.sqrt((Math.pow(Math.sin((Math.toRadians(doc[\"lat\"].value) - Math.toRadians(origin_lat)) / 2), 2)+ " \
               "Math.cos(Math.toRadians(origin_lat)) * Math.cos(Math.toRadians(doc[\"lat\"].value))* Math.pow(Math.sin((Math.toRadians(doc[\"lng\"].value) - " \
               "Math.toRadians(origin_lon)) / 2),2)))) * 12742); " \
               "if (actualDistance<="+distance+") " \
                    "{_score= _score + ((1 - (actualDistance/"+distance+"))*"+weight+");} " \
               "else {_score= _score - ((1 - ("+distance+"/actualDistance))*"+weight+"); }"
    return query,script
#-------------------------------------------------------------------------------------------------------------
def getDateQuery(fromDate, toDate, priority, field, weight):
    query={}
    script=""

    if  fromDate=="" or toDate=="" or priority=="" or field=="":
        return query,script

    if priority=="must-have":
        query={
          "range": {
              field: {
                  "gte": fromDate,
                  "lt": toDate
              }
          }
        }
    else:
        query={
            "range": {
                field: {
                    "gte": fromDate,
                    "lt": toDate,
                    "boost": weight
                }
            }
        }

    return query,script
#-------------------------------------------------------------------------------------------------------------
def getNumericQuery(gte, priority, field, weight):
    query={}
    script=""

    if priority=="" or field=="":
        return query

    if priority=="must-have":
        query={
            "range": {
                field: {
                    "gte": gte
                }
            }
        }
        gte=str(gte)
        script=  "_score= _score+ ((1- "+gte+" / doc[\""+field+"\"].value)*0.001);"
    else:
        gte=str(gte)
        weight=str(weight)
        script=  "if (doc[\""+field+"\"].value>= "+gte+"){_score= _score+ ( (1- ("+gte+" / doc[\""+field+"\"].value)) * "+weight+");}"+\
                "else {_score= _score - ((1-(doc[\""+field+"\"].value/"+gte+"))* "+weight+");}"
    return query,script
#-------------------------------------------------------------------------------------------------------------
def getCurrencyQuery(lte, priority, field, weight):
    query={}
    script=""

    if priority=="" or field=="":
        return query,script

    if priority=="must-have":
        query={
            "range": {
                field: {
                    "lte": lte
                }
            }
        }
        gte=str(lte)
        script=  "_score= _score+ ((1- doc[\""+field+"\"].value/"+lte+")*0.001);"
    else:
        gte=str(lte)
        weight=str(weight)
        script=  "if ( doc[\""+field+"\"].value <= "+lte+" ) {_score= _score+ ((1- (doc[\""+field+"\"].value/"+lte+")) * "+weight+");}"+\
                "else{_score= _score - ((1- ("+lte+"/doc[\""+field+"\"].value)) * "+weight+");}"
    return query,script
#-------------------------------------------------------------------------------------------------------------
def getStringQuery(term, priority, field, weight):
    query={}
    script=""
    if priority=="" or field=="" or term=="":
        return query,script

    if priority=="must-have":
        query={
              "term": {
                  field: term
              }
          }
    else:
        query= {
              "match": {
                  field: {
                      "query": term,
                      "boost": weight
                  }
              }
          }
    return query,script
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
