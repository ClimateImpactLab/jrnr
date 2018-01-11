=====
Usage
=====

`jrnr` is a python library currently configured to work on systems using `slurm workload managers <https://slurm.schedmd.com/>`_. If your computing workflows can be parallelized, `jrnr` can help.

`jrnr` is an application that relies on `click <http://click.pocoo.org/5/>`_, the python command line tool. 

At the top of your python module add this to the `import` section:: 

    from jrnr.jrnr import slurm_runner


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
--------------

How does this `jrnr` track the status of my jobs? 

In your directory where you are running your job, `jrnr` creates a `locks` directory. In this `locks` directory, for each job in your set of batch jobs a file is created with the following structure `{job_name}-{unique_id}-{job_index}.` When a node is working on a job, it adds the `.lck` file extension to the file. When the job is completed, it converts the `.lck` extension to a `.done` extension. If, for some reason, the job encounters an error, the extension will shift to `.err`. When you call the `status` command `jrnr` is just displaying the count of files with each file extension in the locks directory. 

