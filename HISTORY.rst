=======
History
=======

0.2.4 (2020-04-21)
------------------

* Compatibility patch allowing commands with underscores to be normalized to dashes in click app returned by jrnr.jrnr.slurm_runner. Thanks for the digging and issue raising @simondgreenhill!

0.2.3 (2018-01-16)
------------------

* Documentation & testing improvements

0.2.2 (2017-08-28)
-----------------------

* Update to documentation

* ``jrnr`` attempts to remove ``.lck`` files if there is a keyboard interrupt or system exit

0.2.1 (2017-07-31)
-----------------------

* Fix bug in ``slurm_runner.do_job`` which caused job duplication when race conditions on lock object creation occur (:issue:`3`)
* Infer filepath from passed function in ``slurm_runner``. Removes need to supply filepath argument in ``slurm_runner`` function calls (:issue:`5`)
* Adds ``return_index`` parameter to ``slurm_runner`` (:issue:`7`)

0.2.0 (2017-07-31)
------------------

* Fix interactive bug -- call interactive=True on ``slurm_runner.run_interactive()`` (:issue:`1`)
* Add slurm_runner as module-level import


0.1.2 (2017-07-28)
------------------

* Add interactive capability


0.1.1 (2017-07-28)
------------------

* Fix deployment bugs


0.1.0 (2017-07-28)
------------------

* First release on PyPI.
