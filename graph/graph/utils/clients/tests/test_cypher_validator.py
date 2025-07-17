from akcent_graph.utils.clients.cypher_validator.CypherLexer import serializedATN as serailizedATN_CL
from akcent_graph.utils.clients.cypher_validator.CypherParser import serializedATN as serailizedATN_CP


def test_serailizedATN_CL():
    value = serailizedATN_CL()
    assert len(value) == 15822
    assert isinstance(value, str)


def test_serailizedATN_CP():
    value = serailizedATN_CP()
    assert len(value) == 20197
    assert isinstance(value, str)
