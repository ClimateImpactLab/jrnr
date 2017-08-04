
from __future__ import absolute_import

import re
import os
import time
import math
import toolz
import click
import pprint
import logging
import itertools
import functools
import subprocess

from jrnr._compat import exclusive_open

FORMAT = '%(asctime)-15s %(message)s'

logger = logging.getLogger('uploader')
logger.setLevel('DEBUG')

formatter = logging.Formatter(FORMAT)

SLURM_SCRIPT = '''
#!/bin/bash
# Job name:
#SBATCH --job-name={jobname}
#
# Partition:
#SBATCH --partition={partition}
#
# Account:
#SBATCH --account=co_laika
#
# QoS:
#SBATCH --qos=savio_lowprio
#
#SBATCH --nodes=1
#
# Wall clock limit:
#SBATCH --time=72:00:00
#
#SBATCH --requeue
{dependencies}
{output}
'''.strip()

SLURM_MULTI_SCRIPT = SLURM_SCRIPT + '''
#
#SBATCH --array=0-{maxnodes}

# set up directories
mkdir -p {logdir}
mkdir -p locks

## Run command

for i in {{1..{jobs_per_node}}}
do
    nohup python {filepath} do_job --job_name {jobname} \
--job_id {uniqueid} --num_jobs {numjobs} --logdir "{logdir}" {flags} \
> {logdir}/nohup-{jobname}-{uniqueid}-${{SLURM_ARRAY_TASK_ID}}-$i.out &
done

python {filepath} wait --job_name {jobname} \
--job_id {uniqueid} --num_jobs {numjobs} {flags}
'''

SLURM_SINGLE_SCRIPT = SLURM_SCRIPT + '''

## Run command
python {filepath} {flags}
'''


def _product(values):
    '''
    Examples
    --------

    .. code-block:: python

        >>> _product([3, 4, 5])
        60

    '''
    return functools.reduce(lambda x, y: x*y, values, 1)


def _unpack_job(specs):
    job = {}
    for spec in specs:
        job.update(spec)
    return job


def generate_jobs(job_spec):
    for specs in itertools.product(*job_spec):
        yield _unpack_job(specs)


def count_jobs(job_spec):
    return _product(map(len, job_spec))


def _prep_slurm(
        filepath,
        jobname='slurm_job',
        partition='savio2',
        job_spec=None,
        limit=None,
        uniqueid='"${SLURM_ARRAY_JOB_ID}"',
        jobs_per_node=24,
        maxnodes=100,
        dependencies=None,
        logdir='log',
        flags=None):

    depstr = ''

    if (dependencies is not None) and (len(dependencies) > 1):
        status, deps = dependencies

        if len(deps) > 0:

            depstr += (
                '#\n#SBATCH --dependency={}:{}'
                .format(status, ','.join(map(str, deps))))

    if flags:
        flagstr = ' '.join(map(str, flags))
    else:
        flagstr = ''

    if job_spec:
        n = count_jobs(job_spec)

        if limit is not None:
            n = min(limit, n)

        numjobs = n

        output = (
                '#\n#SBATCH --output {logdir}/slurm-{jobname}-%A_%a.out'
                .format(jobname=jobname, logdir=logdir))

        template = SLURM_MULTI_SCRIPT

    else:
        numjobs = 1
        output = (
                '#\n#SBATCH --output {logdir}/slurm-{jobname}-%A.out'
                .format(jobname=jobname, logdir=logdir))

        template = SLURM_SINGLE_SCRIPT

    with open('run-slurm.sh', 'w+') as f:
        f.write(template.format(
            jobname=jobname,
            partition=partition,
            numjobs=numjobs,
            jobs_per_node=jobs_per_node,
            maxnodes=(maxnodes-1),
            uniqueid=uniqueid,
            filepath=filepath.replace(os.sep, '/'),
            dependencies=depstr,
            flags=flagstr,
            logdir=logdir,
            output=output))


def run_slurm(
        filepath,
        jobname='slurm_job',
        partition='savio2',
        job_spec=None,
        limit=None,
        uniqueid='"${SLURM_ARRAY_JOB_ID}"',
        jobs_per_node=24,
        maxnodes=100,
        dependencies=None,
        logdir='log',
        flags=None):

    _prep_slurm(
        filepath=filepath,
        jobname=jobname,
        partition=partition,
        job_spec=job_spec,
        limit=limit,
        uniqueid=uniqueid,
        jobs_per_node=jobs_per_node,
        maxnodes=maxnodes,
        dependencies=dependencies,
        logdir=logdir,
        flags=flags)

    job_command = ['sbatch', 'run-slurm.sh']

    proc = subprocess.Popen(
        job_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    out, err = proc.communicate()

    matcher = re.search(r'^\s*Submitted batch job (?P<run_id>[0-9]+)\s*$', out)

    if matcher:
        run_id = int(matcher.group('run_id'))
    else:
        run_id = None

    if err:
        raise OSError('Error encountered submitting job: {}'.format(err))

    return run_id


def get_job_by_index(job_spec, index):
    '''
    Examples
    --------

    .. code-block:: python

        >>> job = get_job_by_index(
        ...    (
        ...        [{'let': 'a'}, {'let': 'b'}, {'let': 'c'}],
        ...        [{'num': 1}, {'num': 2}, {'num': 3}],
        ...        [{'pitch': 'do'}, {'pitch': 'rey'}, {'pitch': 'mi'}]),
        ...    5)
        ...
        >>> sorted(zip(job.keys(), job.values())) # test job ordered
        [('let', 'a'), ('num', 2), ('pitch', 'mi')]

        >>> job = get_job_by_index(
        ...     tuple(map(
        ...         lambda x: [{x: i} for i in x],
        ...         ['hi', 'hello', 'bye'])),
        ...     10)
        ...
        >>> sorted(zip(job.keys(), job.values())) # test job ordered
        [('bye', 'y'), ('hello', 'l'), ('hi', 'h')]


    '''

    return _unpack_job([
        job_spec[i][
            (index//(_product(map(len, job_spec[i+1:]))) % len(job_spec[i]))]
        for i in range(len(job_spec))])


def _get_call_args(job_spec, index=0):
    '''
    Places stringified job parameters into `metadata` dict along with job spec

    .. code-block:: python

        >>> job_spec = (
        ...     [{'ordinal': 1, 'zeroth': 0}, {'ordinal': 2, 'zeroth': 1}],
        ...     [{'letter': 'a'}, {'letter': 'b'}],
        ...     [{'name': 'susie', 'age': 8}, {'name': 'billy', 'age': 6}])
        ...
        >>> job = _get_call_args(job_spec, 2)
        >>> job # doctest: +SKIP
        {'age': 8, 'letter': 'b', 'name': 'susie', 'ordinal': 1, 'zeroth': 0}

        >>> notmeta = {k: v for k, v in job.items() if k != 'metadata'}
        >>> meta = job['metadata']
        >>> sorted(zip(notmeta.keys(), notmeta.values())) \
        # doctest: +NORMALIZE_WHITESPACE
        [('age', 8), ('letter', 'b'), ('name', 'susie'),
        ('ordinal', 1), ('zeroth', 0)]

        >>> sorted(zip(meta.keys(), meta.values())) \
        # doctest: +NORMALIZE_WHITESPACE
        [('age', '8'), ('letter', 'b'), ('name', 'susie'),
        ('ordinal', '1'), ('zeroth', '0')]
    '''

    job = get_job_by_index(job_spec, index)

    metadata = {}
    metadata.update({k: str(v) for k, v in job.items()})

    call_args = {'metadata': metadata}
    call_args.update(job)

    return call_args


@toolz.curry
def slurm_runner(run_job, filepath, job_spec, onfinish=None):

    @click.group()
    def slurm():
        pass

    @slurm.command()
    @click.option(
        '--limit', '-l', type=int, required=False, default=None,
        help='Number of iterations to run')
    @click.option(
        '--jobs_per_node', '-n', type=int, required=False, default=24,
        help='Number of jobs to run per node')
    @click.option(
        '--maxnodes', '-x', type=int, required=False, default=100,
        help='Number of nodes to request for this job')
    @click.option(
        '--jobname', '-j', default='test', help='name of the job')
    @click.option(
        '--partition', '-p', default='savio2', help='resource on which to run')
    @click.option('--dependency', '-d', type=int, multiple=True)
    @click.option(
        '--logdir', '-L', default='log', help='Directory to write log files')
    @click.option(
        '--uniqueid', '-u', default='"${SLURM_ARRAY_JOB_ID}"',
        help='Unique job pool id')
    def prep(
            limit=None,
            jobs_per_node=24,
            jobname='slurm_job',
            dependency=None,
            partition='savio2',
            maxnodes=100,
            logdir='log',
            uniqueid='"${SLURM_ARRAY_JOB_ID}"'):

        _prep_slurm(
            filepath=filepath,
            jobname=jobname,
            partition=partition,
            job_spec=job_spec,
            jobs_per_node=jobs_per_node,
            maxnodes=maxnodes,
            limit=limit,
            uniqueid=uniqueid,
            logdir=logdir,
            dependencies=('afterany', list(dependency)))

    @slurm.command()
    @click.option(
        '--limit', '-l', type=int, required=False, default=None,
        help='Number of iterations to run')
    @click.option(
        '--jobs_per_node', '-n', type=int, required=False, default=24,
        help='Number of jobs to run per node')
    @click.option(
        '--maxnodes', '-x', type=int, required=False, default=100,
        help='Number of nodes to request for this job')
    @click.option(
        '--jobname', '-j', default='test', help='name of the job')
    @click.option(
        '--partition', '-p', default='savio2', help='resource on which to run')
    @click.option(
        '--dependency', '-d', type=int, multiple=True)
    @click.option(
        '--logdir', '-L', default='log', help='Directory to write log files')
    @click.option(
        '--uniqueid', '-u', default='"${SLURM_ARRAY_JOB_ID}"',
        help='Unique job pool id')
    def run(
            limit=None,
            jobs_per_node=24,
            jobname='slurm_job',
            dependency=None,
            partition='savio2',
            maxnodes=100,
            logdir='log',
            uniqueid='"${SLURM_ARRAY_JOB_ID}"'):

        if not os.path.isdir(logdir):
            os.makedirs(logdir)

        slurm_id = run_slurm(
            filepath=filepath,
            jobname=jobname,
            partition=partition,
            job_spec=job_spec,
            jobs_per_node=jobs_per_node,
            maxnodes=maxnodes,
            limit=limit,
            uniqueid=uniqueid,
            logdir=logdir,
            dependencies=('afterany', list(dependency)))

        finish_id = run_slurm(
            filepath=filepath,
            jobname=jobname+'_finish',
            partition=partition,
            dependencies=('afterany', [slurm_id]),
            logdir=logdir,
            flags=['cleanup', slurm_id])

        print('run job: {}\non-finish job: {}'.format(slurm_id, finish_id))

    @slurm.command()
    @click.argument('slurm_id')
    def cleanup(slurm_id):
        proc = subprocess.Popen(
            [
                'sacct', '-j', slurm_id,
                '--format=JobID,JobName,MaxRSS,Elapsed,State'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        out, err = proc.communicate()

        print(out)

        if onfinish:
            onfinish()

    @slurm.command()
    @click.option('--job_name', required=True)
    @click.option('--job_id', required=True)
    @click.option('--num_jobs', required=True, type=int)
    @click.option(
        '--logdir', '-L', default='log', help='Directory to write log files')
    def do_job(job_name, job_id, num_jobs=None, logdir='log'):

        if not os.path.isdir('locks'):
            os.makedirs('locks')

        if not os.path.isdir(logdir):
            os.makedirs(logdir)

        for task_id in range(num_jobs):

            lock_file = (
                'locks/{}-{}-{}.{{}}'
                .format(job_name, job_id, task_id))

            if os.path.exists(lock_file.format('done')):
                print('{} already done. skipping'.format(task_id))
                continue

            elif os.path.exists(lock_file.format('err')):
                print('{} previously errored. skipping'.format(task_id))
                continue

            try:
                with exclusive_open(lock_file.format('lck')):
                    pass

                # Check for race conditions
                if os.path.exists(lock_file.format('done')):
                    print('{} already done. skipping'.format(task_id))
                    if os.path.exists(lock_file.format('lck')):
                        os.remove(lock_file.format('lck'))
                    continue

                elif os.path.exists(lock_file.format('err')):
                    print('{} previously errored. skipping'.format(task_id))
                    if os.path.exists(lock_file.format('lck')):
                        os.remove(lock_file.format('lck'))
                    continue

            except OSError:
                print('{} already in progress. skipping'.format(task_id))
                continue

            handler = logging.FileHandler(os.path.join(
                logdir,
                'run-{}-{}-{}.log'.format(job_name, job_id, task_id)))
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)

            logger.addHandler(handler)

            try:

                job_kwargs = _get_call_args(job_spec, task_id)

                logger.debug('Beginning job\nkwargs:\t{}'.format(
                    pprint.pformat(job_kwargs['metadata'], indent=2)))

                run_job(**job_kwargs)

            except (KeyboardInterrupt, SystemExit):
                raise

            except Exception as e:
                logger.error(
                    'Error encountered in job {} {} {}'
                    .format(job_name, job_id, task_id),
                    exc_info=e)

                with open(lock_file.format('err'), 'w+'):
                    pass

            else:
                with open(lock_file.format('done'), 'w+'):
                    pass

            finally:
                if os.path.exists(lock_file.format('lck')):
                    os.remove(lock_file.format('lck'))

                logger.removeHandler(handler)

    @slurm.command()
    @click.option('--job_name', '-j', required=True)
    @click.option('--job_id', '-u', required=True)
    def status(job_name, job_id, num_jobs=None, logdir='log'):
        n = count_jobs(job_spec)
        locks = os.listdir('locks')

        count = int(math.log10(n)//1 + 1)

        locked = len([
            i for i in range(n)
            if '{}-{}-{}.lck'.format(job_name, job_id, i) in locks])

        done = len([
            i for i in range(n)
            if '{}-{}-{}.done'.format(job_name, job_id, i) in locks])

        err = len([
            i for i in range(n)
            if '{}-{}-{}.err'.format(job_name, job_id, i) in locks])

        print(
            ("\n".join(["{{:<15}}{{:{}d}}".format(count) for _ in range(4)]))
            .format(
                'jobs:', n,
                'done:', done,
                'in progress:', locked,
                'errored:', err))

    @slurm.command()
    @click.option('--job_name', required=True)
    @click.option('--job_id', required=True)
    @click.option('--num_jobs', required=True, type=int)
    def wait(job_name, job_id, num_jobs=None):

        for task_id in range(num_jobs):
            while not os.path.exists(
                        'locks/{}-{}-{}.done'
                        .format(job_name, job_id, task_id)):
                time.sleep(10)

    def run_interactive(task_id=0):

        job_kwargs = _get_call_args(job_spec, task_id)

        logger.debug('Beginning job\nkwargs:\t{}'.format(
            pprint.pformat(job_kwargs['metadata'], indent=2)))

        return run_job(interactive=True, **job_kwargs)

    slurm.run_interactive = run_interactive

    return slurm
