#!/usr/bin/env python
"""
DBS migration service engine
"""
__revision__ = "$Id: DBSMigrationEngine.py,v 1.3 2010/08/12 19:17:57 yuyi Exp $"
__version__ = "$Revision: 1.3 $"

import threading
import logging
import traceback
import os
import time

from sqlalchemy import exceptions

from WMCore.WorkerThreads.BaseWorkerThread import BaseWorkerThread
from WMCore.DAOFactory import DAOFactory

import json, cjson
import urllib, urllib2

from dbs.utils.dbsUtils import dbsUtils

class DBSMigrationEngine(BaseWorkerThread) :

    """
    Each migration engine works as thread handling a completed request.
    """
    
    def __init__(self, config):
        """
        Initialise class members
        """

	# Used for creating connections/transactions
        myThread = threading.currentThread()
	self.threadID = myThread.ident
	self.dbi = myThread.dbi

	self.logger = myThread.logger
	
	BaseWorkerThread.__init__(self)
	# get the db owner
        self.config  = config
	dbconfig = config.section_("CoreDatabase")
	self.dbowner=dbconfig.dbowner
	
	self.datasetCache = {}
	self.datasetCache['primDs']={}
	self.datasetCache['dataset']={}
	self.datasetCache['acquisitionEra']={}
	self.datasetCache['processingVersion']={}
	self.datasetCache['phyGrp']={}
	self.datasetCache['dataTier']={}
	self.datasetCache['primDsTp']={}
	self.datasetCache['datasetAccTp']={}
	self.datasetCache['processedDs']={}
	self.datasetCache['relVer']={}
	self.datasetCache['pHash']={}
	self.datasetCache['appExe']={}
	
    # This is only called once by the frwk
    def setup(self, parameters):
        """
        Load DB objects required for queries
        """

	# Setup the DAO objects
	daofactory = DAOFactory(package='dbs.dao', logger=self.logger, dbinterface=self.dbi, owner=self.dbowner)

        #self.sm		    = daofactory(classname="SequenceManager")
	self.fpr = daofactory(classname="MigrationRequests.FindPendingRequest")
	self.urs = daofactory(classname="MigrationRequests.UpdateRequestStatus")
	self.fmb = daofactory(classname="MigrationBlock.FindMigrateableBlock")
	#self.reqlist = daofactory(classname="MigrationRequests.List")
	#self.minreqlist = daofactory(classname="MigrationRequests.ListOldest")
	#self.requestup   = daofactory(classname="MigrationRequests.Update")
	#self.blklist = daofactory(classname="MigrationBlock.List")
	self.blkup = daofactory(classname="MigrationBlock.Update")

        self.primdslist	    = daofactory(classname="PrimaryDataset.List")
	self.primdsid       = daofactory(classname="PrimaryDataset.GetID")
	self.datasetlist    = daofactory(classname="Dataset.List")
	self.datasetid      = daofactory(classname="Dataset.GetID")
	self.blocklist	    = daofactory(classname="Block.List")
	self.blockid        = daofactory(classname="Block.GetID")
	self.filelist	    = daofactory(classname="File.List")
	self.fplist	    = daofactory(classname="FileParent.List")
        self.fllist	    = daofactory(classname="FileLumi.List")
	self.primdstpid	    = daofactory(classname='PrimaryDSType.GetID')
	self.tierid	    = daofactory(classname='DataTier.GetID')
        self.datatypeid	    = daofactory(classname='DatasetType.GetID')
        self.phygrpid	    = daofactory(classname='PhysicsGroup.GetID')
	self.acqid          = daofactory(classname='AcquisitionEra.GetID')
	self.procsingid     = daofactory(classname='ProcessingEra.GetID')
        self.procdsid	    = daofactory(classname='ProcessedDataset.GetID')
	#self.otptModCfglist = daofactory(classname='OutputModuleConfig.List')
	self.otptModCfgid   = daofactory(classname='OutputModuleConfig.GetID')
	self.releaseVid     = daofactory(classname='ReleaseVersion.GetID')
	self.psetHashid     = daofactory(classname='ParameterSetHashe.GetID') 
	self.appid          = daofactory(classname='ApplicationExecutable.GetID') 

	self.procsingin     = daofactory(classname='ProcessingEra.Insert')
        self.acqin          = daofactory(classname='AcquisitionEra.Insert')
	self.procdsin	    = daofactory(classname='ProcessedDataset.Insert')
        self.primdsin	    = daofactory(classname="PrimaryDataset.Insert")
	self.primdstpin     = daofactory(classname="PrimaryDSType.Insert")
        self.datasetin	    = daofactory(classname='Dataset.Insert')
        self.dsparentin     = daofactory(classname='DatasetParent.Insert')
	self.datatypein     = daofactory(classname='DatasetType.Insert')
	self.blockin        = daofactory(classname='Block.Insert')
	self.sm             = daofactory(classname = "SequenceManager")
	self.filein         = daofactory(classname = "File.Insert")
	self.flumiin        = daofactory(classname = "FileLumi.Insert")
	self.fparentin      = daofactory(classname = "FileParent.Insert")
	self.fpbdlist       = daofactory(classname = "FileParentBlock.List")
	self.blkparentin    = daofactory(classname = "BlockParent.Insert")
	self.dsparentin     = daofactory(classname = "DatasetParent.Insert")
	self.blkstats       = daofactory(classname = "Block.ListStats")
	self.blkstatsin     = daofactory(classname = "Block.UpdateStats")
	self.fconfigin      = daofactory(classname='FileOutputMod_config.Insert')
	self.bufdeletefiles = daofactory(classname="FileBuffer.DeleteFiles")
	self.buflist        = daofactory(classname="FileBuffer.List")
	self.buflistblks    = daofactory(classname="FileBuffer.ListBlocks")
	self.buffinddups    = daofactory(classname="FileBuffer.FindDuplicates")
	self.bufdeletedups  = daofactory(classname="FileBuffer.DeleteDuplicates")
	self.compstatusin   = daofactory(classname="ComponentStatus.Insert")
	self.compstatusup   = daofactory(classname="ComponentStatus.Update")
	self.otptModCfgin   = daofactory(classname='OutputModuleConfig.Insert')
        self.releaseVin     = daofactory(classname='ReleaseVersion.Insert')
	self.psetHashin     = daofactory(classname='ParameterSetHashe.Insert')
	self.appin          = daofactory(classname='ApplicationExecutable.Insert')
        self.dcin           = daofactory(classname='DatasetOutputMod_config.Insert')


	# Report that service has started
	self.insertStatus("STARTED")

    # This is the actual poll method, called over and over by the frwk
    def algorithm(self, parameters):
	"""
	Performs the handleMigration method, called by frwk over and over (until terminate is called)
	"""
	logging.debug("Running dbs migration algorithm")
	
	#here is the excitment starting.
	self.handleMigration()	
	
    def handleMigration(self):
	"""
	The actual handle method for performing migration

	* The method takes a request and tries to complete it till end, this way we 
	* do not have incomplete running migrations running forever
	
	3. Get the highest order 'PENDING' block
	4. Change the status of block to RUNNING
	5. Migrate it
	6. Change the block status to 'COMPLETED' (?remove from the list?)
	7. Pick the next block, go to 4.
	8. After no more blocks can be migrated, mark the request as DONE (move to history table!!!!)
	"""
	
	request={}
	requestID=-1
	try :
	    #1 get a migration request in 0 (PENDING) STATUS & Change its status to 1 (RUNNING)
	    conn = self.dbi.connection()
	    request = getMigrationRequest(conn)
	    if not request:
		return 
	    
	    #2 find the highest order pending block		    
	    requestID=request["migration_request_id"]
	    blocks = self.fmb.execute(conn, requestID)
	    for ablock in blocks:
	        self.migrateBlock(conn, ablock['migration_block_name'], request["migration_url"])
	    
	    #Finally mark the request as 3=Completed
	    tran = conn.begin()
	    self.urs.execute(conn, requestID, 3, self.threadID, dbsUtils().getTime())
	    tran.commit();
	except Exception, ex:
	    self.logger.exception("DBS Migration Service failed to perform migration %s" %str(ex))
	    #FAILED=4
	    tran = conn.begin()
	    self.urs.execute(conn, requestID, 4, self.threadID, dbsUtils().getTime()))
	    tran.commit()
	    raise
	finally:
	    conn.close()

    def getMigrationRequest(self, conn):
	"""
	Find a pending request from the queued requests (in database) and update its status to 1 (running)
	--atomic operation
	"""
	request=[]
	try:
	    tran = conn.begin()
	    #get the pending request
	    request = self.fpr.execute(conn,tran)
	    if len(request) <= 1:
		#not found request, goodby.
		tran.rollback()
		return {}
	    else:	    
		requestID=request[0]["MIGRATION_REQUEST_ID"]
		migration_status = 1
		#update the request to 1 (running)
		self.urs.execute(conn, requestID, 1, self.threadID, dbsUtils().getTime(),tran)
		tran.commit()
		return request[0]
	except:
	    self.logger.exception("DBS Migrate Service Failed to find migration requests")
	    raise
	
		
    def updateBlockStatus(self, conn, block_name, status):
            try:
	        blkupst = dict(migration_status=status, migration_block_name=block_name)
		print "TEMPORARY : commented out"
		#self.blkup.execute(conn, blkupst)
	        self.reportStatus(conn, "WORKING FINE")
            except:
	        raise

    def migrateBlock(self, conn, block_name, url):
	"""
	Performs the block migration
	"""

	try:
	    blockcontent = self.getRemoteBlock(url, block_name)
	    #the mover is putBlock
	    self.putBlock(conn, blockcontent)
	    self.updateBlockStatus(conn, block_name, 'COMPLETED')
	except Exception, ex:
	    self.updateBlockStatus(conn, block_name, 'FAILED')
	    raise Exception ("Migration of Block %s from DBS %s has failed, Exception trace: \n %s " % (url, block_name, ex ))

    def getRemoteBlock(self, url, block_name):
	"""Client type call to get the block content from the remote server"""
	try:
	    blockname = block_name.replace("#",urllib.quote_plus('#'))
	    resturl = "%s/blockdump?block_name=%s" % (url, blockname)
	    req = urllib2.Request(url = resturl)
	    data = urllib2.urlopen(req)
	    #Now it is depending on the remote server's blocks call.
	    ddata = cjson.decode(data.read())
	except Exception, ex:
	    print ex
	    raise Exception ("Unable to get information from src dbs : %s for block : %s" %(url, block_name))
        return ddata

    def getRemoteData(self, url, verb, searchingName, searchingVal):
        """Client type call to get content from the remote server"""
        try:
            resturl = "%s/%s?%s=%s" % (url, verb, searchingname, searchingVal)
            req = urllib2.Request(url = resturl)
            data = urllib2.urlopen(req)
            #Now it is depending on the remote server's calls.
            ddata = cjson.decode(data.read())
        except Exception, ex:
            print ex
            raise Exception ("Unable to get information from src dbs : %s for %s?%s=%s" %(url, verb, searchingName, searchingVal))
        return ddata

    def putBlock(self, conn, blockcontent, url):
	"""
	Insert the data in sereral steps and commit when each step finishes or rollback if there is a problem.
	"""
	#1 insert dataset
	datasetId = self.insertDataset(conn, blockcontent url)
	#2 Insert Block
	blockId = self.insertBlock(conn, blockcontent)

    def insertBlock(self, conn, blockcontent)
	"""
	Block is very simple to insert

	"""
	block = blockcontent['block']
	newBlock = False
	#Insert the block
	try:
	    tran = conn.begin()
	    block['block_id'] = self.sm.increment(conn,"SEQ_BK")
	    block['dataset_id'] =  blockcontent['dataset']['datset_id']
	    self.blockin.execute(conn, block, tran)
	    newBlock = True
	except exceptions.IntegrityError:
	    #ok, already in db
	    block['block_id'] = self.blockid.execute(conn, block['block_name'])
	exception:
	    tran.rollback()
	    raise
	#Now handle Block Parenttage
	bpList = blockcontent['block_parent_list']
	intval = 10
	if newBlock:
	    try:
		for i in range(len(bpList)):
		    if(i==0 or i%intavl==0):
			id = self.sm.increment(conn,"SEQ_BP")
		    parent['block_parent_id'] = id
		    id += 1
		    parent['this_block_id'] = block['block_id']
		    parent['parent_block_id'] = self.blockid.execute(conn, parent['block_name'])
		    if parent['parent_block_id'] <= 0:
			raise Exception("Parent block: %s not found in db" %parent['block_name'])
		    del parent['block_name']
		if bpList and newBlock:
		    self.blkparentin.execute(conn, bpList, tran)
	    exception:
		tran.rollback()
		raise
	try:
	    tran.commit()
	exception:
	    raise
	return block['block_id']

    def insertOutputModuleConfig(self, conn, dataset, url)
        """
        Insert Release version, application, parameter set hashes and the map(output module config).

        """
	remoteConfig = self.getRemoteData(url,'outputconfigs', 'dataset', dataset)
	otptIdList = []
	missingList = []
	try:
	    for c in remoteConfig:
		cfgid = self.otptModCfgid.execute(conn, c["app_name"], c["release_version"], c["pset_hash"],\
		   c["output_module_label"])
		if cfgid > 0:
		    otptIdList.append(cfgid)
		if cfgid <=0 :
		    missingList.append(c)
	exception:
	    raise
	#Now insert the missing configs
	try:
	    tran = conn.begin()
	    for m in missingList:
		#get output module config id
		cfgid = self.sm.increment(conn, "SEQ_OMC")
		#find release version id
		if m["release_version"] in (self.datasetCache['relVer']).keys():
		    #found in cache
		    reId = self.datasetCache['relVer'][m["release_version"]]
		else:
		    reId = self.releaseVid.execute(conn, m["release_version"])
		    if reId <= 0:
			#not found release version in db, insert it now
			reId = self.sm.increment(conn, "SEQ_RV")
			reobj={"release_version": m["release_version"], "release_version_id": reId}
			self.releaseVin(conn, reobj, tran)
		    #cached it
		    self.datasetCache['relVer'][m["release_version"]] = reId
		#find pset hash id
		if m["pset_hash"] in (self.datasetCache['pHash']).keys():
                    #found in cache
                    pHId = self.datasetCache['pHash'][m["pset_hash"]]
                else:
                    pHId = self.psetHashid.execute(conn, m["release_version"])
                    if pHId <= 0:
                        #not found p set hash in db, insert it now
                        pHId = self.sm.increment(conn, "SEQ_PSH")
                        pHobj={"pset_hash": m["pset_hash"], "parameter_set_hash_id": pHId}
                        self.psetHashin(conn, pHobj, tran)
                    #cached it
                    self.datasetCache['pHash'][m["pset_hash"]] = pHId
		#find application id
		if m["app_name"] in (self.datasetCache['appExe']).keys():
                    #found in cache
                    appId = self.datasetCache['appExe'][m["app_name"]]
                else:
                    appId = self.appid.execute(conn, m["app_name"])
                    if appId <= 0:
                        #not found application in db, insert it now
                        appId = self.sm.increment(conn, "SEQ_AE")
                        appobj={"app_name": m["app_name"], "app_exec_id": appId}
                        self.appin(conn, appobj, tran)
                    #cached it
                    self.datasetCache['appExe'][m["app_name"]] = pHId	
		#Now insert the config
		configObj = {'output_mod_config_id':cfgid , 'app_exec_id':appId,  'release_version_id':reId,  \
                             'parameter_set_hash_id':pHId , 'output_module_label':m['output_module_label'],   \
                             'creation_date':, 'create_by': }
		self.otptModCfgin(conn,	configObj, tran)
		otptIdList.append(cfgid)
	    tran.commit()
	exception:
            tran.rollback()
            raise
        return otptIdList


    def insertDataset(self, conn, blockcontent, otptIdList, sourceurl)
	"""
	This method insert a datsset from a block object into dest dbs. When data is not completed in
	the block object. It will reterive data from the source url. 
	"""
	#Check if dataset in the cache
	if dataset["dataset"] in (self.datasetCache['dataset']).keys():
	    dataset['dataset_id'] = self.datasetCache['dataset'][dataset["dataset"]]
	    return dataset['dataset_id']
	else:
	    #check if the dataset in local db
	    try:
		dataset['dataset_id'] = self.datasetid.execute(conn, dataset["dataset"])
	    except:
		raise
	    if dataset['dataset_id'] > 0:
		return dataset['dataset_id']
	#Not in cache nor in local db. A brand new dataset needed to be inserted. 	
	try:
	    #Start a new transaction 
	    tran = conn.begin()
	    #1. Deal with primary dataset. Most primary datasets are perinstalled in db  
	    primds = blockcontent["primds"]
	    #First, search in the cache
	    if primds["primary_ds_name"] in (self.datasetCache['primDs']).keys():
		#found it, update the ID with local ID 
		primds["primary_ds_id"] = self.datasetCache['primDs'][primds["primary_ds_name"]]
	    else:   
		#Second, seach in the local db
		primds["primary_ds_id"] = self.primdsid.execute(conn, primds["primary_ds_name"])
		    if primds["primary_ds_id"] <= 0:
			#primary dataset is not in db yet. We need to check if the primary_ds_type before insert primary ds
			if primds["primary_ds_type"] in (self.datasetCache['primDsTp']).keys(): 
			    primds["primary_ds_type_id"] = self.datasetCache['primDsTp'][primds["primary_ds_type"]]
			else:
			    primds["primary_ds_type_id"] = self.primdstpid.execute(conn, primds["primary_ds_type"]))
			    if primds["primary_ds_type_id"] <= 0:
				#primary ds type is not in db yet. Insert it now
				primds["primary_ds_type_id"] = self.sm.increment(conn,"SEQ_PDT")
				self.primdstpin(conn, primds["primary_ds_type_id"], primds["primary_ds_type"],tran)
			    #register to cache. Done with primary ds type    
			    self.datasetCache['primDsTp']["primary_ds_type"]=primds["primary_ds_type_id"]
			#Now inserting primary ds. Clean up dao object befer inserting
			del primds["primary_ds_type"]
			primds["primary_ds_id"] = self.sm.increment(conn, "SEQ_PDS"))
			self.primdsin(conn, primds, tran) 
		#register to cache. Done with primary ds     
		self.datasetCache['primDs']["primary_ds_name"] = primds["primary_ds_id"]
	    #2 Deal with processed ds
	    #Check if processed ds in the cache
	    if dataset["processed_ds_name"] in (self.datasetCache['processedDs']).keys():
		dataset['processed_ds_id'] = self.datasetCache['processedDs'][dataset["processed_ds_name"]]
	    else:
		try:
		    #Let's insert the processed ds since it is not pre-inserted at schema level
		    daoproc={'processed_ds_id':self.sm.increment(conn,"SEQ_PSDS"), 
			    "processed_ds_name": dataset['processed_ds_name']}
		    self.procdsin.execute(conn,daoproc, tran)
		    #regist to cache
		    self.datasetCache['processedDs']['processed_ds_name'] = daoproc['processed_ds_id']
		    dataset['processed_ds_id'] = daoproc['processed_ds_id']
		except exceptions.IntegrityError:
		    #Ok, it is in db already. Get the ID
		    dataset['processed_ds_id'] = self.procdsid.execute(conn, dataset['processed_ds_name']))
		    #regist to cache
		    self.datasetCache['processedDs']['processed_ds_name'] = dataset['processed_ds_id']
		    pass
		except:
		    tran.rollback
		    raise
	    #3 Deal with Acquisition era
	    aq = blockcontent['acquisition_era']
	    #is there acquisition?
	    if aq:
	    #check if acquisition in cache
		if aq['acquisition_era_name'] in (self.datasetCache['acquisitionEra']).keys():
		    dataset['acquisition_era_id'] = self.datasetCache['acquisitionEra'][aq['acquisition_era_name']]
		else:
		    try;
			#insert acquisition era into db
			aq['acquisition_era_id'] = self.sm.increment(conn,"SEQ_AQE")
			self.acqin.execute(conn, aq, tran)
			#regist to cache
			self.datasetCache['acquisitionEra']['acquisition_era_name'] = aq['acquisition_era_id']
			dataset['acquisition_era_id'] = aq['acquisition_era_id']
		    except exceptions.IntegrityError:
			#ok, already in db
			dataset['acquisition_era_id'] = self.acqid.execute(conn, aq['acquisition_era_name'])
			self.datasetCache['acquisitionEra'][aq['acquisition_era_name']] = dataset['acquisition_era_id']
		    except:
			tran.rollback
			raise
	    else:
		#no acquisition era for this dataset
		pass
	    #4 Deal with Processing era
	    pera = blockcontent['processing_era']
	    #is there processing era?
	    if pera:
		#check if in cache
		if pera['processing_version'] in (self.datasetCache['processingVersion']).keys():
		    dataset['processing_era_id'] = self.datasetCache['processingVersion'][aq['processing_version']]
		else:
		    try;
			#insert processing era into db
			pera['processing_era_id'] = self.sm.increment(conn,"SEQ_PE")
			self.procsingin.execute(conn, pera, tran)
			#regist to cache
			self.datasetCache['processingVersion'][pera['processing_version']] = pera['processing_era_id']
			dataset['processing_era_id'] = pera['processing_era_id']
		    except exceptions.IntegrityError:
			#ok, already in db
			dataset['processing_era_id'] = self.procsingid.execute(conn, pera['processing_version'])
			self.datasetCache['processingVersion'][pera['processing_version']] = dataset['processing_era_id']
		    except:
			tran.rollback
			raise
	    else:
		#no processing era for this dataset
		pass
	    #let's committe first 4 db acativties before going on.
	    tran.commit()
	except:
	    raise
	
	#Continue for the rest.
	try:
	    tran=conn.begnin()
	    #5 Deal with physics gruop
	    phg = dataset['physics_group_name']
	    if phg:
		#Yes, the dataset has physica group. 
		if phg in (self.datasetCache['phyGrp']).keys():
		    dataset['physics_group_id'] = self.datasetCache['phyGrp'][phg]
		else:
		    #find in db since not find it in cache
		    phgId = self.phygrpid.execute(conn, phg)
		    if phgId <=0 :
			#not in db yet, insert it
			phygrp={'physics_group_id':self.sm.increment(conn,"SEQ_PG"), 'physics_group_name':phg}
			self.phygrpin.execute(conn, phygrp, tran)
		    #cache it
		    self.datasetCache['phyGrp'][phg] = phgId
		    dataset['physics_group_id'] = phgId
	    else:
		#no physics gruop for the dataset.
		pass
	    del dataset['physics_group_name']
	    #6 Deal with Data tier. A dataset must has a data tier
	    dataT = dataset['data_tier_name']
	    #check cache
	    if dataT in (self.datasetCache['dataTier']).keys():
		dataset['data_tier_id'] = self.datasetCache['dataTier'][dataT]
	    else:
		#not in cache, check if in db
		dataTId = sef.tierid.execute(conn, dataT)
		if dataTId <= 0 :
		    #not in db. Insert the tier
		    #get the rest data from remote db
		    theTier = self.getRemoteData(sourceurl,'datatiers', 'data_tier_name', dataT)
		    dataTId = self.sm.increment(conn,"SEQ_DT")
		    theTier['data_tier_id'] = dataTId		    
		    self.tierin.execute(conn, theTier, tran)
		dataset['data_tier_id'] = dataTId
		self.datasetCache['dataTier'][dataT] = dataTId
	    del dataset['data_tier_name']
	    #7 Deal with dataset access type. A dataset must have a data type
	    dsTp = dataset['dataset_access_type']
	    #check cache
            if dsTp in (self.datasetCache['datasetAccTp']).keys():
                dataset['dataset_access_type_id'] = self.datasetCache['datasetAccTp'][dataT]
            else:
                #not in cache, check if in db
                dsTpId = sef.datatypeid.execute(conn, dsTp)
                if dsTpId <= 0 :
                    #not in db. Insert the type
                    dsTpId = self.sm.increment(conn,"SEQ_DTP")
                    theType={'dataset_access_type':dsTp, 'dataset_access_type_id':dsTpId}
                    self.datatypein.execute(conn, theType, tran)
                dataset['dataset_access_type_id'] = dsTpId
		self.datasetCache['datasetAccTp'][dataT] = dsTpId
            del dataset['data_access_type_id']
            tran.commit()
	except:
            tran.rollback()
            raise
	try:
	    tran.conn.begin()
	    #8 Finally, we have everything to insert a dataset
	    dataset['dataset_id'] = self.sm.increment(conn,"SEQ_DS")
	    self.datasetin.execute(conn, dataset, tran)
	    self.datasetCache['dataset'][dataset['dataset']]=dataset['dataset_id']
	    #9 Before we commit, make dataset and output module configure mapping	
	    for c in otptIdList:
		try:
		    dcId = self.sm.increment(conn,"SEQ_DC")
		    dcObj ={'ds_output_mod_conf_id': self.sm.increment(conn,"SEQ_DC"), \
                         'dataset_id':dataset['dataset_id'] , 'output_mod_config_id':c }
		    self.dcin.execute(conn, dcobj, tran)
		except exceptions.IntegrityError:
		    #ok, already in db
		    pass
		except:
		    raise 
	    #10 Fill Dataset Parentage
	    dsPList = blockcontent['blockcontent']
	    dsParentObjList=[]
	    for p in dsPList:
		dsParentObj={'dataset_parent_id': self.sm.increment(conn,"SEQ_DP"), 'this_dataset_id': dataset['dataset_id']\
                              'parent_dataset_id' : self.datasetid(conn, p['parent_dataset']}
		dsParentObjList.append(dsParentObj)
	    #insert dataset parentage in bulk
	    self.dsparentin(conn, dsParentObjList, tran)	    
	    tran.commit()
	except:
	    tran.rollback()
	    raise
	return dataset['dataset_id']
    
    def insertStatus(self, status = "UNKNOWN" ):
	"""
	This is a local function, basically component reports its status to database
	"""
	try:
	    conn = self.dbi.connection()
	    tran = conn.begin()
	    comp_status_id = self.sm.increment(conn, "SEQ_CS", transaction=tran)
	    statusObj={ "comp_status_id" : comp_status_id, "component_name" : "MIGRATION SERVICE", "component_status" : status, "last_contact_time" : str(int(time.time())) }
	    self.compstatusin.execute(conn, statusObj, tran)
	    tran.commit()
	except exceptions.IntegrityError, ex:
		    if str(ex).find("unique constraint") != -1 or str(ex).lower().find("duplicate") != -1:
			self.logger.warning("Component Already Known to DBS, ignoring...")
		    else:
			tran.rollback()
			self.logger.exception("DBS Insert Buffer Poller Exception: %s" %ex)
			raise
	except Exception, ex:
	    tran.rollback()
	    self.logger.exception("DBS Insert Buffer Poller Exception: %s" %ex)
	    raise
    	finally:
	    conn.close()

    def reportStatus(self, conn, status = "UNKNOWN" ):
	"""
	This is a local function, basically component reports its status to database
	"""
	try:
	    tran = conn.begin()
	    statusObj={ "component_name" : "MIGRATION SERVICE", "component_status" : status, "last_contact_time" : str(int(time.time())) }
	    self.compstatusup.execute(conn, statusObj, tran)
	    tran.commit()
	except Exception, ex:
	    tran.rollback()
	    self.logger.exception("DBS Insert Buffer Poller Exception: %s" %ex)

    # called by frk at the termination time
    def terminate(self, params):
	"""
	Terminate
	"""
	logging.debug("Terminating DBS Migration Service")

if __name__ == '__main__':
#----------------
# This section is just for testing
#---------------

    from WMCore.Configuration import Configuration, loadConfigurationFile
    from WMCore.Database.DBCore import DBInterface
    from WMCore.Database.DBFactory import DBFactory
    from sqlalchemy import create_engine
    import logging

    def configure(configfile):
        config = loadConfigurationFile(configfile)
	
	"""
        wconfig = cfg.section_("Webtools")
        app = wconfig.application
        appconfig = cfg.section_(app)
        service = list(appconfig.views.active._internal_children)[0]
        dbsconfig = getattr(appconfig.views.active, service)
        dbsconfig.formatter.object="WMCore.WebTools.RESTFormatter"
        config = Configuration()
        config.component_('DBS')
        config.DBS.application = app
        config.DBS.model       = dbsconfig.model
        config.DBS.formatter   = dbsconfig.formatter
        config.DBS.database    = dbsconfig.database
        config.DBS.dbowner     = dbsconfig.dbowner
        config.DBS.version     = dbsconfig.version
        config.DBS.default_expires = 300
        config = config.section_("DBS")
	"""

        print config
        return config

    def setupDB(config):
	
	logger = logging.getLogger()
	_engineMap = {}
	myThread = threading.currentThread()
	print config
	"""
	_defaultEngineParams = {"convert_unicode" : True,
                            "strategy": "threadlocal",
                            "pool_recycle": 7200}
	engine = _engineMap.setdefault(config.database.connectUrl,
                                         create_engine(config.database.connectUrl,
                                                       connect_args = {},
                                                       **_defaultEngineParams)
                                                  )
	"""

	myThread.logger=logger
	myThread.dbFactory = DBFactory(myThread.logger, config.CoreDatabase.connectUrl, options={})
        myThread.dbi = myThread.dbFactory.connect()
    	#dbInterface =  DBInterface(logger, engine)
        #myThread.dbi=dbInterface
#Run the test

    config=configure(os.environ['WMAGENT_CONFIG'])
    setupDB(config)

    migrator=DBSMigrationServicePoller(config)
    migrator.setup("NONE")
    migrator.algorithm("NONE")