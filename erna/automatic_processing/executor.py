import time
start_time = time.perf_counter()

import subprocess as sp
import os
import logging
import tempfile
import sys
import shutil
from glob import iglob
import zmq
import stat

from ..utils import chown

context = zmq.Context()
socket = context.socket(zmq.REQ)

log = logging.getLogger('erna')
log.setLevel(logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def main():
    log.info('FACT Tools executor started')

    host = os.environ['SUBMITTER_HOST']
    port = os.environ['SUBMITTER_PORT']
    socket.connect('tcp://{}:{}'.format(host, port))

    job_id = int(os.environ['JOB_NAME'].replace('erna_', ''))

    socket.send_pyobj({'job_id': job_id, 'status': 'running'})
    socket.recv()

    java = os.environ.get('JAVA_BIN', 'java')
    log.info('Using java executable: {}'.format(java))

    jar = os.path.abspath(os.environ['JARFILE'])
    log.info('Using jar: {}'.format(jar))

    xml = os.path.abspath(os.environ['XMLFILE'])
    log.info('Using xml: {}'.format(xml))

    output_dir = os.path.abspath(os.environ['OUTPUTDIR'])
    os.makedirs(output_dir, exist_ok=True)

    walltime = float(os.environ['WALLTIME'])
    log.info('Walltime = %.0f', walltime)

    job_name = 'fact_erna_job_id_'+str(job_id)+'_'
    with tempfile.TemporaryDirectory(prefix=job_name) as tmp_dir:
        log.debug('Using tmp directory: {}'.format(tmp_dir))
        facttools_output = os.path.join(tmp_dir, 'facttools_output')
        os.makedirs(facttools_output)

        call = [
            'java',
            '-XX:MaxHeapSize=1024m',
            '-XX:InitialHeapSize=512m',
            '-XX:CompressedClassSpaceSize=64m',
            '-XX:MaxMetaspaceSize=128m',
            '-XX:+UseConcMarkSweepGC',
            '-XX:+UseParNewGC',
            '-jar',
            jar,
            xml,
        ]

        for k, v in os.environ.items():
            if k.startswith('facttools_'):
                option = '-D{}={}'.format(k.replace('facttools_', '', 1), v)
                call.append(option)

        try:
            sp.run(['which', java], check=True)
            sp.run(['free', '-m'], check=True)
            sp.run([java, '-Xmx512m', '-version'], check=True)

            log.info('Calling fact-tools with call: {}'.format(call))
            timeout = walltime - (time.perf_counter() - start_time) - 300
            log.info('Setting fact-tools timout to %.0f', timeout)
            sp.run(call, cwd=tmp_dir, check=True, timeout=timeout)
        except sp.CalledProcessError:
            socket.send_pyobj({'job_id': job_id, 'status': 'failed'})
            socket.recv()
            log.exception('Running FACT-Tools failed')
            sys.exit(1)
        except sp.TimeoutExpired:
            socket.send_pyobj({'job_id': job_id, 'status': 'walltime_exceeded'})
            log.exception('FACT Tools about to run into wall-time, terminating')
            socket.recv()
            sys.exit(1)

        try:
            output_file = next(iglob(os.path.join(facttools_output, '*')))
            log.info('Copying {} to {}'.format(output_file, output_dir))
            shutil.copy2(output_file, output_dir)
            output_file = os.path.join(output_dir, os.path.basename(output_file))
            log.info('Copy done')
        except:
            log.exception('Error copying outputfile')
            socket.send_pyobj({'job_id': job_id, 'status': 'failed'})
            socket.recv()
            sys.exit(1)

    try:
        process = sp.run(['md5sum', output_file], check=True, stdout=sp.PIPE)
        md5hash, _ = process.stdout.decode().split()
    except:
        log.exception('Error calculating md5sum')
        socket.send_pyobj({'job_id': job_id, 'status': 'failed'})
        socket.recv()
        sys.exit(1)

    try:
        groupname = os.environ.get('ERNA_GROUP', None)
        chown(output_file, username=None, groupname=groupname)
        os.chmod(output_file, stat.S_IWUSR | stat.S_IRUSR | stat.S_IWGRP | stat.S_IRGRP)
    except OSError:
        log.exception('Error setting file permissions')
        socket.send_pyobj({'job_id': job_id, 'status': 'failed'})
        socket.recv()
        sys.exit(1)

    socket.send_pyobj({
        'job_id': job_id,
        'status': 'success',
        'output_file': output_file,
        'md5hash': md5hash,
    })
    socket.recv()

if __name__ == '__main__':
    main()
