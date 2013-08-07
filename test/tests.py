# -*- coding: utf8 -*-
#!/usr/bin/python

import sys
import unittest
try:
    from rdflib.graph import ConjunctiveGraph
except ImportError:
    from rdflib import ConjunctiveGraph
from SPARQLWrapper import SPARQLWrapper, XML, N3, JSON, POST, GET, SELECT, CONSTRUCT, ASK, DESCRIBE
from SPARQLWrapper.Wrapper import _SPARQL_DEFAULT, _SPARQL_XML, _SPARQL_JSON, _SPARQL_POSSIBLE, _RDF_XML, _RDF_N3, _RDF_POSSIBLE
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed

try:
    from urllib.error import HTTPError   # Python 3
except ImportError:
    from urllib2 import HTTPError        # Python 2

try:
    bytes   # Python 2.6 and above
except NameError:
    bytes = str

endpoint = "http://dbpedia.org/sparql"

prefixes = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

selectQuery =  """
    SELECT ?label
    WHERE {
    <http://dbpedia.org/resource/Asturias> rdfs:label ?label .
    }
"""

constructQuery =  """
    CONSTRUCT {
        _:v rdfs:label ?label .
        _:v rdfs:comment "this is only a mock node to test library"
    }
    WHERE {
        <http://dbpedia.org/resource/Asturias> rdfs:label ?label .
    }
"""

queryBadFormed = """
    PREFIX prop: <http://dbpedia.org/property/>
    PREFIX res: <http://dbpedia.org/resource/>
    FROM <http://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&should-sponge=&query=%0D%0ACONSTRUCT+%7B%0D%0A++++%3Chttp%3A%2F%2Fdbpedia.org%2Fresource%2FBudapest%3E+%3Fp+%3Fo.%0D%0A%7D%0D%0AWHERE+%7B%0D%0A++++%3Chttp%3A%2F%2Fdbpedia.org%2Fresource%2FBudapest%3E+%3Fp+%3Fo.%0D%0A%7D%0D%0A&format=application%2Frdf%2Bxml>
    SELECT ?lat ?long
    WHERE {
        res:Budapest prop:latitude ?lat;
        prop:longitude ?long.
    }      
"""

queryManyPrefixes = """
    PREFIX conf: <http://richard.cyganiak.de/2007/pubby/config.rdf#>
    PREFIX meta: <http://example.org/metadata#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
    PREFIX dbpedia: <http://dbpedia.org/resource/>
    PREFIX o: <http://dbpedia.org/ontology/>
    PREFIX p: <http://dbpedia.org/property/>
    PREFIX yago: <http://dbpedia.org/class/yago/>
    PREFIX units: <http://dbpedia.org/units/>
    PREFIX geonames: <http://www.geonames.org/ontology#>
    PREFIX prv: <http://purl.org/net/provenance/ns#>
    PREFIX prvTypes: <http://purl.org/net/provenance/types#>
    PREFIX foo: <http://purl.org/foo>

    SELECT ?label
    WHERE {
        <http://dbpedia.org/resource/Asturias> rdfs:label ?label .
    }
"""

class SPARQLWrapperTests(unittest.TestCase):

    def __generic(self, query, returnFormat, method):
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(prefixes + query)
        sparql.setReturnFormat(returnFormat)
        sparql.setMethod(method)
        try:
            result = sparql.query()
        except HTTPError:
            # An ugly way to get the exception, but the only one that works
            # both on Python 2.5 and Python 3.
            e = sys.exc_info()[1]
            if e.code == 400:
                sys.stdout.write("Bad Request, probably query is not well formed")
            else:
                sys.stdout.write(str(e))
            sys.stdout.write("\n")
            return False
        else:
            return result


    def testSelectByGETinXML(self):
        result = self.__generic(selectQuery, XML, GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_XML])
        results = result.convert()
        results.toxml()

    def testSelectByPOSTinXML(self):
        result = self.__generic(selectQuery, XML, POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_XML])
        results = result.convert()
        results.toxml()

    def testSelectByGETinN3(self):
        result = self.__generic(selectQuery, N3, GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_N3])
        self.assertTrue(True in [one in ct for one in _SPARQL_POSSIBLE])
        results = result.convert()
        self.assertEqual(type(results), bytes)

    def testSelectByPOSTinN3(self):
        result = self.__generic(selectQuery, N3, POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_XML])
        self.assertTrue(True in [one in ct for one in _SPARQL_POSSIBLE])
        results = result.convert()
        results.toxml()

    def testSelectByGETinJSON(self):
        result = self.__generic(selectQuery, JSON, GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_JSON])
        results = result.convert()
        self.assertEqual(type(results), dict)

    def testSelectByPOSTinJSON(self):
        result = self.__generic(selectQuery, JSON, POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_JSON])
        results = result.convert()
        self.assertEqual(type(results), dict)

    def testSelectByGETinUnknow(self):
        result = self.__generic(selectQuery, "foo", GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_POSSIBLE])
        results = result.convert()

    def testSelectByPOSTinUnknow(self):
        result = self.__generic(selectQuery, "bar", POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _SPARQL_POSSIBLE])
        results = result.convert()

    def testConstructByGETinXML(self):
        result = self.__generic(constructQuery, XML, GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_XML])
        results = result.convert()
        self.assertEqual(type(results), ConjunctiveGraph)

    def testConstructByPOSTinXML(self):
        result = self.__generic(constructQuery, XML, POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_XML])
        results = result.convert()
        self.assertEqual(type(results), ConjunctiveGraph)

    def testConstructByGETinN3(self):
        result = self.__generic(constructQuery, N3, GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_N3])
        results = result.convert()
        self.assertEqual(type(results), bytes)

    def testConstructByPOSTinN3(self):
        result = self.__generic(constructQuery, N3, POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_N3])
        results = result.convert()
        self.assertEqual(type(results), bytes)

    def testConstructByGETinJSON(self):
        result = self.__generic(constructQuery, JSON, GET)
        ct = result.info()["content-type"]
        assert True in [one in ct for one in _RDF_POSSIBLE], ct
        results = result.convert()
        self.assertEqual(type(results), ConjunctiveGraph)

    def testConstructByPOSTinJSON(self):
        result = self.__generic(constructQuery, JSON, POST)
        ct = result.info()["content-type"]
        assert True in [one in ct for one in _RDF_POSSIBLE], ct
        results = result.convert()
        self.assertEqual(type(results), bytes)

    def testConstructByGETinUnknow(self):
        result = self.__generic(constructQuery, "foo", GET)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_POSSIBLE])
        results = result.convert()
        self.assertEqual(type(results), ConjunctiveGraph)

    def testConstructByPOSTinUnknow(self):
        result = self.__generic(constructQuery, "bar", POST)
        ct = result.info()["content-type"]
        self.assertTrue(True in [one in ct for one in _RDF_POSSIBLE])
        results = result.convert()
        self.assertEqual(type(results), ConjunctiveGraph)

    def testQueryBadFormed(self):
        self.assertRaises(QueryBadFormed, self.__generic, queryBadFormed, XML, GET) 

#    def testQueryManyPrefixes(self):        
#        result = self.__generic(queryManyPrefixes, XML, GET)


if __name__ == "__main__":
    unittest.main()

