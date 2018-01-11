=====
Usage
=====

`jrnr` is a python library currently configured to work on systems using `slurm workload managers <https://slurm.schedmd.com/>`_. If your computing workflows can be parallelized, `jrnr` can help.

`jrnr` is an application that relies on `click <http://click.pocoo.org/5/>`_, the python command line tool. 

At the top of your python module add this to the `import` section:: 

    from jrnr.jrnr import slurm_runner

Interactive mode
~~~~~~~~~~~~~~~~

Frequently, you'll want to do some basic debugging and iteration to make sure your batch jobs will run as expected. To assist this process, `jrnr` has an interactive mode that allows you to run a single job in an `ipython` session. 

.. code-block:: ipython

    In [1]: import tas

    In [2]: tas.make_tas.run_interactive(42)

    2018-01-10 17:01:55,001 Beginning job
    kwargs: { 'model': 'NorESM1-M', 'scenario': 'rcp45', 'year': '2054'}
    2018-01-10 17:02:43,733 beginning
    2018-01-10 17:02:43,733 producing_tas
    Out[3]: 
    <xarray.Dataset>
    Dimensions:  (lat: 720, lon: 1440, time: 365)
    Coordinates:
      * lon      (lon) float32 -179.875 -179.625 -179.375 -179.125 -178.875 ...
      * time     (time) datetime64[ns] 2054-01-01T12:00:00 2054-01-02T12:00:00 ...
      * lat      (lat) float32 -89.875 -89.625 -89.375 -89.125 -88.875 -88.625 ...
    Data variables:
        tas      (time, lat, lon) float32 272.935 272.937 272.931 272.911 ...
    Attributes:
        version:         1.0
        repo:            https://gitlab.com/ClimateImpactLab/make_tas/
        frequency:       annual
        oneline:         Average Daily Temperature, tavg
        file:            tas.py
        year:            2054
        write_variable:  tas
        description:     Average Daily Temperature, tavg\n\n Average Daily Temper...
        execute:         python tas.py run
        project:         gcp
        team:            climate
        dependencies:    ['/global/scratch/groups/co_laika/gcp/climate/nasa_bcsd/...
        model:           NorESM1-M


As you can see, if you setting up logging, the logging information will print to wherever you direct stdout. In this case, ininteractive mode, it prints to the ipython terminal. In batch mode, jrnr logs can be found in the directory you specified as ``run-{job_name}-{job_id}-{task-id}.log``. 



Running your job
~~~~~~~~~~~~~~~~

The `slurm_runner` decorator function in `jrnr` acts as a wrapper around your main function. Make sure that above your main function you have added `@slurm_runner()`. With this enabled, you can use the command line to launch your jobs on the `slurm workload manager <https://slurm.schedmd.com/>`_. 

Make sure you are in the directory where your python module is located. Let's say we are running the job specified in `tas.py`. Let's look at what the `help` function does. 

.. code-block:: bash

    $ python tas.py --help

    Usage: tas.py [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      cleanup
      do_job
      prep
      run
      status
      wait


We can see that this will give us the list of options. Let's look at `run`.

`run`
~~~~~

Let's first have a look at the options with the run command. 

.. code-block:: bash

    $ python run --help

    Usage: tas.py run [OPTIONS]

    Options:
      -l, --limit INTEGER          Number of iterations to run
      -n, --jobs_per_node INTEGER  Number of jobs to run per node
      -x, --maxnodes INTEGER       Number of nodes to request for this job
      -j, --jobname TEXT           name of the job
      -p, --partition TEXT         resource on which to run
      -d, --dependency INTEGER
      -L, --logdir TEXT            Directory to write log files
      -u, --uniqueid TEXT          Unique job pool id
      --help                       Show this message and exit.

The most important options are `u`, `j` and `L`. To specify a job you need `u` and `j` since these parameters uniquely identify a job and allow you to track the progress of your jobs. An example command is below

.. code-block:: bash

    $ python tas.py run -u 001 -j tas 

This creates a job with a unique id of `001` and a job name of `tas`.

By specifying some of the options listed above, you can adjust the behavior of your slurm jobs. For example, you can put your log files in a specific directory by specifying a value for argument `L`. Additionally, if you want to use a specific partition on your cluster you can specify the `p` option. Similarly, if your job is particularly compute intensive, with `n` you can adjust the number of jobs per node.

.. code-block:: bash

    $ python tas.py run -u 001 -j tas -L /logs/tas/ -p savio2_bigmem -n 10

Its important to note that, by default, log files will be written to the directory where you are executing the file. Depending on how large your job is you may want to put these log files elsewhere. 


`status`
~~~~~~~~

You launched your job 10 minutes ago and you want to check on the status of your jobs. We can check with the `status` option. Let's look again at our `tas.py` file. 

.. code-block:: bash

    $ python tas.py status -u 001 -j tas

    jobs:          4473
    done:          3000
    in progress:   1470
    errored:          3

Notice that we use the unique id `001` and the jobname `tas` that we used when we created the job. You must use these values or we cannot compute the progress of our job.


Technical note
~~~~~~~~~~~~~~

How does this `jrnr` track the status of my jobs? 
-------------------------------------------------

In your directory where you are running your job, `jrnr` creates a `locks` directory. In this `locks` directory, for each job in your set of batch jobs a file is created with the following structure `{job_name}-{unique_id}-{job_index}.` When a node is working on a job, it adds the `.lck` file extension to the file. When the job is completed, it converts the `.lck` extension to a `.done` extension. If, for some reason, the job encounters an error, the extension will shift to `.err`. When you call the `status` command `jrnr` is just displaying the count of files with each file extension in the locks directory. 


How does `jrnr` construct a job specification?
----------------------------------------------

Each `jrnr` job can be specified with arguments from key, value dictionaries. Since these arguments are taken from a set of known possible inputs we can take each key and its associated set of possible values and compute the cartesian product of every key, value combination. In the background of `jrnr`, we take lists of dictionaries and use the python method `itertools.product` to specify the superset of possible batch jobs. An demonstration is below: 


.. code-block:: ipython

  In [1]: def generate_jobs(job_spec):
            for specs in itertools.product(*job_spec):
              yield _unpack_job(specs)


  In [2]: def _unpack_job(specs):
              job = {}
              for spec in specs:
                  job.update(spec)
              return job


  In [3]: MODELS = list(map(lambda x: dict(model=x), [
          'ACCESS1-0',
          'bcc-csm1-1',
          'BNU-ESM',
          'CanESM2',
          ]))

  In [4]: PERIODS = (
          [dict(scenario='historical', year=y) for y in range(1981, 2006)] +
          [dict(scenario='rcp45',  year=y) for y in range(2006, 2100)]

  In [5]: job_spec = [PERIODS, MODELS]

  In [6]: jobs = list(generate_jobs(job_spec))

  In [7]: jobs[:100:10]
  Out[7]:
  [{'model': 'ACCESS1-0', 'scenario': 'historical', 'year': 1981},
  {'model': 'BNU-ESM', 'scenario': 'historical', 'year': 1983},
  {'model': 'ACCESS1-0', 'scenario': 'historical', 'year': 1986},
  {'model': 'BNU-ESM', 'scenario': 'historical', 'year': 1988},
  {'model': 'ACCESS1-0', 'scenario': 'historical', 'year': 1991},
  {'model': 'BNU-ESM', 'scenario': 'historical', 'year': 1993},
  {'model': 'ACCESS1-0', 'scenario': 'historical', 'year': 1996},
  {'model': 'BNU-ESM', 'scenario': 'historical', 'year': 1998},
  {'model': 'ACCESS1-0', 'scenario': 'historical', 'year': 2001},
  {'model': 'BNU-ESM', 'scenario': 'historical', 'year': 2003}]





