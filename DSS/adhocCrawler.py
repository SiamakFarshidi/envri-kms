import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import colorama
import json
import time
import urllib3
import re
import datefinder
import spacy
from spacy import displacy
from collections import Counter
import en_core_web_sm
import lxml.html
import validators
nlp = en_core_web_sm.load()
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Index
import uuid
import os

#-----------------------------------------------------------------------------------------------------------------------
# init the colorama module
colorama.init()
GREEN = colorama.Fore.GREEN
GRAY = colorama.Fore.LIGHTBLACK_EX
RESET = colorama.Fore.RESET
YELLOW = colorama.Fore.YELLOW
# initialize the set of links (unique links)
internal_urls = set()
external_urls = set()
permitted_urls=set()
urllib3.disable_warnings()
#-----------------------------------------------------------------------------------------------------------------------
# number of urls visited so far will be stored here
max_urls=999999
config={}
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent':  'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Cookie': 'PHPSESSID=r2t5uvjq435r4q7ib3vtdjq120',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'Keep-Alive': '300',
    'Accept-Language': 'en-us,en;q=0.5',
    'Accept-Encoding': 'gzip,deflate',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
}
#-----------------------------------------------------------------------------------------------------------------------
def openCrawlerConfig(webSiteEntity):
    crawlerConfig = open('crawlerConfig.json',"r")
    crawlerConfig = json.loads(r''+crawlerConfig.read())
    NewConfig={
        "permitted_urls_rules":crawlerConfig[webSiteEntity]['permitted_urls_rules'],
        "denied_urls_rules":crawlerConfig[webSiteEntity]['denied_urls_rules'],
        "features":crawlerConfig[webSiteEntity]['features'],
        "seed":crawlerConfig[webSiteEntity]['seed'],
        "decision_model":crawlerConfig[webSiteEntity]['decision_model'],
    }
    print("The new configurations have been set!")
    return NewConfig
#-----------------------------------------------------------------------------------------------------------------------
def is_valid(url):
    """
    Checks whether `url` is a valid URL.
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)
#-----------------------------------------------------------------------------------------------------------------------
def get_all_website_links(url):
    """
    Returns all URLs that is found on `url` in which it belongs to the same website
    """
    # all URLs of `url`
    urls = set()
    # domain name of the URL without the protocol
    domain_name = urlparse(url).netloc
    soup=""
    cnt=0
    while soup=='':
        try:
            soup = BeautifulSoup(requests.get(url,verify=True, timeout=5, headers=headers).content, "html.parser",from_encoding="iso-8859-1")
            break
        except:
            print("Connection refused by the server...")
            time.sleep(0.2)
            cnt=cnt+1

            if cnt==20:
                return urls
            continue
    cnt=0

    for a_tag in soup.findAll("a"):
        href = a_tag.attrs.get("href")

        if href == "" or href is None:
            # href empty tag
            continue

        # join the URL if it's relative (not absolute link)
        href = urljoin(url, href)
        parsed_href = urlparse(href)
        # remove URL GET parameters, URL fragments, etc.
        href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path

        if not is_valid(href):
            # not a valid URL
            continue
        if href in internal_urls:
            # already in the set
            continue
        if domain_name not in href:
            continue

        accessPermitted=True
        for condition in config["denied_urls_rules"]:
            if (len(re.findall(condition, href))>0):
                accessPermitted=False

        if(not accessPermitted):
            continue

        urls.add(href)
        internal_urls.add(href)

        for condition in config["permitted_urls_rules"]:
            if (len(re.findall(condition, href))>0) and href not in permitted_urls:
                permitted_urls.add(href)
                print(f"{GREEN}[{len(permitted_urls)}] Permitted link: {href}{RESET}")
                indexWebpage(href)
    return urls
#-----------------------------------------------------------------------------------------------------------------------
def extractHTML(url):
    soup=""
    cnt=0
    while soup=='':
        try:
            soup = BeautifulSoup(requests.get(url,verify=True, timeout=5, headers=headers).content, "html.parser",from_encoding="iso-8859-1")
            break
        except:
            print("Connection refused by the server...")
            time.sleep(0.2)
            cnt=cnt+1

            if cnt==20:
                break
            continue
    if len(soup)>0 and len(soup.find_all('body'))>0:
        return soup
    else:
        return ""
#-----------------------------------------------------------------------------------------------------------------------
def extractTitle(html):
    lstTitle=[]
    for title in html.find_all('title'):
        lstTitle.append(title.get_text())
    return lstTitle
#-----------------------------------------------------------------------------------------------------------------------
def indexWebsite(website):
    global max_urls
    global config

    config=openCrawlerConfig(website)
    url=config["seed"]

    permitted_urls.clear()
    internal_urls.clear()
    external_urls.clear()
    total_urls_visited=0

    uniquelinks=set()
    uniquelinks.add(url)

    while total_urls_visited < max_urls and uniquelinks:
        url=uniquelinks.pop()
        total_urls_visited += 1
        print(f"{YELLOW}[*] Crawling: {url}{RESET}")
        links = get_all_website_links(url)
        for link in links:
            uniquelinks.add(link)
#-----------------------------------------------------------------------------------------------------------------------
def printResults():
    print("[+]  Total Internal links: ", len(internal_urls))
    print("[+]  Total External links: ", len(external_urls))
    print("[+] Total Permitted links: ", len(permitted_urls))
    print("[+]            Total URLs: ", len(external_urls) + len(internal_urls))
    print("[+]  Maximum Crawled URLs: ", max_urls)
#-----------------------------------------------------------------------------------------------------------------------
def strippedText(text):
    if type(text)!=None and type(text)==str:
        text=text.replace('\n',' ')
        text=text.replace('\r','')
        text=text.replace('\t','')
        text=text.replace('  ','')
        text=text.replace('..','.')
    return text
#-----------------------------------------------------------------------------------------------------------------------
def remove_tags(raw_html):
    text=""
    if(type(raw_html)!= type(None)):
        text= BeautifulSoup(raw_html, "lxml").text
        text= "\n".join([s for s in text.split("\n") if s])
    return text
#-----------------------------------------------------------------------------------------------------------------------
def filterByDatatype(value,datatype):
    if datatype=="currency" or datatype=="int" or datatype=="decimal":
        trim = re.compile(r'[^\d.,]+')
        lstvalue=value.split()
        for val in lstvalue:
            value = trim.sub('', val)
            if(value):
                return value
    elif datatype=="char" or datatype=="text":
        return strippedText(value)
    elif datatype=="zipcode":
        p = re.compile(r'\d{4} [A-Za-z]{2}')
        value=p.findall(value)
        if len(value)>0:
            return value[0]
    return value
#-----------------------------------------------------------------------------------------------------------------------
def saveMetadataInFile(metadata):
    filename= str(uuid.uuid4())
    path="index_files/"+config["decision_model"]+"/"

    isExist = os.path.exists(path)
    if not isExist:
        os.makedirs(path)

    f = open(path+config["decision_model"]+"-"+filename+".json", 'w+')
    f.write(json.dumps(metadata))
    f.close()
#-----------------------------------------------------------------------------------------------------------------------
def ingest_metadataFile(metadataFile):
    global config

    es = Elasticsearch("http://localhost:9200")
    index = Index(config['decision_model'], es)

    if not es.indices.exists(index=config['decision_model']):
        index.settings(
            index={'mapping': {'ignore_malformed': True}}
        )
        index.create()
    else:
        es.indices.close(index=config['decision_model'])
        put = es.indices.put_settings(
            index=config['decision_model'],
            body={
                "index": {
                    "mapping": {
                        "ignore_malformed": True
                    }
                }
            })
        es.indices.open(index=config['decision_model'])

        id = metadataFile["url"]
        res = es.index(index=config['decision_model'], id=id, body=metadataFile)
        es.indices.refresh(index=config['decision_model'])
#-----------------------------------------------------------------------------------------------------------------------
def indexWebpage(url):
    global config
    html=extractHTML(url)
    metadata={}
    if html!="":
        metadata['url']=url
        for feature in config['features']:
            metadata[feature]=findValue(feature, html)

    #print(metadata)
    #........................................
    if not(if_URL_exist(url)):
        if(metadata):
            saveMetadataInFile(metadata)
            ingest_metadataFile(metadata)
    #........................................
    return metadata
#-----------------------------------------------------------------------------------------------------------------------
def extractJSONfromHTML(string):
    clean = re.compile('<.*?>')
    string = re.sub(clean, " ", string)
    jsonFile={}
    try:
        jsonFile=json.loads(string)
    except ValueError as e:
        return {}
    return jsonFile
#-----------------------------------------------------------------------------------------------------------------------
def getPropertyFromJSON(tag, feature):
    jsonFile={}
    property=config['features'][feature]['propertyValue']
    if(config['features'][feature]['datatype']=="json" and property):
        jsonFile=extractJSONfromHTML(str(tag))
    if(jsonFile and  property in jsonFile):
        return jsonFile[property]
    return {}
#-----------------------------------------------------------------------------------------------------------------------
def findValue(feature, html):
    value=getValue(feature, html)
    datatype=config['features'][feature]['datatype']

    if (value!="N/A"):
        if datatype=="currency" or datatype=="int":
            value=value.replace(",","").replace(".","").strip()
            if value:
                return int(value)
        elif datatype=="decimal":
            value= float(value.replace(",",""))
            if value:
                return int(value)
    return value
#-----------------------------------------------------------------------------------------------------------------------
def getValue(feature, html):
    global config
    tags=html.find_all(config['features'][feature]['tag'], {"class" : config['features'][feature]['cssClass']})

    if len(tags)==1:
        tag=tags[0]
        if not(config['features'][feature]['htmlAllowed']):
            if(config['features'][feature]['propertyValue']):
                tag=tag.attrs.get(config['features'][feature]['propertyValue'])
            return filterByDatatype(remove_tags(str(tag)), config['features'][feature]['datatype'])
        else:
            return str(tag)

    for tag in tags:

        propertyValue=getPropertyFromJSON(tag, feature)
        if(propertyValue):
            return propertyValue

        infix = getByInfix(feature,tag)
        if(infix):
            return str(infix)

        prefix=getByPrefix(feature,tag,html)
        if(prefix):
            return str(prefix)

        postfix=getByPostfix(feature,tag,html)
        if(postfix):
                return str(postfix)

    return "N/A"
#-----------------------------------------------------------------------------------------------------------------------
def getByPostfix(feature,tag,html):
    global config
    if type(tag)!=type(None):
        preTag=tag.find_next(config['features'][feature]['searchKeywords']['postfix']['tag'],class_=config['features'][feature]['searchKeywords']['postfix']['cssClass'])
        if type(preTag)!=type(None):
            property=config['features'][feature]['searchKeywords']['postfix']['propertyValue']
            tagContents=config['features'][feature]['searchKeywords']['postfix']['content']
            #------ propertyValue
            if(property):
                preTag=preTag.attrs.get(property)
                for tagContent in tagContents:
                    if tagContent == preTag:
                        property=config['features'][feature]['propertyValue']
                        if(property):
                            return filterByDatatype(tag.attrs.get(property), config['features'][feature]['datatype'])
                        else:
                            return filterByDatatype(str(tag), config['features'][feature]['datatype'])
            #------ Content
            for tagContent in tagContents:
                if tagContent and tagContent in str(preTag):
                    if not(config['features'][feature]['htmlAllowed']):
                        return filterByDatatype(remove_tags(str(tag)), config['features'][feature]['datatype'])
                    else:
                        return (str(tag))
    return {}
#-----------------------------------------------------------------------------------------------------------------------
def getByPrefix(feature,tag,html):
    global config
    if type(tag)!=type(None):
        preTag=tag.find_previous(config['features'][feature]['searchKeywords']['prefix']['tag'],class_=config['features'][feature]['searchKeywords']['prefix']['cssClass'])
        if type(preTag)!=type(None):
            property=config['features'][feature]['searchKeywords']['prefix']['propertyValue']
            tagContents=config['features'][feature]['searchKeywords']['prefix']['content']
            #------ propertyValue
            if(property):
                preTag=preTag.attrs.get(property)
                for tagContent in tagContents:
                    if tagContent == preTag:
                        property=config['features'][feature]['propertyValue']
                        if(property):
                            return filterByDatatype(tag.attrs.get(property), config['features'][feature]['datatype'])
                        else:
                            return filterByDatatype(str(tag), config['features'][feature]['datatype'])
            #------ Content
            for tagContent in tagContents:
                if tagContent and tagContent in str(preTag):
                    if not(config['features'][feature]['htmlAllowed']):
                        return filterByDatatype(remove_tags(str(tag)), config['features'][feature]['datatype'])
                    else:
                        return (str(tag))
    return {}
#-----------------------------------------------------------------------------------------------------------------------
def getByInfix(feature,tag):
    global config
    if type(tag)!=type(None):
        infix=tag.find(config['features'][feature]['searchKeywords']['infix']['tag'], {"class" : config['features'][feature]['searchKeywords']['infix']['cssClass']})
    if type(infix)!=type(None):
        property=config['features'][feature]['searchKeywords']['infix']['propertyValue']
        tagContents=config['features'][feature]['searchKeywords']['infix']['content']
        #------ propertyValue
        if(property):
            preTag=preTag.attrs.get(property)
            for tagContent in tagContents:
                if tagContent == preTag:
                    property=config['features'][feature]['propertyValue']
                    if(property):
                        return filterByDatatype(tag.attrs.get(property), config['features'][feature]['datatype'])
                    else:
                        return filterByDatatype(str(tag), config['features'][feature]['datatype'])
        #------ Content
        for tagContent in tagContents:
            if tagContent and tagContent in str(infix):
                if not(config['features'][feature]['htmlAllowed']):
                    return filterByDatatype(remove_tags(str(infix)), config['features'][feature]['datatype'])
                else:
                    return (str(infix))
    return {}
#-----------------------------------------------------------------------------------------------------------------------
def if_URL_exist(url):
    global config

    es = Elasticsearch("http://localhost:9200")
    index = Index(config['decision_model'], es)

    if not es.indices.exists(index=config['decision_model']):
        index.settings(
            index={'mapping': {'ignore_malformed': True}}
        )
        index.create()
    else:
        es.indices.close(index=config['decision_model'])
        put = es.indices.put_settings(
            index=config['decision_model'],
            body={
                "index": {
                    "mapping": {
                        "ignore_malformed": True
                    }
                }
            })
        es.indices.open(index=config['decision_model'])

    user_request = "some_param"
    query_body = {
        "query": {
            "bool": {
                "must": [{
                    "match_phrase": {
                        "url": url
                    }
                }]
            }
        },
        "from": 0,
        "size": 1
    }
    result = es.search(index=config['decision_model'], body=query_body)
    numHits=result['hits']['total']['value']
    return True if numHits>0 else False
#-----------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    indexWebsite("funda")
    printResults()

    #config=openCrawlerConfig('funda')
    #indexWebpage("https://www.funda.nl/koop/utrecht/huis-42692721-zilvergeldstraat-11/")
    #get_all_website_links("https://www.funda.nl/doorsturen/mail/huur/den-haag/appartement-88058331-javastraat-31/")
#-----------------------------------------------------------------------------------------------------------------------
