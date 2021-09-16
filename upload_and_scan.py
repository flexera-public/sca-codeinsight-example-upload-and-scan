'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Thu Sep 16 2021
File : upload_and_scan.py
'''

import requests
import logging
import time


logfileName = "_upload_and_scan.log"

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)

#----------------------------------------------------------------------#
def main():

    authToken = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJzZ2VhcnkiLCJ1c2VySWQiOjksImlhdCI6MTYyOTQwMTAzM30._NyOGbk1m0hp_tJpfUNiUQAkxPBSM22DSKeTYLR-QUmZAVkbXwHOckosrc1bk5Oqfe1aRwhkhmqPECmBxCsLnw"
    codeInsightURL = "http://localhost:8888"

    projectName = "Project A"
    zipFile = "codebase.zip"

    # Create a dictionary with the project default with modifications below
    projectDetails = {}
    projectDetails["name"] = projectName

    # Create a new project for the file to be uploaded to.  Returns projectID
    projectID = create_project(projectDetails, codeInsightURL, authToken)

    logger.debug("Project %s created with project ID %s" %(projectName, projectID))
    print("Project %s created with project ID %s" %(projectName, projectID))

    # Upload a zip file to the server
    fileptr = open(zipFile,"rb")
    zipFileContents = fileptr.read()
    fileptr.close()

    upload_project_codebase(projectID, zipFileContents, codeInsightURL, authToken)
    logger.debug("Project zip file has been uploaded")
    print("Project zip file has been uploaded")

    # Start a scan
    scanID = scan_project(projectID, codeInsightURL, authToken)
    logger.debug("Project scan started with scan ID %s" %scanID)
    print("Project scan started with scan ID %s" %scanID)

    # Query the scan until it completes
    
    scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
    
    while scanStatus not in ["completed", "terminated", "failed"]:
        logger.debug("in while loop %s" %scanStatus)
        #  See if it is schedule at this point.. If so hold here in a loop until it is active
        if scanStatus in ["scheduled", "waiting on update"]:
            
            print("Project queued for scanning", end = '', flush=True)
      
            # Loop around while the scan is pending
            while scanStatus in ["scheduled", "waiting on update"]:
                logger.debug("While loop - Scan Status is now %s" %scanStatus)
              
                # Check the status every 10 seconds  * 5*2   
                for x in range(5):
                    time.sleep(2)                    
                    # But update the window every 2 seconds 
                    if x == 4:         
                        scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
                        logger.debug("Scan Status is now %s" %scanStatus)
                        print(".", end = '', flush=True)
            print("")
                                
            print("Project preparing to be scanned.")
            
        #  After it was scheduled it should not be active so start to loop here
        if scanStatus == "active":
            print("Scanning project", end = "", flush=True)
           
            # Loop around while the scan is happening
            while scanStatus == "active":
               
                # But update the window every 2 seconds    
                for x in range(5):
                    time.sleep(5)
                    print(".", end ="", flush=True)
                    
                    # Check the status every 25 seconds  * 5*5
                    if x == 4:         
                        scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
                        logger.debug("scanStatus:  %s" %scanStatus)

        # Get an update on the status
        scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
    
    print("")

    logger.debug("Project scan completed with status %s" %scanStatus)
    print("Project scan completed with status %s" %scanStatus)


#------------  REST API CODE  ------------#

def create_project(projectDetails, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/projects"
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 

    #Extract the details from the PROJECTDETAILS dictionary to create the projectData variable
    projectData = "{"
    
    for attribute in projectDetails:
        projectData = projectData + "\"" + attribute + "\": \"" + projectDetails[attribute] + "\","
        
    # Strip off the last , from projectData string 
    projectData = projectData[:-1] + "}"

    #  Make the request to get the required data   
    try:
        response = requests.post(apiEndPoint, headers=headers, data=projectData)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    
    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 201:
        # The project was created
        projectID = (response.json()["id"])
        logger.debug("ProjectID: %s" %(projectID))
        return projectID
    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def upload_project_codebase(projectID, zipFileContents, codeInsightURL, authToken):

    apiOptions = "&deleteExistingFileOnServer=true&expansionLevel=1" 

    apiEndPoint = codeInsightURL + "/codeinsight/api/project/uploadProjectCodebase"
    apiEndPoint += "?projectId=" + str(projectID) + apiOptions
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/octet-stream', 'Authorization': 'Bearer ' + authToken}  
    
    #  Make the request to get the required data   
    try:
        response = requests.post(apiEndPoint, headers=headers, data=zipFileContents)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        if  "File upload successful" in response.json()["Content: "]:
            logger.debug("File uploaded")
    else:
        logger.error(response.text)
        return 

#--------------------------------------------------
def scan_project(projectID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/scanResource/projectScan"
    apiEndPoint += "/" + str(projectID)
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.post(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        scanID = response.json()["Content: "]
        logger.debug("Scan started with ID: %s" %scanID)
        return scanID
    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def get_scan_status(scanID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/project/scanStatus"
    apiEndPoint += "/" + str(scanID)
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.get(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        scanState = response.json()["Content: "]
        logger.debug("Returning Scan State: %s" %scanState)
        return scanState
    else:
        logger.error(response.text)
        return 



###########################################################################  
if __name__ == "__main__":
    main()  