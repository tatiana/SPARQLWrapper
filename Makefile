USER=dba
PWD=dba
VIRTUOSO_HOST=localhost

setup:
	isql $(VIRTUOSO_HOST) $(USER) $(PWD) ./scripts/virtuoso_setup.isql

tests:
	PYTHONPATH=src/:$PYTHONPATH python test/tests.py
