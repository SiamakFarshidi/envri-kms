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

import Github

ACCESS_TOKEN_Github= "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"
ACCESS_TOKEN_Gitlab= "glpat-RLNz1MhmyeR7jcox_dyA"

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
def search_repository_github(keywords):
    g = Github(ACCESS_TOKEN_Github)
    keywords = [keyword.strip() for keyword in keywords.split(',')]
    keywords.append("notebook")
    query = '+'.join(keywords)+ '+in:readme+in:description'
    result = g.search_repositories(query, 'stars', 'desc')
    cnt=0
    data=[]
    iter_obj = iter(result)
    while True:
        try:
            cnt=cnt+1
            repo = next(iter_obj)
            new_record= {
                "id":cnt,
                "name": repo.full_name,
                "description": re.sub(r'[^A-Za-z0-9 ]+', '',repo.description),
                "html_url":repo.html_url,
                "git_url": repo.clone_url,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "size": repo.size,
            }
            if new_record["language"]=="Jupyter Notebook" and new_record not in data:
                data.append(new_record)
        except StopIteration:
            break
        except RateLimitExceededException:
            continue
    data=(json.dumps({"results_count": result.totalCount,"hits":data}).replace("'",'"'))
    return  json.loads(data)
# ----------------------------------------------------------------


response_data=search_repository_github('')

print(response_data)

indexFile= open("notebooks.json","w+")
indexFile.write(json.dumps(response_data))
indexFile.close()


indexingpipeline()
