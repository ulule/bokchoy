from bokchoy.conductors import base
from bokchoy.compat import as_text

import nsq

from .connection import ConnectionPool


class NSQConductor(base.Conductor):
    def __init__(self, *args, **kwargs):
        self.tcp_addresses = kwargs.pop('tcp_addresses')
        self.http_addresses = kwargs.pop('http_addresses')

        super(NSQConductor, self).__init__(*args, **kwargs)

        self.writer = nsq.Writer(self.tcp_addresses)
        self.writer.conns = {'pool': ConnectionPool(self.tcp_addresses)}

    def _publish(self, job, *args, **kwargs):
        countdown = kwargs.pop('countdown', None)

        if countdown:
            self.writer.dpub(job.task.queue, countdown * 1000, job.key)
        else:
            self.writer.pub(job.task.queue, job.key)

    def consume(self, topics, channel):
        self.logger.info("NSQ worker started, topics: {}, channel:{}, addresses:{}".format(','.join(topics), channel, ','.join(self.http_addresses)))

        for t in topics:
            nsq.Reader(message_handler=self.handle,
                       lookupd_http_addresses=self.http_addresses,
                       topic=t, channel=channel,
                       lookupd_poll_interval=15)
        nsq.run()

    def _get_job_id(self, message):
        return as_text(message.body)

    def _retry(self, job, message):
        message.requeue(time_ms=job.task.retry_interval * 1000)
