'''

This module demonstrates the specification of a jrnr script

This jrnr script will compute daily average temperature 
as a the average of daily max and min temperature. 

To run, jrnr requires a parameterized job spec. This is constructed 
as a list on line 105 and handed to jrnr's `slurm_runner` decorator on line 123.

Each job, interactive and batch, in jrnr receives a 
dictionary which fully parameterizes the input arguments. 

To parameterize your job spec jrnr takes the 
cartesian product of the items in lists of dictionaries. 
`JOB_SPEC` on line 112 is simply a list of those lists. 
'''

import os
import logging
import time
import xarray as xr
import pandas as pd
import numpy as np
import climate_toolbox.climate_toolbox as ctb 
from jrnr.jrnr import slurm_runner

#set up logging format and configuration
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('uploader')
logger.setLevel('DEBUG')


description = '\n\n'.join(
        map(lambda s: ' '.join(s.split('\n')),
            __doc__.strip().split('\n\n')))

oneline = description.split('\n')[0]

__author__ = 'Justin Simcock'
__contact__ = 'jsimcock@rhg.com'
__version__ = '1.0'


READ_PATH = (
    '/global/scratch/groups/co_laika/gcp/climate/nasa_bcsd/reformatted/' +
    '{scenario}/{model}/{variable}/' +
    '{variable}_day_BCSD_{scenario}_r1i1p1_{model}_{year}/1.0.nc4')

WRITE_PATH = ('/global/scratch/groups/co_laika/gcp/climate/nasa_bcsd/reformatted/' +
                '{scenario}/{model}/{variable}/' + 
                '{variable}_day_BCSD_{scenario}_r1i1p1_{model}_{year}/' +
                '{version}.nc4')


ADDITIONAL_METADATA = dict(
    oneline=oneline,
    description=description,
    author=__author__,
    contact=__contact__,
    version=__version__,
    repo='https://gitlab.com/ClimateImpactLab/make_tas/',
    file=str(__file__),
    execute='python {} run'.format(str(__file__)),
    project='gcp',
    team='climate',
    frequency='annual',
    write_variable='tas',
    dependencies='')


def make_tas_ds(tasmax, tasmin):

    tas = xr.Dataset()
    tas['tas'] = (tasmax.tasmax + tasmin.tasmin) / 2.
    return tas

PERIODS = (
    [dict(scenario='historical', year=y) for y in range(1981, 2006)] +
    [dict(scenario='rcp45',  year=y) for y in range(2006, 2100)] +
    [dict(scenario='rcp85', year=y) for y in range(2006, 2100)])


MODELS = list(map(lambda x: dict(model=x), [
    'ACCESS1-0',
    'bcc-csm1-1',
    'BNU-ESM',
    'CanESM2',
    'CCSM4',
    'CESM1-BGC',
    'CNRM-CM5',
    'CSIRO-Mk3-6-0',
    'GFDL-CM3',
    'GFDL-ESM2G',
    'GFDL-ESM2M',
    'IPSL-CM5A-LR',
    'IPSL-CM5A-MR',
    'MIROC-ESM-CHEM',
    'MIROC-ESM',
    'MIROC5',
    'MPI-ESM-LR',
    'MPI-ESM-MR',
    'MRI-CGCM3',
    'inmcm4',
    'NorESM1-M'
    ]))


JOB_SPEC = [MODELS, PERIODS]

def validate_tas(tas):
    '''
    Make sure NaNs are not present
    '''
    msg_null = 'DataArray contains NaNs'
    msg_shape = 'DataSet dims {} do not match expected'
    tas_nan = tas.tas.sel(lat=slice(-85,85)).isnull().sum().values
    assert tas_nan == 0 , msg_null
    assert tas.dims['lat'] == 720,  msg_shape.format(tas.dims['lat'])
    assert tas.dims['lon'] == 1440, msg_shape.format(tas.dims['lon'])
    assert tas.dims['time'] in [364, 365, 366], msg_shape.format(tas.dims['time']) 
    assert tas.lon.min().values == -179.875
    assert tas.lon.max().values == 179.875
    return


@slurm_runner(job_spec=JOB_SPEC)
def make_tas(metadata,
            scenario,
            year,
            model,
            interactive=False
            ):


    metadata.update(ADDITIONAL_METADATA)

    tasmin_read = READ_PATH.format(variable='tasmin', **metadata)
    tasmax_read = READ_PATH.format(variable='tasmax', **metadata)

    metadata['dependencies'] = str([tasmin_read, tasmax_read])

    tas_write = WRITE_PATH.format(variable='tas', **metadata)


    if os.path.isfile(tas_write) and not interactive:
        tas = xr.open_dataset(tas_write, autoclose=True, chunks={'time': 100}).load()
        tas = ctb._standardize_longitude_dimension(tas)



    else: 
        tasmax = xr.open_dataset(tasmax_read, autoclose=True, chunks={'time': 100}).load()
        tasmin = xr.open_dataset(tasmin_read, autoclose=True, chunks={'time': 100}).load()

        logger.debug('beginning')

        logger.debug('producing_tas')
        tas = make_tas_ds(tasmax, tasmin)
        tas = ctb._standardize_longitude_dimension(tas)
    
    tas.attrs.update(metadata)
    
    if interactive:
        return tas

    logger.debug('checking_tas_path')
    if not os.path.isdir(os.path.dirname(tas_write)):
        os.makedirs(os.path.dirname(tas_write))

    tas.to_netcdf(tas_write + '~', encoding={var : {'dtype': 'float32'} for var in tas.data_vars.keys()})
    logger.debug('write_tas_path')

    validate_tas(tas)
    logger.debug('validate_tas')
    os.rename(tas_write + '~', tas_write)


    logger.debug('job_complete')


if __name__ == '__main__':
    make_tas()

















    
            


