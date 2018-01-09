=====
Usage
=====

To use jrnr on an High Performance Computer with a slurm scheduler you need do this

At the top of your python module add this to the import section:: 

    from jrnr.jrnr import slurm_runner


Defining your job spec
~~~~~~~~~~~~~~~~~~~~~~

The main idea behind `jrnr` is that all your jobs can be specified programmatically by taking the cartesian product of each of the potential values for the input parameters. 

For example, we are frequently computing some transformation on a set of climate models over a series of years and rcp scenarios. In `jrnr` the job spec creationg routine takes lists of dictionaries, concatenates them into one list and then constructs the full set of possible parameters. In that situation we can parameterize our set of inputs similar to the following:  

jrnr writes a slurm batch script that gets submitted to a slurm job scheduler


then at the top of your function that will serve as your main function::

    @slurm_runner(job_spec=JOB_SPEC)

where `JOB_SPEC` is a list of dictionaries of the parameterized inputs for all the jobs you intend to run





 def _unpack_job(specs):
    job = {}
    for spec in specs:
        job.update(spec)
    return job
  


def generate_jobs(job_spec):
       for specs in itertools.product(*job_spec):
            yield _unpack_job(specs)
        

models = list(map(lambda x: dict(model=x), ['Model_1', 'Model_2']))

scenarios = list(map(lambda x: dict(scenarios=x), ['scenario_1', 'scenario_2']))

years = list(map(lambda x: dict(year=x), range(2000,2006)))

