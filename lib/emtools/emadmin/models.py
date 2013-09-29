import datetime
import logging

from django.db import models
from django.db import transaction

class Schedule(models.Model):
    name = models.CharField(max_length=32)
    last_run = models.DateTimeField()
    next_run = models.DateTimeField()

    class Meta:
        ordering = ["name"]

    def is_late(self):
        now = datetime.datetime.utcnow()
        return self.next_run < now

class LogRecord(models.Model):
    timestamp = models.DateTimeField()
    message = models.TextField()

    class Meta:
        ordering = ["-timestamp"]

class DBHandler(logging.Handler):
    def emit(self, record):
        sid = transaction.savepoint()
        try:
            LogRecord.objects.create(
                timestamp=datetime.datetime.utcfromtimestamp(record.created),
                message=self.format(record))
            transaction.savepoint_commit(sid)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            transaction.savepoint_rollback(sid)
            self.handleError(record)        

# Set up the logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = DBHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)-10s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
