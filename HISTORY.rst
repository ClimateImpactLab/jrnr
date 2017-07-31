=======
History
=======

0.2.1 (Current Version)
-----------------------

* Fix bug in ``slurm_runner.do_job`` which caused job duplication when race conditions on lock object creation occur (:issue:`3`)


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
