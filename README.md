SPARQLWrapper
=============

SPARQLWrapper fork. Original source code available at: https://sourceforge.net/projects/sparql-wrapper/

It has two differences when compared to the upstream source:
- Support to digest authentication
- Fixes related to Python 3

This project initial commit is a copy of r177 (~ release 1.5.3) and was cloned (checked out) from the official SVN repository, using:

$ svn checkout svn://svn.code.sf.net/p/sparql-wrapper/code/trunkls sparql-wrapper-code

Running test suite
------------------

$ make tests

Note that 3 tests fail from the original repository, as described on:
- http://pastebin.com/LRnnLuU4
- http://pastebin.com/CYZaKyJe

Will check this soon.