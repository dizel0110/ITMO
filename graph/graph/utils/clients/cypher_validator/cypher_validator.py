# type: ignore
# flake8: noqa
import logging

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from akcent_graph.utils.clients.cypher_validator.CypherLexer import CypherLexer
from akcent_graph.utils.clients.cypher_validator.CypherParser import CypherParser

logger = logging.getLogger(__name__)


class CypherErrorListener(ErrorListener):
    def __init__(self):
        super(CypherErrorListener, self).__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, error):
        self.errors.append(f'line {line}:{column} {msg}')

    def has_errors(self):
        return len(self.errors) > 0

    def get_errors(self):
        return self.errors


def validate_query(query):
    input_stream = InputStream(query)
    lexer = CypherLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CypherParser(stream)
    error_listener = CypherErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    try:
        parser.oC_Cypher()
        if error_listener.has_errors():
            logger.info('Cypher query is invalid:')
            for error in error_listener.get_errors():
                logger.info(error)
            return False
        else:
            logger.info('Cypher query is valid.')
            return True
    except ValueError as err:
        logger.info('Cypher query is invalid: %s', err)
        return False
