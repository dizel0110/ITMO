import enum

from akcent_graph.apps.medaggregator.helpers import DataImportanceFeature


class QueryAnamnesis(enum.Enum):
    """
    Cypher query templates for getting anamnesis.
    =============================================

    Variables:
    ----------
    \n\tDISEASE_OF_PATIENT
    \n\tDISEASE_TRUE_OR_NOT

    """

    DISEASE_OF_PATIENT = """MATCH (n:NeoProtocol)-[r]-(m:NeoDisease)
    WHERE r.patient_id = {patient_id}
    RETURN DISTINCT m.name AS disease, n.name AS protocol
    """
    DISEASE_TRUE_OR_NOT = f"""MATCH (n)-[r]-(m:NeoProtocol)
    WHERE r.protocol_pk = |protocol_pk| AND r.chain CONTAINS '|chain|' AND r.attention = {DataImportanceFeature.TRUE_IMPORTANCE.value}  AND r.patient_id = |patient_id|
    RETURN COUNT(n) > 0
    """
