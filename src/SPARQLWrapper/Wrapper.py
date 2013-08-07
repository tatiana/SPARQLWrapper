# -*- coding: utf-8 -*-
# epydoc
#
"""
@var JSON: to be used to set the return format to JSON
@var XML: to be used to set the return format to XML (SPARQL XML format or RDF/XML, depending on the query type). This is the default.
@var TURTLE: to be used to set the return format to Turtle
@var N3: to be used to set the return format to N3 (for most of the SPARQL services this is equivalent to Turtle)
@var RDF: to be used to set the return RDF Graph

@var POST: to be used to set HTTP POST
@var GET: to be used to set HTTP GET. This is the default.

@var SELECT: to be used to set the query type to SELECT. This is, usually, determined automatically.
@var CONSTRUCT: to be used to set the query type to CONSTRUCT. This is, usually, determined automatically.
@var ASK: to be used to set the query type to ASK. This is, usually, determined automatically.
@var DESCRIBE: to be used to set the query type to DESCRIBE. This is, usually, determined automatically.

@see: U{SPARQL Specification<http://www.w3.org/TR/rdf-sparql-query/>}
@authors: U{Ivan Herman<http://www.ivan-herman.net>}, U{Sergio Fernández<http://www.wikier.org>}, U{Carlos Tejo Alonso<http://www.dayures.net>}
@organization: U{World Wide Web Consortium<http://www.w3.org>}, U{Salzburg Research<http://www.salzburgresearch.at>} and U{Foundation CTIC<http://www.fundacionctic.org/>}.
@license: U{W3C® SOFTWARE NOTICE AND LICENSE<href="http://www.w3.org/Consortium/Legal/copyright-software">}
@requires: U{RDFLib<http://rdflib.net>} package.
"""

import sys
import urllib, urllib2
import base64
import re
import jsonlayer
import warnings
from SPARQLWrapper import __agent__
from SPARQLExceptions import QueryBadFormed, EndPointNotFound, EndPointInternalError
from SPARQLUtils import deprecated
from KeyCaseInsensitiveDict import KeyCaseInsensitiveDict

#  Possible output format keys...
JSON   = "json"
XML    = "xml"
TURTLE = "n3"
N3     = "n3"
RDF    = "rdf"
_allowedFormats = [JSON, XML, TURTLE, N3, RDF]

# Possible HTTP methods
POST = "POST"
GET  = "GET"
_allowedRequests = [POST, GET]

# Possible SPARQL/SPARUL query type
SELECT     = "SELECT"
CONSTRUCT  = "CONSTRUCT"
ASK        = "ASK"
DESCRIBE   = "DESCRIBE"
INSERT     = "INSERT"
DELETE     = "DELETE"
MODIFY     = "MODIFY"
_allowedQueryTypes = [SELECT, CONSTRUCT, ASK, DESCRIBE, INSERT, DELETE, MODIFY]

# Possible output format (mime types) that can be converted by the local script. Unfortunately,
# it does not work by simply setting the return format, because there is still a certain level of confusion
# among implementations.
# For example, Joseki returns application/javascript and not the sparql-results+json thing that is required...
# Ie, alternatives should be given...
# Andy Seaborne told me (June 2007) that the right return format is now added to his CVS, ie, future releases of
# joseki will be o.k., too. The situation with turtle and n3 is even more confusing because the text/n3 and text/turtle
# mime types have just been proposed and not yet widely used...
_SPARQL_DEFAULT  = ["application/sparql-results+xml", "application/rdf+xml", "*/*"]
_SPARQL_XML      = ["application/sparql-results+xml"]
_SPARQL_JSON     = ["application/sparql-results+json", "text/javascript", "application/json"]
_RDF_XML         = ["application/rdf+xml"]
_RDF_N3          = ["text/rdf+n3","application/n-triples","application/turtle","application/n3","text/n3","text/turtle"]
_ALL             = ["*/*"]
_RDF_POSSIBLE    = _RDF_XML + _RDF_N3
_SPARQL_POSSIBLE = _SPARQL_XML + _SPARQL_JSON + _RDF_XML + _RDF_N3
_SPARQL_PARAMS   = ["query"]

# This is very ugly. The fact is that the key for the choice of the output format is not defined. 
# Virtuoso uses 'format', joseki uses 'output', rasqual seems to use "results", etc. Lee Feigenbaum 
# told me that virtuoso also understand 'output' these days, so I removed 'format'. I do not have 
# info about the others yet, ie, for the time being I keep the general mechanism. Hopefully, in a 
# future release, I can get rid of that. However, these processors are (hopefully) oblivious to the 
# parameters they do not understand. So: just repeat all possibilities in the final URI. UGLY!!!!!!!
_returnFormatSetting = ["format","output","results"]

#######################################################################################################

class SPARQLWrapper :
    """
    Wrapper around an online access to a SPARQL Web entry point.

    The same class instance can be reused for subsequent queries. The values of the base Graph URI, return formats, etc,
    are retained from one query to the next (in other words, only the query string changes). The instance can also be
    reset to its initial values using the L{resetQuery} method.

    @cvar pattern: regular expression used to determine whether a query is of type L{CONSTRUCT}, L{SELECT}, L{ASK}, or L{DESCRIBE}.
    @type pattern: compiled regular expression (see the C{re} module of Python)
    @ivar baseURI: the URI of the SPARQL service
    """
    pattern = re.compile(r"""
                (?P<base>(\s*BASE\s*<.*?>)\s*)*
                (?P<prefixes>(\s*PREFIX\s+.+:\s*<.*?>)\s*)*
                (?P<queryType>(CONSTRUCT|SELECT|ASK|DESCRIBE|INSERT|DELETE|MODIFY))
    """, re.VERBOSE | re.IGNORECASE)
    def __init__(self,endpoint,updateEndpoint=None,returnFormat=XML,defaultGraph=None,agent=__agent__) :
        """
        Class encapsulating a full SPARQL call.
        @param endpoint: string of the SPARQL endpoint's URI
        @type endpoint: string
        @param updateEndpoint: string of the SPARQL endpoint's URI for update operations (if it's a different one)
        @type updateEndpoint: string
        @keyword returnFormat: Default: L{XML}.
        Can be set to JSON or Turtle/N3

        No local check is done, the parameter is simply
        sent to the endpoint. Eg, if the value is set to JSON and a construct query is issued, it
        is up to the endpoint to react or not, this wrapper does not check.

        Possible values:
        L{JSON}, L{XML}, L{TURTLE}, L{N3} (constants in this module). The value can also be set via explicit
        call, see below.
        @type returnFormat: string
        @keyword defaultGraph: URI for the default graph. Default is None, the value can be set either via an L{explicit call<addDefaultGraph>} or as part of the query string.
        @type defaultGraph: string
        """
        self.endpoint = endpoint
        self.updateEndpoint = updateEndpoint if updateEndpoint else endpoint
        self.agent = agent
        self.user = None
        self.passwd = None
        self.customParameters = {}
        self._defaultGraph = defaultGraph
        if defaultGraph : self.customParameters["default-graph-uri"] = defaultGraph
        if returnFormat in _allowedFormats :
            self.returnFormat = returnFormat
        else :
            self.returnFormat = XML
        self._defaultReturnFormat = self.returnFormat
        self.queryString = """SELECT * WHERE{ ?s ?p ?o }"""
        self.method    = GET
        self.queryType = SELECT

    def resetQuery(self) :
        """Reset the query, ie, return format, query, default or named graph settings, etc,
        are reset to their default values."""
        self.customParameters = {}
        if self._defaultGraph : self.customParameters["default-graph-uri"] = self._defaultGraph
        self.returnFormat = self._defaultReturnFormat
        self.method    = GET
        self.queryType = SELECT
        self.queryString = """SELECT * WHERE{ ?s ?p ?o }"""

    def setReturnFormat(self,format) :
        """Set the return format. If not an allowed value, the setting is ignored.

        @param format: Possible values: are L{JSON}, L{XML}, L{TURTLE}, L{N3}, L{RDF} (constants in this module). All other cases are ignored.
        @type format: string
        """
        if format in _allowedFormats :
            self.returnFormat = format

    @deprecated
    def addDefaultGraph(self,uri) :
        """
            Add a default graph URI.
            @param uri: URI of the graph
            @type uri: string
            @deprecated: use addCustomParameter("default-graph-uri", uri) instead of this method
        """
        self.addCustomParameter("default-graph-uri",uri)

    @deprecated
    def addNamedGraph(self,uri) :
        """
            Add a named graph URI.
            @param uri: URI of the graph
            @type uri: string
            @deprecated: use addCustomParameter("named-graph-uri", uri) instead of this method
        """
        self.addCustomParameter("named-graph-uri",uri)

    @deprecated
    def addExtraURITag(self,key,value) :
        """
            Some SPARQL endpoints require extra key value pairs.
            E.g., in virtuoso, one would add C{should-sponge=soft} to the query forcing 
            virtuoso to retrieve graphs that are not stored in its local database.
            @param key: key of the query part
            @type key: string
            @param value: value of the query part
            @type value: string
            @deprecated: use addCustomParameter(key, value) instead of this method
        """
        self.addCustomParameter(key,value)

    def addCustomParameter(self,name,value):
        """
            Some SPARQL endpoints allow extra key value pairs.
            E.g., in virtuoso, one would add C{should-sponge=soft} to the query forcing 
            virtuoso to retrieve graphs that are not stored in its local database.
            @param name: name 
            @type name: string
            @param value: value
            @type value: string
            @rtype: bool
        """
        if (name in _SPARQL_PARAMS):
            return False;
        else:
            self.customParameters[name] = value
            return True

    def setCredentials(self,user,passwd) :
        """
            Set the credentials for querying the current endpoint
            @param user: username
            @type user: string
            @param passwd: password
            @type passwd: string
        """
        self.user = user
        self.passwd = passwd

    def setQuery(self,query) :
        """
            Set the SPARQL query text. Note: no check is done on the validity of the query 
            (syntax or otherwise) by this module, except for testing the query type (SELECT, 
            ASK, etc). Syntax and validity checking is done by the SPARQL service itself.
            @param query: query text
            @type query: string
            @bug: #2320024
        """
        self.resetQuery()
        self.queryString = query
        self.queryType   = self._parseQueryType(query)

    def _parseQueryType(self,query) :
        """
            Parse the SPARQL query and return its type (ie, L{SELECT}, L{ASK}, etc).

            Note that the method returns L{SELECT} if nothing is specified. This is just to get all other
            methods running; in fact, this means that the query is erronous, because the query must be,
            according to the SPARQL specification, one of Select, Ask, Describe, or Construct. The
            SPARQL endpoint should raise an exception (via urllib) for such syntax error.

            @param query: query text
            @type query: string
            @rtype: string
        """
        try:
            r_queryType = self.pattern.search(query).group("queryType").upper()
        except AttributeError:
            r_queryType = None
    
        if r_queryType in _allowedQueryTypes :
            return r_queryType
        else :
            #raise Exception("Illegal SPARQL Query; must be one of SELECT, ASK, DESCRIBE, or CONSTRUCT")
            warnings.warn("unknown query type", RuntimeWarning)
            return SELECT

    def setMethod(self,method) :
        """Set the invocation method. By default, this is L{GET}, but can be set to L{POST}.
        @param method: should be either L{GET} or L{POST}. Other cases are ignored.
        """
        if method in _allowedRequests : self.method = method

    def setUseKeepAlive(self):
        """Make urllib2 use keep-alive.
        @raise ImportError: when could not be imported urlgrabber.keepalive.HTTPHandler
        """
        try:
            from urlgrabber.keepalive import HTTPHandler
            keepalive_handler = HTTPHandler()
            opener = urllib2.build_opener(keepalive_handler)
            urllib2.install_opener(opener)
        except ImportError:
            warnings.warn("urlgrabber not installed in the system. The execution of this method has no effect.")

    def _getURI(self) :
        """Return the URI as sent (or to be sent) to the SPARQL endpoint. The URI is constructed
        with the base URI given at initialization, plus all the other parameters set.
        @return: URI
        @rtype: string
        """
        finalQueryParameters = self.customParameters.copy()
        if self.queryType in [INSERT, DELETE, MODIFY]:
            uri = self.updateEndpoint
            finalQueryParameters["update"] = self.queryString
        else:
            uri = self.endpoint
            finalQueryParameters["query"] = self.queryString

        # This is very ugly. The fact is that the key for the choice of the output format is not defined. 
        # Virtuoso uses 'format',sparqler uses 'output'
        # However, these processors are (hopefully) oblivious to the parameters they do not understand. 
        # So: just repeat all possibilities in the final URI. UGLY!!!!!!!
        for f in _returnFormatSetting: finalQueryParameters[f] = self.returnFormat

        return uri + "?" + urllib.urlencode(dict([k, v.encode("utf-8")] for k, v in finalQueryParameters.items()))

    def _createRequest(self) :
        """Internal method to create request according a HTTP method. Returns a
        C{urllib2.Request} object of the urllib2 Python library
        @return: request
        """
        if self.queryType in [SELECT, ASK]:
            if self.returnFormat == XML:
                acceptHeader = ",".join(_SPARQL_XML)
            elif self.returnFormat == JSON:
                acceptHeader = ",".join(_SPARQL_JSON)
            else :
                acceptHeader = ",".join(_ALL)
        elif self.queryType in [INSERT, DELETE, MODIFY]:
            acceptHeader = "*/*"
        else:
            if self.returnFormat == N3 or self.returnFormat == TURTLE :
                acceptHeader = ",".join(_RDF_N3)
            elif self.returnFormat == XML :
                acceptHeader = ",".join(_RDF_XML)
            else :
                acceptHeader = ",".join(_ALL)

        if self.method == POST :
            # by POST
            if self.queryType in [INSERT, DELETE, MODIFY]:
                uri = self.updateEndpoint
                values = { "update" : self.queryString }
            else:
                uri = self.endpoint
                values = { "query" : self.queryString }
            request = urllib2.Request(uri)
            request.add_header("Content-Type", "application/x-www-url-form-urlencoded")
            data = urllib.urlencode(values)
            if isinstance(data, unicode):
                data = data.encode("utf-8")
            request.add_data(data)
        else:
            # by GET
            # Some versions of Joseki do not work well if no Accept header is given.
            # Although it is probably o.k. in newer versions, it does not harm to have that set once and for all...
            request = urllib2.Request(self._getURI())

        request.add_header("User-Agent", self.agent)
        request.add_header("Accept", acceptHeader)
        if (self.user and self.passwd):
            request.add_header("Authorization", "Basic " + base64.encodestring("%s:%s" % (self.user,self.passwd)))
        return request

    def _query(self):
        """Internal method to execute the query. Returns the output of the
        C{urllib2.urlopen} method of the standard Python library

        @return: tuples with the raw request plus the expected format
        """
        request = self._createRequest()
        try:
            response = urllib2.urlopen(request)
            return (response, self.returnFormat)
        except urllib2.HTTPError, e:
            if e.code == 400:
                raise QueryBadFormed(e.read())
            elif e.code == 404:
                raise EndPointNotFound(e.read())
            elif e.code == 500:
                raise EndPointInternalError(e.read())
            else:
                raise e
            return (None, self.returnFormat)
    
    def query(self) :
        """
            Execute the query.
            Exceptions can be raised if either the URI is wrong or the HTTP sends back an error (this is also the
            case when the query is syntactically incorrect, leading to an HTTP error sent back by the SPARQL endpoint).
            The usual urllib2 exceptions are raised, which therefore cover possible SPARQL errors, too.

            Note that some combinations of return formats and query types may not make sense. For example,
            a SELECT query with Turtle response is meaningless (the output of a SELECT is not a Graph), or a CONSTRUCT
            query with JSON output may be a problem because, at the moment, there is no accepted JSON serialization
            of RDF (let alone one implemented by SPARQL endpoints). In such cases the returned media type of the result is
            unpredictable and may differ from one SPARQL endpoint implementation to the other. (Endpoints usually fall
            back to one of the "meaningful" formats, but it is up to the specific implementation to choose which
            one that is.)

            @return: query result
            @rtype: L{QueryResult} instance
        """
        return QueryResult(self._query())

    def queryAndConvert(self) :
        """Macro like method: issue a query and return the converted results.
        @return: the converted query result. See the conversion methods for more details.
        """
        res = self.query()
        return res.convert()

#######################################################################################################

class QueryResult :
    """
    Wrapper around an a query result. Users should not create instances of this class, it is
    generated by a L{SPARQLWrapper.query} call. The results can be
    converted to various formats, or used directly.

    If used directly: the class gives access to the direct http request results
    L{self.response}: it is a file-like object with two additional methods: C{geturl()} to
    return the URL of the resource retrieved and
    C{info()} that returns the meta-information of the HTTP result as a dictionary-like object
    (see the urllib2 standard library module of Python).

    For convenience, these methods are also available on the instance. The C{__iter__} and
    C{next} methods are also implemented (by mapping them to L{self.response}). This means that the
    common idiom::
     for l in obj : do_something_with_line(l)
    would work, too.

    @ivar response: the direct HTTP response; a file-like object, as return by the C{urllib2.urlopen} library call.
    """
    def __init__(self,result) :
        """
        @param result: HTTP response stemming from a L{SPARQLWrapper.query} call, or a tuple with the expected format: (response,format)
        """
        if (type(result) == tuple):
            self.response = result[0]
            self.requestedFormat = result[1]
        else:
            self.response = result
        """Direct response, see class comments for details"""

    def geturl(self) :
        """Return the URI of the original call.
        @return: URI
        @rtype: string
        """
        return self.response.geturl()

    def info(self) :
        """Return the meta-information of the HTTP result.
        @return: meta information
        @rtype: dictionary
        """
        return KeyCaseInsensitiveDict(self.response.info())

    def __iter__(self) :
        """Return an iterator object. This method is expected for the inclusion
        of the object in a standard C{for} loop.
        """
        return self.response.__iter__()

    def next(self) :
        """Method for the standard iterator."""
        return self.response.next()

    def setJSONModule(self,module) :
        """Set the Python module for encoding JSON data. If not an allowed value, the setting is ignored.
           JSON modules supported:
             - ``simplejson``: http://code.google.com/p/simplejson/
             - ``cjson``: http://pypi.python.org/pypi/python-cjson
             - ``json``: This is the version of ``simplejson`` that is bundled with the
               Python standard library since version 2.6
               (see http://docs.python.org/library/json.html)
        @param module: Possible values: are L{simplejson}, L{cjson}, L{json}. All other cases raise a ValueError exception.
        @type module: string
        """
        jsonlayer.use(module)

    def _convertJSON(self) :
        """
        Convert a JSON result into a Python dict. This method can be overwritten in a subclass
        for a different conversion method.
        @return: converted result
        @rtype: Python dictionary
        """
        return jsonlayer.decode(self.response.read().decode("utf-8"))
        # patch to solve bug #2781984
        # later updated with a trick from http://bob.pythonmac.org/archives/2008/10/02/python-26-released-now-with-json/
        #try:
        #    import simplejson as json
        #except ImportError:
        #    import json
        #return json.load(self.response)

    def _convertXML(self) :
        """
        Convert an XML result into a Python dom tree. This method can be overwritten in a
        subclass for a different conversion method.
        @return: converted result
        @rtype: PyXlib DOM node
        """
        from xml.dom.minidom import parse
        return parse(self.response)

    def _convertRDF(self) :
        """
        Convert an RDF/XML result into an RDFLib triple store. This method can be overwritten
        in a subclass for a different conversion method.
        @return: converted result
        @rtype: RDFLib Graph
        """
        try:
            from rdflib.graph import ConjunctiveGraph
        except ImportError:
            from rdflib import ConjunctiveGraph
        retval = ConjunctiveGraph()
        # this is a strange hack. If the publicID is not set, rdflib (or the underlying xml parser) makes a funny
        #(and, as far as I could see, meaningless) error message...
        retval.load(self.response,publicID=' ')
        return retval

    def _convertN3(self) :
        """
        Convert an RDF Turtle/N3 result into a string. This method can be overwritten in a subclass
        for a different conversion method.
        @return: converted result
        @rtype: string
        """
        return self.response.read()

    def convert(self) :
        """
        Encode the return value depending on the return format:
            - in the case of XML, a DOM top element is returned;
            - in the case of JSON, a simplejson conversion will return a dictionary;
            - in the case of RDF/XML, the value is converted via RDFLib into a Graph instance.
        In all other cases the input simply returned.

        @return: the converted query result. See the conversion methods for more details.
        """
        if ("content-type" in self.info()):
            ct = self.info()["content-type"]
            if True in [ct.find(q) != -1 for q in _SPARQL_XML] :
                if (self.requestedFormat != XML):
                    warnings.warn("Format requested was %s, but XML (%s) has been returned by the endpoint" % (self.requestedFormat.upper(), ct), RuntimeWarning)
                return self._convertXML()
            elif True in [ct.find(q) != -1 for q in _SPARQL_JSON]  :
                if (self.requestedFormat != JSON):
                    warnings.warn("Format requested was %s, but JSON (%s) has been returned by the endpoint" % (self.requestedFormat.upper(), ct), RuntimeWarning)
                return self._convertJSON()
            elif True in [ct.find(q) != -1 for q in _RDF_XML] :
                if (self.requestedFormat != RDF and self.requestedFormat != XML):
                    warnings.warn("Format requested was %s, but RDF/XML (%s) has been returned by the endpoint" % (self.requestedFormat.upper(), ct), RuntimeWarning)
                return self._convertRDF()
            elif True in [ct.find(q) != -1 for q in _RDF_N3] :
                if (self.requestedFormat != N3 and self.requestedFormat != TURTLE):
                    warnings.warn("Format requested was %s, but N3 (%s) has been returned by the endpoint" % (self.requestedFormat.upper(), ct), RuntimeWarning)
                return self._convertN3()
            else :
                warnings.warn("unknown response content type, returning raw response...", RuntimeWarning)
                return self.response.read()
        else :
            warnings.warn("unknown response content type, returning raw response...", RuntimeWarning)
            return self.response.read()

    def print_results(self, minWidth=None):
        results = self._convertJSON()
        if minWidth :
            width = self.__get_results_width(results, minWidth)
        else :
            width = self.__get_results_width(results)
        index = 0
        for var in results["head"]["vars"] :
            print ("?" + var).ljust(width[index]),"|",
            index += 1
        print
        print "=" * (sum(width) + 3 * len(width))
        for result in results["results"]["bindings"] :
            index = 0
            for var in results["head"]["vars"] :
                print result[var]["value"].ljust(width[index]),"|",
                index += 1
            print

    def __get_results_width(self, results, minWidth=2):
        width = []
        for var in results["head"]["vars"] :
            width.append(max(minWidth, len(var)+1))
        for result in results["results"]["bindings"] :
            index = 0
            for var in results["head"]["vars"] :
                width[index] = max(width[index], len(result[var]["value"]))
                index =+ 1
        return width

