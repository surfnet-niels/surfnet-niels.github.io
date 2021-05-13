#!/usr/bin/env python3 
#-*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
from operator import itemgetter
from collections import OrderedDict

import os
import datetime
import sys, getopt
import json
import hashlib
import time
import urllib.request
from pathlib import Path

LOGDEBUG = False

##################################################################################################################################
#
# Config and logs handling functions
#
##################################################################################################################################
def loadJSONconfig(json_file):
   with open(json_file) as json_file:
     return json.load(json_file)

def p(message, writetolog=False):
    if writetolog:
      write_log(message)
    else:
      print(message)
    
def pj(the_json, writetolog=False):
    p(json.dumps(the_json, indent=4, sort_keys=True), writetolog)

def write_log(message):
    datestamp = (datetime.datetime.now()).strftime("%Y-%m-%d")
    timestamp = (datetime.datetime.now()).strftime("%Y-%m-%d %X")
    f = open("./logs/" + datestamp + "_apistatus.log", "a")
    f.write(timestamp +" "+ message+"\n")
    f.close()

##################################################################################################################################
#
# Metadata url/file handling functions
#
##################################################################################################################################

def is_file_older_than_x_days(file, days=1): 
    file_time = os.path.getmtime(file) 
    # Check against 24 hours 
    if (time.time() - file_time) / 3600 > 24*days: 
        return True
    else: 
        return False

def fetchXML(url, file_path):
  try:
    urllib.request.urlretrieve(url, file_path)
    return True
  except:
    p("ERROR: Could not download URL: " + url, LOGDEBUG)
    return False

def parseMetadataXML(file_path):
    try:
      with open(file_path) as fd:
          ent = xmltodict.parse(fd.read())
          return ent

    except:
      print("ERROR: Could not parse " +file_path)
      return {}    

def fetchMetadata(md_urls, raname, input_path):

    metadataSet = []

    for i in range(len(md_urls)):
       md_url = md_urls[i]
      
       file_path = input_path + raname.replace(" ", "_") + '_' + str(i) + '.xml'
    
       if os.path.isfile(file_path) and not (is_file_older_than_x_days(file_path, 1)):
           p("INFO: " + raname + " metadata still up to date, skipping download", LOGDEBUG)
       else:
           p("INFO: " + raname + " metadata out of date, downloading from " + md_url, LOGDEBUG)

           if (fetchXML(md_url, file_path)):
             p("INFO: Downloaded metadata: " + md_url + " to file location: " + file_path, LOGDEBUG)
           else:
             p("ERROR: Could not download metadata: " + md_url, LOGDEBUG)
             return {} 
             
       metadataSet.append(file_path)
       
       
    if len(md_urls) == 0:
      p("ERROR: No metadata URL provided for RA " + raname, LOGDEBUG)

    return metadataSet

def setRAdata(raconf, input_path, edugain_ra_uri, entities):
  # Read RA config and loads RA metadata 
  RAs={}

  for ra in raconf.keys():
     RAs[ra] = {} 
      
     RAs[ra]["md_url"] = raconf[ra]["md_url"]
     RAs[ra]["ra_name"] = raconf[ra]["name"]
     RAs[ra]["ra_hash"] = hashSHA1(ra)
     RAs[ra]["country_code"] = raconf[ra]["country_code"]
     RAs[ra]["filepath"] = []

  return RAs

##################################################################################################################################
#
# Metadata processing functions
#
##################################################################################################################################

# Get entityID
def getEntityID(EntityDescriptor, namespaces):
    return EntityDescriptor.get('entityID')

# Get hased EntityID
def hashSHA1(aString):    
    return hashlib.sha1(aString.encode('utf-8')).hexdigest()

# Get MDUI Descriptions
def getDescriptions(EntityDescriptor,namespaces,entType='sp'):
    description_list = list()
    entityType = "./md:SPSSODescriptor"

    descriptions = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Description" % entityType, namespaces)

    if (len(descriptions) != 0):
       for desc in descriptions:
           lang = desc.get("{http://www.w3.org/XML/1998/namespace}lang")
           description_list.append({lang: desc.text})
   
    return description_list


# Get MDUI Logo BIG
def getLogoBig(EntityDescriptor,namespaces,entType='sp'):

    entityType = "./md:SPSSODescriptor"
    
    logoUrl = ""
    logos = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Logo[@xml:lang='en']" % entityType,namespaces)
    if (len(logos) != 0):
       for logo in logos:
           logoHeight = logo.get("height")
           logoWidth = logo.get("width")
           if (logoHeight != logoWidth):
              # Avoid "embedded" logos
              if ("data:image" in logo.text):
                 logoUrl = "embeddedLogo"
                 return logoUrl
              else:
                 logoUrl = logo.text
                 return logoUrl
    else:
       logos = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Logo" % entityType,namespaces)
       if (len(logos) != 0):
          for logo in logos:
             logoHeight = logo.get("height")
             logoWidth = logo.get("width")
             if (logoHeight != logoWidth):
              # Avoid "embedded" logos
                if ("data:image" in logo.text):
                   logoUrl = "embeddedLogo"
                   return logoUrl
                else:
                   logoUrl = logo.text
                   return logoUrl
       else:
          return ""


# Get MDUI Logo SMALL
def getLogoSmall(EntityDescriptor,namespaces,entType='sp'):
    entityType = "./md:SPSSODescriptor"
    
    logoUrl = ""
    logos = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Logo[@xml:lang='en']" % entityType,namespaces)
    if (len(logos) != 0):
       for logo in logos:
           logoHeight = logo.get("height")
           logoWidth = logo.get("width")
           if (logoHeight == logoWidth):
           # Avoid "embedded" logos
              if ("data:image" in logo.text):
                 logoUrl = "embeddedLogo"
                 return logoUrl
              else:
                 logoUrl = logo.text
                 return logoUrl
    else:
       logos = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Logo" % entityType,namespaces)
       if (len(logos) != 0):
          for logo in logos:
              logoHeight = logo.get("height")
              logoWidth = logo.get("width")
              if (logoHeight == logoWidth):
              # Avoid "embedded" logos
                  if ("data:image" in logo.text):
                     logoUrl = "embeddedLogo"
                     return logoUrl
                  else:
                     logoUrl = logo.text
                     return logoUrl
       else:
           return ""


# Get ServiceName
def getServiceName(EntityDescriptor,namespaces,lang='en'):
    entityType = "./md:SPSSODescriptor"
    name_dict = dict()    
    name_dict["en"] = getEntityID(EntityDescriptor,namespaces) 
    
    serviceNames = EntityDescriptor.findall("%s/md:AttributeConsumingService/md:ServiceName" % entityType,namespaces)
    if (serviceNames != None):
       for sn in serviceNames:
          lang = sn.get("{http://www.w3.org/XML/1998/namespace}lang")
          name_dict[lang] = sn.text

    return name_dict

# Get Organization info
def getOrganizationInfo(EntityDescriptor, namespaces,lang='en'):
    orgNames = EntityDescriptor.findall("./md:Organization/md:OrganizationName",namespaces)
    orgDspNames = EntityDescriptor.findall("./md:Organization/md:OrganizationDisplayName",namespaces)
    orgUrls = EntityDescriptor.findall("./md:Organization/md:OrganizationURL",namespaces)
    
    org_dict = {"name": [],"displayname":[],"url":[]};

    if (orgNames != None):
       for org in orgNames:
          lang = org.get("{http://www.w3.org/XML/1998/namespace}lang")
          #org_dict["name"][lang] = org.text
          org_dict["name"].append({lang: org.text})
    
    if (orgDspNames != None):
       for orgdsn in orgDspNames:
          lang = orgdsn.get("{http://www.w3.org/XML/1998/namespace}lang")
          #org_dict["displayname"][lang] = orgdsn.text
          org_dict["displayname"].append({lang: orgdsn.text})

    
    if (orgUrls != None):
       for orgurl in orgUrls:
          lang = orgurl.get("{http://www.w3.org/XML/1998/namespace}lang")
          #if lang not in org_dict["url"]:
          #  org_dict["url"].update({lang: orgurl.text})
          #org_dict["url"][lang] = orgurl.text
          org_dict["url"].append({lang: orgurl.text})
    
    return org_dict


# Get DisplayName or ServiceName
def getName(EntityDescriptor, namespaces, entType='sp'):
    entityType = "./md:SPSSODescriptor"
    name_dict = dict() 
    
    name_dict["en"] = getEntityID(EntityDescriptor,namespaces) 
    displayNames = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:DisplayName" % entityType,namespaces)
    displayNames == None

    if (displayNames != None):
        for dn in displayNames:
          lang = dn.get("{http://www.w3.org/XML/1998/namespace}lang")
          name_dict[lang] = dn.text
    else:
       name_dict = getServiceName(EntityDescriptor,namespaces)

    return name_dict

    
# Get MDUI InformationURLs
def getInformationURLs(EntityDescriptor,namespaces,entType='sp'):
    entityType = "./md:SPSSODescriptor"

    info_pages = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:InformationURL" % entityType, namespaces)

    info_dict = dict()
    for infop in info_pages:
        lang = infop.get("{http://www.w3.org/XML/1998/namespace}lang")
        info_dict[lang] = infop.text

    return info_dict


# Get MDUI PrivacyStatementURLs
def getPrivacyStatementURLs(EntityDescriptor,namespaces,entType='sp'):
    entityType = "./md:SPSSODescriptor"

    privacy_pages = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:PrivacyStatementURL" % entityType, namespaces)

    privacy_dict = dict()
    for pp in privacy_pages:
        lang = pp.get("{http://www.w3.org/XML/1998/namespace}lang")
        privacy_dict[lang] = pp.text

    return privacy_dict

# Get RequestedAttribute
def getRequestedAttribute(EntityDescriptor,namespaces):
    reqAttr = EntityDescriptor.findall("./md:SPSSODescriptor/md:AttributeConsumingService/md:RequestedAttribute", namespaces)

    requireList = list()
    requestedList = list()
    requestedAttributes = dict()

    if (len(reqAttr) != 0):
       for ra in reqAttr:
           if (ra.get('isRequired') == "true"):
              requireList.append(ra.get('FriendlyName'))
           else:
              requestedList.append(ra.get('FriendlyName'))

    requestedAttributes['required'] = requireList
    requestedAttributes['requested'] = requestedList

    return requestedAttributes

# Get entity categories
def getEntityCatagories(EntityDescriptor,namespaces):
    #entityType = "./md:SPSSODescriptor"
    entityCats = EntityDescriptor.findall("./md:Extensions/mdattr:EntityAttributes/saml:Attribute[@Name='http://macedir.org/entity-category']/saml:AttributeValue", namespaces)

    ecs = []
    if (len(entityCats) != 0):
       for ec in entityCats:
           ecs.append(ec.text)
    return ecs

# Get Sirtfi
def getSirtfiSupport(EntityDescriptor,namespaces):
    sirtfiCats = EntityDescriptor.findall("./md:Extensions/mdattr:EntityAttributes/saml:Attribute[@Name='urn:oasis:names:tc:SAML:attribute:assurance-certification']/saml:AttributeValue", namespaces)

    sirtfiSupport = []
    if (len(sirtfiCats) != 0):
       for sirtfi in sirtfiCats:
           sirtfiSupport.append(sirtfi.text)
    return sirtfiSupport    

# Get Contacts
def getAllContacts(EntityDescriptor,namespaces):
    contactsDict = list()
    
    contacts = EntityDescriptor.findall("./md:ContactPerson", namespaces)
    for c in contacts:
        contactTypeDict = {"type": [],"name":[],"email":[]};
        ctype = c.get('contactType')
        
        cname = ""
        if ctype != None:
            contactTypeDict["type"] = ctype
            
            if ctype == "other":
                #Test if this is SIRTFI 
                securityContacts = EntityDescriptor.findall("./md:ContactPerson[@contactType='other'][@remd:contactType='http://refeds.org/metadata/contactType/security']", namespaces)
                if (len(securityContacts) != None):
                    contactTypeDict["type"] = "security"
 
            contactsEmail = EntityDescriptor.findall("./md:ContactPerson[@contactType='"+ctype+"']/md:EmailAddress", namespaces)
            if (len(contactsEmail) != 0):
                contactTypeDict['email'] = contactsEmail[0].text
            contactsGivenName = EntityDescriptor.findall("./md:ContactPerson[@contactType='"+ctype+"']/md:GivenName", namespaces)
            if (len(contactsGivenName) != 0):
                cname = contactsGivenName[0].text
            contactsSurName = EntityDescriptor.findall("./md:ContactPerson[@contactType='"+ctype+"']/md:SurName", namespaces)
            if (len(contactsSurName) != 0):
                cname = cname + contactsSurName[0].text 
         
            if (len(cname) != 0):
             contactTypeDict['name'] = cname

        contactsDict.append(contactTypeDict)

    return contactsDict

def mkAcmeData(entityID):
    # This is fake curated data just so we have some example
    curated = '[{ "catalogID": "%s", "entityID": "%s" ,"service": { "licence": "FALSE", "mfa required": "FALSE", "tenancy": "single", "service type": "other", "landing_page": "https://example.org/acmp_sp"}, "vendor": { "vendor_name": "ACME Inc.", "vendor information": "ACME product line is featuring outlandish products that fail or backfire catastrophically at the worst possible times", "vendor logo": "images/acme.jpeg", "vendor support pages": "https://example.org/acme/support", "vendor website": "https://example.org/acme"} }]' % (hashSHA1(entityID), entityID)
      
    return json.loads(curated)
    
def parseSPs(ra_hash, inputfile, outputpath, namespaces):
   p("Working on: " + inputfile, LOGDEBUG) 
    
   tree = ET.parse(inputfile)
   root = tree.getroot()
   sp = root.findall("./md:EntityDescriptor[md:SPSSODescriptor]", namespaces)

   sps = dict()
   list_sps = list()

   #cont_id = ""

   for EntityDescriptor in sp:
      #list_sps = list()
      info = ""
      privacy = ""
      
      # Get entityID
      entityID = getEntityID(EntityDescriptor,namespaces)
      
#      if entityID == entityID:
#      if entityID == "https://sp.exprodo.com/shibboleth":          
      if entityID == "https://attribute-viewer.aai.switch.ch/shibboleth":          
          # Get hashed entityID
          cont_id = hashSHA1(entityID)

          # Build SP JSON Dictionary
          sp = OrderedDict([
            ('catalogID',           cont_id),
            ('entityID',            entityID),
            ('resourceName',        getName(EntityDescriptor,namespaces,'sp')),
            ('resourceProvider',    getOrganizationInfo(EntityDescriptor, namespaces)),
            ('resourceAttributes',  getRequestedAttribute(EntityDescriptor,namespaces)),
            ('descriptions',        getDescriptions(EntityDescriptor,namespaces)),
            ('resourceContacts',    getAllContacts(EntityDescriptor, namespaces)),
            ('info',                getInformationURLs(EntityDescriptor, namespaces, 'sp')),
            ('privacy',             getPrivacyStatementURLs(EntityDescriptor, namespaces, 'sp')),
            ('entityCategories',    getEntityCatagories(EntityDescriptor,namespaces)),
            ('SirtfiSupport',       getSirtfiSupport(EntityDescriptor,namespaces))
          ])     

          #per SP curated output
          path = outputpath + "catalog/"
          file_path = path + cont_id + ".json"
          Path(path).mkdir(parents=True, exist_ok=True)

          # THis is for demo purposes only
          curated_spdata = open(file_path, "w",encoding=None)
          curated_spdata.write(json.dumps(mkAcmeData(entityID),sort_keys=False, indent=4, ensure_ascii=False,separators=(',', ':')))
          curated_spdata.close()

          # add Sp to list of per federation SPs
          list_sps.append(sp)

   #write out all SPs in one fed to a single file
   path = outputpath + "fed/"
   file_path = path + ra_hash + ".json"
   Path(path).mkdir(parents=True, exist_ok=True)
   result_sps = open(file_path, "w",encoding=None)
   result_sps.write(json.dumps(list_sps,sort_keys=False, indent=4, ensure_ascii=False,separators=(',', ':')))
   result_sps.close()

def main(argv):
   ROOTPATH='.'
   CONFIG_PATH = ROOTPATH + '/config/'
   INPUT_PATH = ROOTPATH + '/feeds/'
   OUTPUT_PATH = ROOTPATH + '/output/'
   EDUGAIN_RA_URI = 'https://www.edugain.org'
   entities = {}
   entity_data = {}
   entity_occurance = {}   
 
   inputfile = None
   inputpath = INPUT_PATH
   outputpath = OUTPUT_PATH

   namespaces = {
      'xml':'http://www.w3.org/XML/1998/namespace',
      'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
      'mdrpi': 'urn:oasis:names:tc:SAML:metadata:rpi',
      'shibmd': 'urn:mace:shibboleth:metadata:1.0',
      'mdattr': 'urn:oasis:names:tc:SAML:metadata:attribute',
      'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
      'ds': 'http://www.w3.org/2000/09/xmldsig#',
      'mdui': 'urn:oasis:names:tc:SAML:metadata:ui',
      'remd': 'http://refeds.org/metadata'
   }

   # First load RA config
   raConf = loadJSONconfig(CONFIG_PATH + 'RAs.json')
   RAs = setRAdata(raConf, INPUT_PATH, EDUGAIN_RA_URI, entities)

   #pj(RAs)

   # eduGAOIn only
   RAs[EDUGAIN_RA_URI]["filepath"] = fetchMetadata(RAs[EDUGAIN_RA_URI]["md_url"], RAs[EDUGAIN_RA_URI]["ra_name"], INPUT_PATH)
   # Now loop over RAs files to extract SP metadata and work that into a json
   parseSPs(RAs[EDUGAIN_RA_URI]["ra_hash"], RAs[EDUGAIN_RA_URI]["filepath"][0], outputpath, namespaces)

   # For each RA process the entities
#   for ra in RAs.keys():
        # Load entity data from federation endpoint(s) and retrunme the file locations
#        RAs[ra]["filepath"] = fetchMetadata(RAs[ra]["md_url"], RAs[ra]["ra_name"], INPUT_PATH)
 
        # Now loop over RAs files to extract SP metadata and work that into a json
#        parseSPs(RAs[ra]["ra_hash"], RAs[ra]["filepath"][0], outputpath, namespaces)

if __name__ == "__main__":
   main(sys.argv[1:])
