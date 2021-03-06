import elasticsearch
import curator
import os
import json
import string, random, tempfile
import time
from click import testing as clicktest
from mock import patch, Mock

from . import CuratorTestCase
from . import testvars as testvars

import logging
logger = logging.getLogger(__name__)

host, port = os.environ.get('TEST_ES_SERVER', 'localhost:9200').split(':')
port = int(port) if port else 9200
# '      repository: {0}\n'
# '      - filtertype: {1}\n'
# '        source: {2}\n'
# '        direction: {3}\n'
# '        timestring: {4}\n'
# '        unit: {5}\n'
# '        unit_count: {6}\n'
# '        epoch: {7}\n')
class TestCLIDeleteSnapshots(CuratorTestCase):
    def test_deletesnapshot(self):
        def add_docs(idx):
            for i in ["1", "2", "3"]:
                self.client.create(
                    index=idx, doc_type='log',
                    body={"doc" + i :'TEST DOCUMENT'},
                )
                # This should force each doc to be in its own segment.
                self.client.indices.flush(index=idx, force=True)
        ### Create snapshots to delete and verify them
        self.create_repository()
        timestamps = []
        for i in range(1,4):
            add_docs('my_index{0}'.format(i))
            ilo = curator.IndexList(self.client)
            snap = curator.Snapshot(ilo, repository=self.args['repository'],
                name='curator-%Y%m%d%H%M%S'
            )
            snap.do_action()
            snapshot = curator.get_snapshot(
                        self.client, self.args['repository'], '_all'
                       )
            self.assertEqual(i, len(snapshot['snapshots']))
            time.sleep(1.0)
            timestamps.append(int(time.time()))
            time.sleep(1.0)
        ### Setup the actual delete
        self.write_config(
            self.args['configfile'], testvars.client_config.format(host, port))
        self.write_config(self.args['actionfile'],
            testvars.delete_snap_proto.format(
                self.args['repository'], 'age', 'creation_date', 'older', ' ',
                'seconds', '0', timestamps[0]
            )
        )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--config', self.args['configfile'],
                        self.args['actionfile']
                    ],
                    )
        snapshot = curator.get_snapshot(
                    self.client, self.args['repository'], '_all'
                   )
        self.assertEqual(2, len(snapshot['snapshots']))
    def test_no_repository(self):
        self.write_config(
            self.args['configfile'], testvars.client_config.format(host, port))
        self.write_config(self.args['actionfile'],
            testvars.delete_snap_proto.format(
                ' ', 'age', 'creation_date', 'older', ' ',
                'seconds', '0', ' '
            )
        )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--config', self.args['configfile'],
                        self.args['actionfile']
                    ],
                    )
        self.assertEqual(1, result.exit_code)
    def test_extra_options(self):
        self.write_config(
            self.args['configfile'], testvars.client_config.format(host, port))
        self.write_config(self.args['actionfile'],
            testvars.bad_option_proto_test.format('delete_snapshots'))
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--config', self.args['configfile'],
                        self.args['actionfile']
                    ],
                    )
        self.assertEqual(1, result.exit_code)
