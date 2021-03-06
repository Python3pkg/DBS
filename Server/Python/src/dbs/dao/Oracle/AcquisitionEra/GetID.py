#!/usr/bin/env python
"""
This module provides AcquisitionEra.GetID data access object.

"""
from WMCore.Database.DBFormatter import DBFormatter

class GetID(DBFormatter):
    """
    AcquisitionEra GetID DAO class.
    """
    def __init__(self, logger, dbi, owner):
        """
        Add schema owner and sql.
        """
        DBFormatter.__init__(self, logger, dbi)
        self.owner = "%s." % owner if not owner in ("", "__MYSQL__") else ""
        self.sql = \
	"""
	SELECT AE.ACQUISITION_ERA_ID, AE.ACQUISITION_ERA_NAME
	FROM %sACQUISITION_ERAS AE 
        WHERE AE.ACQUISITION_ERA_NAME = :acquisition_era_name 
	""" % (self.owner)

    def execute(self, conn, name, transaction = False):
        """
        returns id for a given acquisition_era
        Args: 
            name (str):  The name of acquisition era
        Returns:
           int.  The id of the acquisition era
        """
        binds = {"acquisition_era_name":name}
        result = self.dbi.processData(self.sql, binds, conn, transaction)
        plist = self.formatDict(result)
	if len(plist) < 1: return -1
        return plist[0]["acquisition_era_id"]
