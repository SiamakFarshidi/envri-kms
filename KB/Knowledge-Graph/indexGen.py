from knowledgeGraph import get_entity, get_relation, show
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, Index
import os
from elasticsearch_dsl.query import MatchAll
import re
import sys
import csv
import json
import glob
from inspect import getmembers, isfunction
from modulefinder import ModuleFinder
import language_tool_python
tool = language_tool_python.LanguageTool('en-US')
import spacy
spacy_nlp  = spacy.load('en_core_web_sm')
similarity_threshold=0.8
#-----------------------------------------------------------------------------------------------------------------------
def pythonLibraries(filePath):
    lstLibraries=set()
    finder = ModuleFinder()
    finder.run_script(filePath)
    for name, mod in finder.modules.items():
        #print('%s: ' % name, end='')
        lstLibraries.add(name)
        #print(','.join(list(mod.globalnames.keys())[:3]))
    #print('-'*50)
    #print('Modules not imported:')
    #print('\n'.join(finder.badmodules.keys()))
    return lstLibraries
#-----------------------------------------------------------------------------------------------------------------------
def cleanhtml(raw_html):
    CLEANR = re.compile('<.*?>')
    cleantext = re.sub(CLEANR, '', raw_html)
    cleantext=cleantext.replace('\n','').split('.')

    lstText=set()
    for txt in cleantext:
        if len(txt)>20:
            lstText.add(re.sub('[\W ]+', ' ', txt))

    cleantext=""
    for txt in lstText:
        cleantext += txt.strip()+". "

    return cleantext, lstText
#-----------------------------------------------------------------------------------------------------------------------
def addExtraContextualInformation(description):
    lstextra=[]
    ontoClasses = open_file("classessOfOntologies.json")
    description=description.lower()
    for cls in ontoClasses:
        for onto in ontoClasses[cls]:
            onto=onto.lower()
            if (onto in description) or (getSimilarity(onto, description) > similarity_threshold):
                lstextra.append(onto)
    return str(lstextra)
#-----------------------------------------------------------------------------------------------------------------------
def indexGen():
    maxInt = sys.maxsize
    while True:
        # decrease the maxInt value by factor 10
        # as long as the OverflowError occurs.
        try:
            csv.field_size_limit(maxInt)
            break
        except OverflowError:
            maxInt = int(maxInt/10)
    with open('NotebookDatasets/text_code_URL.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                #print(f'Column names are {", ".join(row)}')
                line_count += 1
            else:
                line_count += 1

                name= re.sub('[\W_ ]+', ' ', row[1]).replace('ipynb','')
                title= re.sub('[\W_ ]+', ' ', row[7])

                description,lstDescrition=cleanhtml(row[6]+row[8])
                entitiesOfKnowledgeGraph= generate_knowledgeGraph(lstDescrition)
                url=row[9]
                temp_data = {}
                temp_data["name"] = name
                temp_data["full_name"] = title
                temp_data["stargazers_count"] = 0
                temp_data["forks_count"] = 0
                temp_data["description"] = description
                temp_data["id"] = row[0]
                temp_data["size"] = row[5]
                temp_data["language"] = row[2]
                temp_data["html_url"] = url
                temp_data["git_url"] = url
                temp_data["script"] = extractLibs(row[10])
                temp_data["entities"]= entitiesOfKnowledgeGraph
                temp_data["extra"]= addExtraContextualInformation(description)
                filename= re.sub(r'[^A-Za-z0-9 ]+', '',name)+"_"+"_"+str( row[5])
                f = open("index_files/"+filename+".json", 'w+')
                f.write(json.dumps(temp_data))
                f.close()
                print(url)
#-----------------------------------------------------------------------------------------------------------------------
def extractLibs(PyScript):
    libraries=set()
    strLibSet=""
    patterns = ["import (.*?) as", "from (.*?) import", "def (.*?)\(","from.* import (.*?)$", "class (.*?):"]
    for line in PyScript.splitlines():
        for pattern in patterns:
            if type(re.search(pattern, line))!=type(None):
                substring = re.search(pattern, line).group(1)
                lst=substring.split(',')
                for item in lst:
                    if len(item)>1:
                        libraries.add(item.strip())

    for lib in libraries:
        strLibSet += lib + " "

    return strLibSet
#-----------------------------------------------------------------------------------------------------------------------
def generate_knowledgeGraph(lstText):
    lstEntities=set()
    entities=""
    for text in lstText:
        text=text.strip()+"."
        #if(isCorrectSentence(text)):
        #print("\n --------------------------------- \n")
        #print(text)
        if len(text)>40:
            output_entitiy = get_entity(text)
            output_relation = get_relation(text)
            if output_entitiy and output_relation and output_entitiy[0] and output_entitiy[1]:
                tupple=(output_entitiy, output_relation)
                lstEntities.add(tupple)
        #show(text)
        #s=input()
    for entity in lstEntities:
        entities += str(entity)+ " "
    return entities
#-----------------------------------------------------------------------------------------------------------------------
def isCorrectSentence(sentence):
    matches = tool.check(sentence)
    if len(matches):
        return False
    return True
#-----------------------------------------------------------------------------------------------------------------------
def indexingpipeline():
    cnt=0
    root=(os. getcwd()+"/Analysis/Testset")
    print(root)
    for path, subdirs, files in os.walk(root):
        for name in files:
            cnt=cnt+1
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)
            elasticSearchIndexer('notebooks_test',indexfile["git_url"], indexfile)
            print(str(cnt)+" recode added! \n")
#-----------------------------------------------------------------------------------------------------------------------
def elasticSearchIndexer(IndexName, ID, content):
    es = Elasticsearch("http://localhost:9200")
    index = Index(IndexName, es)

    if not es.indices.exists(index=IndexName):
        index.settings(
            index={'mapping': {'ignore_malformed': True}}
        )
        index.create()
    else:
        es.indices.close(index=IndexName)
        put = es.indices.put_settings(
            index=IndexName,
            body={
                "index": {
                    "mapping": {
                        "ignore_malformed": True
                    }
                }
            })
    es.indices.open(index=IndexName)
    res = es.index(index=IndexName, id= ID, body=content)
    es.indices.refresh(index=IndexName)
#-----------------------------------------------------------------------------------------------------------------------
def open_file(file):
    read_path = file
    with open(read_path, "r", errors='ignore') as read_file:
        data = json.load(read_file)
    return data
#-----------------------------------------------------------------------------------------------------------------------
def removeAllFiles():
    directories=["Low_description_files", "No_description_files", "No_entity_files","No_script_files", "Perfect_files", "No_extra_files"]
    for dir in directories:
        files = glob.glob('Analysis/'+dir+'/*')
        for f in files:
            os.remove(f)

#-----------------------------------------------------------------------------------------------------------------------
def classifyIndexes():

    lstLowDescriptionFiles=[]
    lstNoDescriptionFiles=[]
    lstNoEntityFiles=[]
    lstNoScriptFiles=[]
    lstPerfectFiles=[]
    lstNoExtraFiles=[]

    root=(os. getcwd()+"/index_files/")
    for path, subdirs, files in os.walk(root):
        for name in files:
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)

            if len(indexfile['description'])>0 and len(indexfile['description'])<50 :
                lstLowDescriptionFiles.append(name)

            if indexfile['description']=="":
                lstNoDescriptionFiles.append(name)

            if indexfile['entities']=="":
                lstNoEntityFiles.append(name)

            if indexfile['script']=="":
                lstNoScriptFiles.append(name)

            if len(indexfile['description'])>50 and indexfile['entities']!="" and  indexfile['script']!="":
                lstPerfectFiles.append(name)

            extra=str(indexfile['extra']).replace('\"','').replace('[','').replace(']','').replace(',','').replace('\'','')
            if extra=='':
                lstNoExtraFiles.append(name)

    print("lstLowDescriptionFiles: " + str(len(lstLowDescriptionFiles)))
    print("lstNoDescriptionFiles: " + str(len(lstNoDescriptionFiles)))
    print("lstNoEntityFiles: " + str(len(lstNoEntityFiles)))
    print("lstNoScriptFiles: " + str(len(lstNoScriptFiles)))
    print("lstPerfetcFiles: " + str(len(lstPerfectFiles)))
    print("lstNoExtraFiles: " + str(len(lstNoExtraFiles)))

    removeAllFiles()

    for file in lstLowDescriptionFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/Low_description_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()
        elasticSearchIndexer('lowdescription', indexfile["git_url"], indexfile)

    for file in lstNoDescriptionFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_description_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()
        elasticSearchIndexer('nodescription', indexfile["git_url"], indexfile)

    for file in lstNoEntityFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_entity_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()
        elasticSearchIndexer('noentity', indexfile["git_url"], indexfile)

    for file in lstNoScriptFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_script_files/"+file, 'w')
        elasticSearchIndexer('noscript', indexfile["git_url"], indexfile)
        f.write(json.dumps(indexfile))
        f.close()

    for file in lstPerfectFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/Perfect_files/"+file, 'w')
        f.write(json.dumps(indexfile))
        f.close()
        elasticSearchIndexer('perfect', indexfile["git_url"], indexfile)

    for file in lstNoExtraFiles:
        indexfile = open_file(root+file)
        f = open("Analysis/No_extra_files/"+file, 'w')
        indexfile['extra']= str(indexfile['extra']).replace('\"','').replace('[','').replace(']','').replace(',','').replace('\'','')
        f.write(json.dumps(indexfile))
        f.close()
        elasticSearchIndexer('extra', indexfile["git_url"], indexfile)
#-----------------------------------------------------------------------------------------------------------------------
def extract_queries():
    nonQueries=["it", "they", "we", "us", "them", "our", "is", "be", "be you", "be we", "www", "that",
                "have","have you", "one", "be who", "others", "make we", "have which", "need we", "be we",
                "the", "be that", "which", "let s", "be which", "etc", "be us", "be s", "way", "need that",
                "e.",  "use that","me", "be model", "use s", "do that", "be image", "call that", "m you", "1e", "some",
                "{}", "get", "you", "when", "where", "why","typical",""]
    queries={}
    root=(os. getcwd()+"/Analysis/")
    for path, subdirs, files in os.walk(root):
        for name in files:
            indexfile= os.path.join(path, name)
            print(indexfile)

            indexfile = open_file(indexfile)

            entities=(indexfile['entities'].replace('(','').replace(')','').replace('\'','')).split(',')
            for entity in entities:
                if entity not in queries:
                    queries[entity.lower()]=1
                else:
                    queries[entity] +=1

            entities=(indexfile['script'].replace('.',' ').replace('_',' ').replace('-',' ')).split(' ')

            for entity in entities:
                if entity not in queries:
                    queries[entity.lower()]=1
                else:
                    queries[entity] +=1

            entities=(indexfile['extra'].replace('[','').replace(']','').replace('\'','').replace(',','')).split(' ')

            for entity in entities:
                if entity not in queries:
                    queries[entity.lower()]=1
                else:
                    queries[entity] +=1

    sorted_dictionaries = sorted(queries.items(), key=lambda x: x[1])

    queries.clear()
    queries={}
    for entity in sorted_dictionaries:
        ent=entity[0].strip()
        if entity[1]>2 and len(ent)>1 and not ent.isnumeric():
            if ent not in nonQueries:
                queries[ent]=entity[1]

    f = open("Analysis/queries.json", 'w')
    f.write(json.dumps(queries))
    f.close()
#-----------------------------------------------------------------------------------------------------------------------
def get_cosine_sim(query, text):
    w1= spacy_nlp(query.lower())
    w2= spacy_nlp(text.lower())
    similarity=w1.similarity(w2)
    #print(similarity)
    return similarity
#-----------------------------------------------------------------------------------------------------------------------
def get_jaccard_sim(str1, str2):
    a = set(str1.split())
    b = set(str2.split())
    c = a.intersection(b)
    if ((len(a) + len(b) - len(c))>0) :
        sim = float(len(c)) / (len(a) + len(b) - len(c))
    else :
        sim=0
    return sim

#-----------------------------------------------------------------------------------------------------------------------
def calculateMetrics(query, index, queryFields, positives, negatives):
    lstResults=getSearchResults(query,index, queryFields)
    results=[]

    TP=0
    FP=0
    TN=0
    FN=0

    for res in lstResults:
        result=res['_source']
        results.append(result['git_url'])

    for result in results:

        if result in positives and result not in negatives:
            TP=TP+1

        elif result not in positives and result in negatives:
            FP=FP+1

    for neg in negatives:
        if neg not in results:
            TN=TN+1

    for pos in positives:
        if pos not in results:
            FN=FN+1

    return   TP,FP, TN, FN
#----------------------------------------------------------------------------------------------------------------------- Pipeline
def calculate_similarity(filePath,index):
    queries = open_file("Analysis/queries.json")

    total_sim=0

    for query in queries:
        positives, negatives= getPositiveNagativeSets(query, 0.5, filePath)

        TP,FP, TN, FN =calculateMetrics(query,index, ['description', 'script', 'entities', 'extra'], positives, negatives)

        print("Query: " + query)
        print("TP : " + str(TP))
        print("FP : " + str(FP))
        print("TN : " + str(TN))
        print("FN : " + str(FN))

#-----------------------------------------------------------------------------------------------------------------------
def getSearchResults(query, index, searchFields):
    es = Elasticsearch("http://localhost:9200")
    user_request = "some_param"
    query_body = {
        "query": {
            "bool": {
                "must": {
                    "multi_match" : {
                        "query": query,
                        "fields": searchFields,
                        "type": "best_fields",
                        "minimum_should_match": "100%"
                    }
                },
            }
        },
    }
    results = es.search(index=index, body=query_body)

    return results['hits']['hits']
#-----------------------------------------------------------------------------------------------------------------------
def indexingSelectedIndexes(filePath,index):
    root=(os. getcwd()+"/Analysis/"+filePath+"/")
    for path, subdirs, files in os.walk(root):
        for name in files:
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)
            elasticSearchIndexer(index, indexfile["git_url"], indexfile)
            print("Added " + name)

#-----------------------------------------------------------------------------------------------------------------------
def getPotentialQueries(text,filename):
    lstqueries=[]
    indexfile = open_file(os. getcwd()+filename)

    for query in indexfile:
        matched=False
        if len(query.split()) == 1:
            lsttext=text.split()
            for txt in lsttext:
                if (query not in lstqueries) and (query==txt or get_jaccard_sim(query,txt)>0.5):
                    lstqueries.append(query)
                    matched=True
                    break
        if not(matched):
            lsttext= text.split('.')
            for txt in lsttext:
                if (query not in lstqueries) and  (get_jaccard_sim(query,txt)>0.5):

                    lstqueries.append(query)
                    matched=True
                    break

    return lstqueries
#-----------------------------------------------------------------------------------------------------------------------
def findPotentialQueries():
    lstTestset=set()
    directories=["Low_description_files", "No_description_files", "No_entity_files","No_script_files","No_extra_files", "Perfect_files"]
    cnt=1
    for dir in directories:
        root=(os. getcwd()+"/Analysis/"+dir+"/")
        for path, subdirs, files in os.walk(root):
            for name in files:
                if name not in lstTestset:
                    lstTestset.add(name)
                    indexfile= os.path.join(path, name)
                    indexfile = open_file(indexfile)
                    f = open("Analysis/Testset/"+name, 'w')
                    indexfile["label"]= dir
                    #---------------------------------------------------------------------------------------------------
                    allQueries=[]

                    description_queries=getPotentialQueries(indexfile["description"], "/Analysis/queries.json")

                    for query in description_queries:
                        if query not in allQueries:
                            allQueries.append(query)
                        else:
                            description_queries.remove(query)

                    indexfile["potential_description_queries"]=description_queries
                    indexfile["potential_description_queries_len"]=len(description_queries)

                    script_queries=getPotentialQueries(indexfile["script"], "/Analysis/queries.json")

                    for query in script_queries:
                        if query not in allQueries:
                            allQueries.append(query)
                        else:
                            script_queries.remove(query)

                    indexfile["potential_script_queries"]=script_queries
                    indexfile["potential_script_queries_len"]=len(script_queries)

                    entities_queries=getPotentialQueries(str(indexfile["entities"]), "/Analysis/queries.json")

                    for query in entities_queries:
                        if query not in allQueries:
                            allQueries.append(query)
                        else:
                            entities_queries.remove(query)

                    indexfile["potential_entities_queries"]=entities_queries
                    indexfile["potential_entities_queries_len"]=len(entities_queries)

                    txtExtra=str(indexfile["extra"]).replace("\'","").replace("[","").replace("]","").replace("\'","")
                    extra_queries=getPotentialQueries((txtExtra), "/Analysis/queries.json")
                    for query in extra_queries:
                        if query not in allQueries:
                            allQueries.append(query)
                        else:
                            extra_queries.remove(query)

                    indexfile["potential_extra_queries"]=extra_queries
                    indexfile["potential_extra_queries_len"]=len(extra_queries)

                    indexfile["all_components_potential_queries_len"]=len(allQueries)
                    #---------------------------------------------------------------------------------------------------

                    elasticSearchIndexer('testset', indexfile["git_url"], indexfile)
                    f.write(json.dumps(indexfile))
                    f.close()
                    print(str(cnt)+" : "+ dir+ " : " + name)
                    cnt=cnt+1
#-----------------------------------------------------------------------------------------------------------------------
def getPositiveNagativeSets(query, threshold, filePath):
    lstpositives=set()
    lstnegatives=set()
    root=(os. getcwd()+"/Analysis/"+filePath+"/")

    for path, subdirs, files in os.walk(root):
        for name in files:
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)
            text=indexfile['description']+indexfile['script']+indexfile['entities']+indexfile['extra']

            if get_jaccard_sim(query, text) >= threshold:
                lstpositives.add(indexfile['git_url'])
            else:
                lstnegatives.add(indexfile['git_url'])

    return list(lstpositives), list(lstnegatives)
#-----------------------------------------------------------------------------------------------------------------------
def experimentDB():

    for query in indexfile:
        print(query)
        results=getSearchResults(query, "testset", ['description', 'script', 'entities', 'extra'])
        if len(results)>0:
            results=results[0]['_source']
            text= str(results['description'])+str(results['script'])+str(results['entities'])+str(results['extra'])
            print(get_jaccard_sim(query, text))
        print("--------------------")
#-----------------------------------------------------------------------------------------------------------------------
def getMetrics(testFieldQueries,testField, searchSpace):
    TP=0
    FP=0
    FN=0
    TN=0

    queries = open_file(os. getcwd()+"/Analysis/queries.json")

    for query in queries:
        if query not in searchSpace:
            TN=TN+1

    for query in testFieldQueries:
        if query in testField:
            TP=TP+1
        else:
            FP=FP+1

    FN=len(queries)-(TP+FP+TN)
    return str(TP), str(FP), str(TN),str(FN)
#-----------------------------------------------------------------------------------------------------------------------
def calculateStatistics():
    root=(os. getcwd()+"/Analysis/Testset")
    queries = open_file(os. getcwd()+"/Analysis/queries.json")
    csvFile="url,label, descriptions, scripts, entities, extra, all ,names, TP_desc, FP_desc, TN_desc,FN_desc,  TP_script, FP_script, TN_script,FN_script,  TP_ent, FP_ent, TN_ent,FN_ent , TP_extra, FP_extra, TN_extra, FN_extra \n"
    cnt=1
    for path, subdirs, files in os.walk(root):
        for name in files:
            print(cnt)
            print(name)
            cnt=cnt+1
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)

            TP=0
            FP=0
            FN=0
            TN=0

            description=indexfile['description'].split()
            script=indexfile['script'].split()
            entities=indexfile['entities'].split()
            extra=indexfile['extra'].split()


            TP_desc, FP_desc, TN_desc,FN_desc = getMetrics(indexfile['potential_description_queries'],indexfile['description'],
                                       [*indexfile['potential_description_queries'],*description, *script, *entities, *extra] )

            TP_script, FP_script, TN_script,FN_script = getMetrics(indexfile['potential_script_queries'],indexfile['script'],
                                       [*indexfile['potential_description_queries'], *indexfile['potential_script_queries'],*description, *script, *entities, *extra] )

            TP_ent, FP_ent, TN_ent,FN_ent = getMetrics(indexfile['potential_entities_queries'],indexfile['entities'],
                                       [*indexfile['potential_description_queries'], *indexfile['potential_entities_queries'],*description, *script, *entities, *extra] )

            TP_extra, FP_extra, TN_extra, FN_extra = getMetrics(indexfile['potential_extra_queries'],indexfile['extra'],
                                       [*indexfile['potential_description_queries'], *indexfile['potential_extra_queries'], *description, *script, *entities, *extra] )


            row =indexfile['html_url']+","+ \
                 indexfile['label']+','+ \
                 str(indexfile['potential_description_queries_len'])+','+ \
                 str(indexfile['potential_script_queries_len'])+','+ \
                 str(indexfile['potential_entities_queries_len'])+','+ \
                 str(indexfile['potential_extra_queries_len'])+','+ \
                 str(indexfile['all_components_potential_queries_len'])+','+ \
                 indexfile['name']+','+ \
                 TP_desc+','+ \
                 FP_desc+','+ \
                 TN_desc+','+ \
                 FN_desc+','+ \
                 TP_script+','+ \
                 FP_script+','+ \
                 TN_script+','+ \
                 FN_script+','+ \
                 TP_ent+','+ \
                 FP_ent+','+ \
                 TN_ent+','+ \
                 FN_ent +','+ \
                 TP_extra+','+ \
                 FP_extra+','+ \
                 TN_extra+','+ \
                 FN_extra +'\n'

            csvFile=csvFile+row

    f = open("Analysis/analysis.csv", 'w')
    f.write(csvFile)
    f.close()

#-----------------------------------------------------------------------------------------------------------------------

def totalCalculateStatistics():
    root=(os. getcwd()+"/Analysis/Testset")
    queries = open_file(os. getcwd()+"/Analysis/queries.json")
    csvFile="url,label, descriptions, scripts, entities, extra, all ,names, TP,FP, TN, FN \n"
    cnt=1
    for path, subdirs, files in os.walk(root):
        for name in files:
            print(cnt)
            print(name)
            cnt=cnt+1
            indexfile= os.path.join(path, name)
            indexfile = open_file(indexfile)

            TP=0
            FP=0
            FN=0
            TN=0

            for query in queries:
                if ((query  not in indexfile['potential_description_queries']) and (query  not in indexfile['description'].split())) and \
                        ((query not in indexfile['potential_script_queries']) and (query not in indexfile['script'].split())) and \
                        ((query not in indexfile['potential_entities_queries']) and (query not in indexfile['entities'].split())) and \
                        ((query  not in indexfile['potential_extra_queries']) and (query not in indexfile['extra'].split())):
                    TN=TN+1
                else:
                    FN=FN+1

            for query in indexfile['potential_description_queries']:
                if query in indexfile['description']:
                    TP=TP+1
                else:
                    FP=FP+1

            for query in indexfile['potential_script_queries']:
                if query in indexfile['script']:
                    TP=TP+1
                else:
                    FP=FP+1

            for query in indexfile['potential_entities_queries']:
                if query in indexfile['entities']:
                    TP=TP+1
                else:
                    FP=FP+1

            for query in indexfile['potential_extra_queries']:
                if query in indexfile['extra']:
                    TP=TP+1
                else:
                    FP=FP+1

            row =indexfile['html_url']+","+\
                 indexfile['label']+','+ \
                 str(indexfile['potential_description_queries_len'])+','+ \
                 str(indexfile['potential_script_queries_len'])+','+ \
                 str(indexfile['potential_entities_queries_len'])+','+ \
                 str(indexfile['potential_extra_queries_len'])+','+ \
                 str(indexfile['all_components_potential_queries_len'])+','+ \
                 indexfile['name']+','+ \
                 str (TP)+","+ \
                 str(FP)+","+ \
                 str(TN)+","+ \
                 str((TP+FP+TN)-len(queries)) +"\n"


            csvFile=csvFile+row

    f = open("Analysis/analysis.csv", 'w')
    f.write(csvFile)
    f.close()
#----------------------------------------------------------------------------------------------------------------------- Pipeline
#indexGen()
#indexingpipeline()
#----------------------------------------------------------------------------------------------------------------------- Testing and analysis
#classifyIndexes()
#extract_queries()
#findPotentialQueries()
#calculateStatistics()
#-----------------------------------------------------------------------------------------------------------------------
#calculate_similarity('Testset','testset')
#addExtraContextualInformation("")
indexingpipeline()