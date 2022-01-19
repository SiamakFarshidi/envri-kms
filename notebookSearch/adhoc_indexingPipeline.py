from django.forms.widgets import NullBooleanSelect, Widget
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import simplejson
from urllib.request import urlopen
import urllib
from datetime import datetime
from elasticsearch import Elasticsearch
from glob import glob
from elasticsearch_dsl import Search, Q, Index
from elasticsearch_dsl.query import MatchAll
from django.core import serializers
import numpy as np
import json
import uuid

# ----------------------------------------------------------------
def open_file(file):
    read_path = file
    with open(read_path, "r", errors='ignore') as read_file:
        data = json.load(read_file)
    return data
# ----------------------------------------------------------------
def indexingpipeline():
    es = Elasticsearch("http://localhost:9200")
    index = Index('notebooks', es)

    if not es.indices.exists(index='notebooks'):
        index.settings(
            index={'mapping': {'ignore_malformed': True}}
        )
        index.create()
    else:
        es.indices.close(index='notebooks')
        put = es.indices.put_settings(
            index='notebooks',
            body={
                "index": {
                    "mapping": {
                        "ignore_malformed": True
                    }
                }
            })
        es.indices.open(index='notebooks')

    indexFile= open('notebooks.json',"r")
    dataset_json = json.loads(r''+indexFile.read())

    for record in dataset_json["hits"]:
        newRecord={
           'name': record['name'],
           'description': record['description'],
           'html_url': record['html_url'],
           'git_url': record['git_url'],
           'language': record['language'],
           'stars': record['stars'],
           'size': record['size']
        }

        res = es.index(index="notebooks", id= uuid.uuid4(), body=newRecord)
        es.indices.refresh(index="notebooks")
# ----------------------------------------------------------------
indexingpipeline()