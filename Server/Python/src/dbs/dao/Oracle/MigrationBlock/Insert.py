""" DAO Object for MigrationBlocks table """ 

from WMCore.Database.DBFormatter import DBFormatter
from dbs.utils.dbsExceptionHandler import dbsExceptionHandler

class Insert(DBFormatter):
    """ Migration Insert DAO Class"""

    def __init__(self, logger, dbi, owner):
        DBFormatter.__init__(self, logger, dbi)
        self.owner = "%s." % owner
        self.owner = "%s." % owner if not owner in ("", "__MYSQL__") else ""
        self.logger = logger
        self.sql = \
"""
INSERT INTO %sMIGRATION_BLOCKS
(MIGRATION_BLOCK_ID, MIGRATION_REQUEST_ID, MIGRATION_BLOCK_NAME, MIGRATION_ORDER, MIGRATION_STATUS, CREATION_DATE, CREATE_BY, LAST_MODIFICATION_DATE, LAST_MODIFIED_BY)
VALUES(:migration_block_id, :migration_request_id, :migration_block_name, :migration_order, :migration_status, :creation_date, :create_by, :last_modification_date, :last_modified_by)
""" % self.owner

    def execute(self, conn, daoinput, transaction = False):
        """
	insert into MIGRATION_BLOCKS
        """
        if not conn:
            dbsExceptionHandler("dbsException-failed-connect2host", "Oracle/MigrationBlock/Insert. Expects db connection from upper layer.", self.logger.exception)

        self.dbi.processData(self.sql, daoinput, conn, transaction)
