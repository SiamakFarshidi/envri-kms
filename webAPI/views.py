from django.shortcuts import render
import glob
from os.path import isfile, join
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Index
import os
from os import walk
import json
import uuid
import numpy as np
import requests
from bs4 import BeautifulSoup
from spellchecker import SpellChecker

aggregares={
    "primaryCategory":{
        "terms":{
            "field": "primaryCategory.keyword",
            "size": 20,
        }
    },
    "provider":{
        "terms":{
            "field": "provider.keyword",
            "size": 20,
        }
    },
    "type":{
        "terms":{
            "field": "type.keyword",
            "size": 20,
        }
    },
    "architecturalStyle":{
        "terms":{
            "field": "architecturalStyle.keyword",
            "size": 20,
        }
    },
    "SSL_Support":{
        "terms":{
            "field": "SSL_Support.keyword",
            "size": 20,
        }
    },
    "supportedRequestFormats":{
        "terms":{
            "field": "supportedRequestFormats.keyword",
            "size": 20,
        }
    },
    "supportedResponseFormats":{
        "terms":{
            "field": "supportedResponseFormats.keyword",
            "size": 20,
        }
    },
    "authentication_Model":{
        "terms":{
            "field": "authentication_Model.keyword",
            "size": 20,
        }
    },
    "restrictedAccess":{
        "terms":{
            "field": "restrictedAccess.keyword",
            "size": 20,
        }
    },
}
#-----------------------------------------------------------------------------------------------------------------------
def aggregates(request):

    return  0
#-----------------------------------------------------------------------------------------------------------------------
def genericsearch(request):
    try:
        term = request.GET['term']
        term=term.rstrip()
        term=term.lstrip()
    except:
        term = ''

    try:
        page = request.GET['page']
    except:
        page = 0

    try:
        filter = request.GET['filter']
    except:
        filter = ''

    try:
        facet = request.GET['facet']
    except:
        facet = ''

    try:
        suggestedSearchTerm = request.GET['suggestedSearchTerm']
    except:
        suggestedSearchTerm = ''

    searchResults=getSearchResults(request, facet, filter, page, term)

    if(suggestedSearchTerm != ""):
        searchResults["suggestedSearchTerm"]=""
    else:
        suggestedSearchTerm=""
        if searchResults["NumberOfHits"]==0:
            suggestedSearchTerm= potentialSearchTerm(term)
            searchResults=getSearchResults(request, facet, filter, page, "*")
            searchResults["NumberOfHits"]=0
            searchResults["searchTerm"]=term
            searchResults["suggestedSearchTerm"]=suggestedSearchTerm

    return render(request,'webapi_results.html',searchResults)

#-----------------------------------------------------------------------------------------------------------------------
def getSearchResults(request, facet, filter, page, term):
    es = Elasticsearch("http://localhost:9200")
    index = Index('webapi', es)
    if filter!="" and facet!="":
        saved_list = request.session['filters']
        saved_list.append({"term": {facet+".keyword": filter}})
        request.session['filters'] = saved_list
    else:
        if 'filters' in request.session:
            del request.session['filters']
        request.session['filters']=[]

    page=(int(page)-1)*10

    result={}
    if term=="*" or term=="top10":
        result = es.search(
            index="webapi",
            body={
                "from" : page,
                "size" : 10,
                "query": {
                    "bool" : {
                        "must" : {
                            "match_all": {}
                        },
                        "filter": {
                            "bool" : {
                                "must" :request.session.get('filters')
                            }
                        }
                    }
                },
                "aggs":aggregares
            }
        )
    else:
        user_request = "some_param"
        query_body = {
            "from" : page, "size" : 10,
            "query": {
                "bool": {
                    "must": {
                        "multi_match" : {
                            "query": term,
                            "fields": [ "name", "description", "primaryCategory", "provider", "type", "architecturalStyle", "secondaryCategories", "authentication_Model", "supportedRequestFormats", "supportedResponseFormats"],
                            "type": "best_fields",
                            "minimum_should_match": "50%"
                        }
                    },
                    "filter": {
                        "bool" : {
                            "must" :request.session.get('filters')
                        }
                    }
                }
            },
            "aggs":aggregares
        }

        result = es.search(index="webapi", body=query_body)
    lstResults=[]
    for searchResult in result['hits']['hits']:
        lstResults.append(searchResult['_source'])
    #......................
    provider=[]
    primaryCategory=[]
    SSL_Support=[]
    architecturalStyle=[]
    type=[]
    supportedRequestFormats=[]
    supportedResponseFormats=[]
    authentication_Model=[]
    restrictedAccess=[]
    #......................
    for searchResult in result['aggregations']['restrictedAccess']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            pro={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            restrictedAccess.append (pro)
    #......................
    for searchResult in result['aggregations']['authentication_Model']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            pro={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            authentication_Model.append (pro)
    #......................
    for searchResult in result['aggregations']['supportedRequestFormats']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            pro={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            supportedRequestFormats.append (pro)
    #......................
    for searchResult in result['aggregations']['supportedResponseFormats']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            pro={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            supportedResponseFormats.append (pro)
    #......................
    for searchResult in result['aggregations']['provider']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            pro={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            provider.append (pro)
    #......................
    for searchResult in result['aggregations']['primaryCategory']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            cat={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            primaryCategory.append (cat)
    #......................
    for searchResult in result['aggregations']['SSL_Support']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            ssl={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            SSL_Support.append (ssl)
    #......................
    for searchResult in result['aggregations']['architecturalStyle']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            arch={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            architecturalStyle.append (arch)
    #......................
    for searchResult in result['aggregations']['type']['buckets']:
        if(searchResult['key']!="None" and searchResult['key']!="unknown" and searchResult['key']!="Unknown" and searchResult['key']!="Data" and searchResult['key']!="Unspecified" and searchResult['key']!="" and searchResult['key']!="N/A"):
            service={
                'key':searchResult['key'],
                'doc_count': searchResult['doc_count']
            }
            type.append (service)
    #......................
    facets={
        'provider':provider,
        'primaryCategory':primaryCategory,
        'SSL_Support':SSL_Support,
        'architecturalStyle':architecturalStyle,
        'type':type,
        'supportedRequestFormats':supportedRequestFormats,
        'supportedResponseFormats':supportedResponseFormats,
        'authentication_Model':authentication_Model,
        'restrictedAccess':restrictedAccess
    }

    numHits=result['hits']['total']['value']

    upperBoundPage=round(np.ceil(numHits/10)+1)
    if(upperBoundPage>10):
        upperBoundPage=11

    result={
              "facets":facets,
              "results":lstResults,
              "NumberOfHits": numHits,
              "page_range": range(1,upperBoundPage),
              "cur_page": (page/10+1),
              "searchTerm":term,
              "functionList": getAllfunctionList(request)
                  }
    return result
#-----------------------------------------------------------------------------------------------------------------------
def synonyms(term):
    response = requests.get('https://www.thesaurus.com/browse/{}'.format(term))
    soup = BeautifulSoup(response.text, 'html.parser')
    soup.find('section', {'class': 'css-191l5o0-ClassicContentCard e1qo4u830'})
    return [span.text for span in soup.findAll('a', {'class': 'css-1kg1yv8 eh475bn0'})]
#-----------------------------------------------------------------------------------------------------------------------
def potentialSearchTerm(term):
    alternativeSearchTerm=""

    spell = SpellChecker()
    searchTerm=term.split()
    alternativeSearchTerm=""
    for sTerm in searchTerm:
        alterWord=spell.correction(sTerm)
        if(alterWord!=""):
            alternativeSearchTerm= alternativeSearchTerm+" "+alterWord

    alternativeSearchTerm=alternativeSearchTerm.rstrip()
    alternativeSearchTerm=alternativeSearchTerm.lstrip()

    if alternativeSearchTerm==term:
        alternativeSearchTerm=""
        for sTerm in searchTerm:
            syn=synonyms(sTerm)
            if len(syn)>0:
                alterWord=syn[0]
                alternativeSearchTerm= alternativeSearchTerm+" "+alterWord

    alternativeSearchTerm=alternativeSearchTerm.rstrip()
    alternativeSearchTerm=alternativeSearchTerm.lstrip()

    return alternativeSearchTerm
#-----------------------------------------------------------------------------------------------------------------------
# Create your views here.
def indexingpipeline(request):
    es = Elasticsearch("http://localhost:9200")
    index = Index('webapi', es)

    if not es.indices.exists(index='webapi'):
        index.settings(
            index={'mapping': {'ignore_malformed': True}}
        )
        index.create()
    else:
        es.indices.close(index='webapi')
        put = es.indices.put_settings(
            index='webapi',
            body={
                "index": {
                    "mapping": {
                        "ignore_malformed": True
                    }
                }
            })
        es.indices.open(index='webapi')

    root=(os. getcwd()+"/webAPI/DB/")
    print (root)
    for path, subdirs, files in os.walk(root):
        for name in files:
            print(name)
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)
            res = es.index(index="webapi", id= indexfile['url'], body=indexfile)
            es.indices.refresh(index="webapi")

    return render(request,'webcontent_results.html',{})

#-----------------------------------------------------------------------------------------------------------------------
def open_file(file):
    read_path = file
    with open(read_path, "r", errors='ignore') as read_file:
        print(read_path)
        data = json.load(read_file)
        return data
#-----------------------------------------------------------------------------------------------------------------------
def getAllfunctionList(request):
    if not 'BasketURLs' in request.session or not request.session['BasketURLs']:
        request.session['BasketURLs'] = []
    if not 'MyBasket' in request.session or not request.session['MyBasket']:
        request.session['MyBasket'] = []

    functionList=""
    saved_list = request.session['MyBasket']
    for item in saved_list:
        functionList= functionList+r"modifyCart({'operation':'add','type':'"+item['type']+"','title':'"+item['title']+"','url':'"+item['url']+"','id':'"+item['id']+"' });"
    return functionList
