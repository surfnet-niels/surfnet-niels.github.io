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
  #try:
    urllib.request.urlretrieve(url, file_path)
    return True
  #except:
  #  p("ERROR: Could not download URL: " + url, LOGDEBUG)
  #  return False

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
def getDescriptions(EntityDescriptor,namespaces,entType='idp'):

    description_list = list()
    if (entType.lower() == 'idp'):
       entityType = "./md:IDPSSODescriptor"
    if (entType.lower() == 'sp'):
       entityType = "./md:SPSSODescriptor"

    descriptions = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Description" % entityType, namespaces)

    if (len(descriptions) != 0):
       for desc in descriptions:
           descriptions_dict = dict()
           descriptions_dict['value'] = desc.text
           descriptions_dict['lang'] = desc.get("{http://www.w3.org/XML/1998/namespace}lang")
           description_list.append(descriptions_dict)
    
    return description_list


# Get MDUI Logo BIG
def getLogoBig(EntityDescriptor,namespaces,entType='idp'):

    entityType = ""
    if (entType.lower() == 'idp'):
       entityType = "./md:IDPSSODescriptor"
    if (entType.lower() == 'sp'):
       entityType = "./md:SPSSODescriptor"
    
    logoUrl = ""
    logos = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Logo[@xml:lang='it']" % entityType,namespaces)
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
def getLogoSmall(EntityDescriptor,namespaces,entType='idp'):
    entityType = ""
    if (entType.lower() == 'idp'):
       entityType = "./md:IDPSSODescriptor"
    if (entType.lower() == 'sp'):
       entityType = "./md:SPSSODescriptor"
    
    logoUrl = ""
    logos = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:Logo[@xml:lang='it']" % entityType,namespaces)
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
def getServiceName(EntityDescriptor,namespaces):
    serviceName = EntityDescriptor.find("./md:SPSSODescriptor/md:AttributeConsumingService/md:ServiceName[@xml:lang='it']", namespaces)
    if (serviceName != None):
       return serviceName.text
    else:
       serviceName = EntityDescriptor.find("./md:SPSSODescriptor/md:AttributeConsumingService/md:ServiceName[@xml:lang='en']", namespaces)
       if (serviceName != None):
          return serviceName.text
       else:
          return ""


# Get Organization Name
def getOrganizationName(EntityDescriptor, namespaces,lang='it'):
    orgName = EntityDescriptor.find("./md:Organization/md:OrganizationName[@xml:lang='%s']" % lang,namespaces)

    if (orgName != None):
       return orgName.text
    else:
       return ""


# Get DisplayName
def getDisplayName(EntityDescriptor, namespaces, entType='idp'):
    entityType = ""
    if (entType.lower() == 'idp'):
       entityType = "./md:IDPSSODescriptor"
    if (entType.lower() == 'sp'):
       entityType = "./md:SPSSODescriptor"

    displayName = EntityDescriptor.find("%s/md:Extensions/mdui:DisplayName[@xml:lang='it']" % entityType,namespaces)

    if (displayName != None):
       return displayName.text
    else:
       displayName = EntityDescriptor.find("%s/md:Extensions/mdui:DisplayName[@xml:lang='en']" % entityType,namespaces)
       if (displayName != None):
          return displayName.text
       else:
          if (entType == 'sp'):
             displayName = getServiceName(EntityDescriptor,namespaces)
             if (displayName != None):
                return displayName
             else:
                return ""
          else:
             displayName = getOrganizationName(EntityDescriptor,namespaces)
             return displayName

    
# Get MDUI InformationURLs
def getInformationURLs(EntityDescriptor,namespaces,entType='idp'):
    entityType = ""
    if (entType.lower() == 'sp'):
       entityType = "./md:SPSSODescriptor"

    info_pages = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:InformationURL" % entityType, namespaces)

    info_dict = dict()
    for infop in info_pages:
        lang = infop.get("{http://www.w3.org/XML/1998/namespace}lang")
        info_dict[lang] = infop.text

    return info_dict


# Get MDUI PrivacyStatementURLs
def getPrivacyStatementURLs(EntityDescriptor,namespaces,entType='idp'):
    entityType = ""
    if (entType.lower() == 'sp'):
       entityType = "./md:SPSSODescriptor"

    privacy_pages = EntityDescriptor.findall("%s/md:Extensions/mdui:UIInfo/mdui:PrivacyStatementURL" % entityType, namespaces)

    privacy_dict = dict()
    for pp in privacy_pages:
        lang = pp.get("{http://www.w3.org/XML/1998/namespace}lang")
        privacy_dict[lang] = pp.text

    return privacy_dict


# Get OrganizationURL
def getOrganizationURL(EntityDescriptor,namespaces,lang='it'):
    orgUrl = EntityDescriptor.find("./md:Organization/md:OrganizationURL[@xml:lang='%s']" % lang,namespaces)

    if (orgUrl != None):
       return orgUrl.text
    else:
       return ""


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


# Get Contacts
def getContacts(EntityDescriptor,namespaces,contactType='technical'):
    #ToDo: add a more strict scan for securtiy as 'other may also be used in another way'

    contactsList = list()
    contacts = EntityDescriptor.findall("./md:ContactPerson[@contactType='"+contactType.lower()+"']/md:EmailAddress", namespaces)
    contactsGivenName = EntityDescriptor.findall("./md:ContactPerson[@contactType='"+contactType.lower()+"']/md:GivenName", namespaces)
    contactsSurName = EntityDescriptor.findall("./md:ContactPerson[@contactType='"+contactType.lower()+"']/md:SurName", namespaces)

    cname = "" 
    if (len(contactsGivenName) != 0):
       for cgn in contactsGivenName:
           cname = cgn.text

    if (len(contactsSurName) != 0):
       for csn in contactsSurName:
           cname = cname + " " + csn.text
   
    if (len(cname) != 0):
       contactsList.append(cname.strip())              

    if (len(contacts) != 0):
       for ctc in contacts:
           if ctc.text.startswith("mailto:"):
              contactsList.append(ctc.text.replace("mailto:", ""))
           else:
              contactsList.append(ctc.text)

    #return '<br/>'.join(contactsList)
    return 'contactsList

def parseSPs(ra_hash, inputfile, outputpath, namespaces):
   p("Working on: " + inputfile, LOGDEBUG) 
    
   # JSON SP Output:
   # [
   #   {
   #     "id": #_sha1-hash-over-entityID_#,
   #     "resourceName": "#_resource-display-name_#",
   #     "resourceProvider": "#_organization-name-linked_#",
   #     "resourceAttributes": {
   #        "required": [
   #                      "eduPersonPrincipalName",
   #                      "email",
   #                      "givenName",
   #                      "surname"
   #                    ],
   #        "requested": []
   #     },
   #     "entityID": "#_entityID-resource_#",
   #     "resourceContacts": {
   #        "technical": [
   #                       "#_email-address-list_#"
   #                     ],
   #        "support": [],
   #        "administrative": []
   #     },
   #     "info": "<a href='#_info-url-it_#'>IT</a>, <a href='#_info-url-en_#'>EN</a>",
   #     "privacy": "<a href='#_privacy-url-it_#'>IT</a>, <a href='#_privacy-url-en_#'>EN</a>"
   #   }
   # ]

   tree = ET.parse(inputfile)
   root = tree.getroot()
   sp = root.findall("./md:EntityDescriptor[md:SPSSODescriptor]", namespaces)

   sps = dict()
   list_sps = list()

   #cont_id = ""

   for EntityDescriptor in sp:
      info = ""
      privacy = ""
      
      # Get entityID
      entityID = getEntityID(EntityDescriptor,namespaces)
      
      if entityID == entityID:
          
          # Get hashed entityID
          cont_id = hashSHA1(entityID)

          # Get InformationURL
          infoDict = getInformationURLs(EntityDescriptor, namespaces, 'sp')

          # Get PrivacyStatementURL
          privacyDict = getPrivacyStatementURLs(EntityDescriptor, namespaces, 'sp')

          # Get ServiceName
          serviceName = getDisplayName(EntityDescriptor,namespaces,'sp')

          # Build Resource Info Pages
          #info = "<ul>"
          info = {}
          for lng in infoDict:
            info[lng] = infoDict[lng]
  
          # Build Resource Privacy Pages
          privacy = {}
          for lng in privacyDict:
            privacy[lng] = privacyDict[lng]

          # Get Requested Attributes
          requestedAttributes = getRequestedAttribute(EntityDescriptor,namespaces)

          # Get Organization Name

          orgName = getOrganizationName(EntityDescriptor,namespaces,'it')
          if (orgName == ""):
             orgName = getOrganizationName(EntityDescriptor,namespaces,'en')

          # Get Organization Page
          orgUrl = getOrganizationURL(EntityDescriptor,namespaces,'it')
          if (orgUrl == ""):
             orgUrl = getOrganizationURL(EntityDescriptor,namespaces,'en')
         
          orgName = "<a href='%s' target='_blank'>%s</a>" % (orgUrl,orgName)

          # Get Contacts
          techContacts = getContacts(EntityDescriptor, namespaces, 'technical')
          suppContacts = getContacts(EntityDescriptor, namespaces, 'support')
          adminContacts = getContacts(EntityDescriptor, namespaces, 'administrative')
          securityContacts = getContacts(EntityDescriptor, namespaces, 'other')


          contacts = OrderedDict([
             ('technical', techContacts),
             ('support', suppContacts),
             ('administrative', adminContacts),
             ('security', securityContacts),
          ])

          # Build SP JSON Dictionary
          sp = OrderedDict([
            ('id',cont_id),
            ('resourceName',serviceName),
            ('resourceProvider', orgName),
            ('resourceAttributes',requestedAttributes),
            ('entityID',entityID),
            ('resourceContacts',contacts),
            ('info', info),
            ('privacy', privacy)
          ])     

      # per SP outup
      #path = all_outputpath + "/" + cont_id + ".json"
      #Path(all_outputpath).mkdir(parents=True, exist_ok=True)
      #result_sp = open(path, "w",encoding=None)
      #result_sp.write(json.dumps(sp,sort_keys=False, indent=4, ensure_ascii=False,separators=(',', ':')))
      #result_sp.close()

      list_sps.append(sp)

   #all SPs in one fed 
   path = outputpath + "/" + ra_hash + ".json"
   Path(outputpath).mkdir(parents=True, exist_ok=True)
   result_sps = open(path, "w",encoding=None)
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
      'mdui': 'urn:oasis:names:tc:SAML:metadata:ui'
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
