"""
Constant cypher queries for medaggregator.
==========================================

Classes:
----------
DataCypherQueriesNeoSpider

Variables:
----------

Dependencies:
-------------
enum

"""

import enum


class DataCypherQueriesNeoSpider(enum.Enum):
    """
    Constants to NeoSpider ability.
    ===============================

    Variables:
    ----------
    \n\tNODES_WITHOUT_PARENTS cypher query to get nodes without parents
    \n\tPARENT_AND_CHILD_CLASSES_FOR_CLASS cypher query to define parent and child class name
    \n\tFIND_DOUBLES cypher query to find doubles
    \n\tNOT_MATCHED_DISEASES cypher query to find not matched neodisease nodes
    \n\tTRANSFER_ALL_RELATIONSHIPS cypher query to transfer all relationships only by cypher
    \n\tFIND_ALL_RELATIONSHIPS cypher query to find all relationships by node id
    \n\tTRANSFER_RELATIONSHIP cypher query to transfer (create) one relationship between two nodes
    \n\tRENAME_LABEL cypher query to rename label of node with id
    """

    NODES_WITHOUT_PARENTS = """\
        MATCH (n)-[r]->(m) WHERE r.parent_not_found=$parent_value
        RETURN labels(n), properties(n), r
        """
    PARENT_AND_CHILD_CLASSES_FOR_CLASS = """\
        MATCH (current:`{current_class_name}`)
        OPTIONAL MATCH (current)-[downRel]->(lowerClass)
        WHERE downRel.patient_id = -1 and downRel.protocol_pk = -1
        OPTIONAL MATCH (upperClass)-[upRel]->(current)
        WHERE upRel.patient_id = -1 and upRel.protocol_pk = -1
        RETURN collect(DISTINCT labels(current)[0]) AS CurrentClass,
        collect(DISTINCT labels(lowerClass)[0]) AS LowerClasses,
        collect(DISTINCT labels(upperClass)[0]) AS UpperClasses;
        """
    FIND_DOUBLES = """\
        MATCH (n:`{current_class_name}`)
        WITH n.name AS name, COLLECT(n) AS nodes
        WHERE SIZE(nodes) > 1
        UNWIND nodes AS nodeInstance
        WITH name, ID(nodeInstance) AS id, SIZE(nodes) AS duplicate_count
        RETURN name, COLLECT(id) AS ids, duplicate_count
        ORDER BY duplicate_count DESC;
        """
    NOT_MATCHED_DISEASES = """\
        MATCH (n:NeoDisease)
        WHERE NOT EXISTS (n.level)
        RETURN n.name, id(n);
        """
    TRANSFER_ALL_RELATIONSHIPS = """\
        MATCH (source:NeoDisease)
        WHERE id(source) = {source_id}
        MATCH (target:NeoDisease)
        WHERE id(target) = {target_id}
        MATCH (source)-[rels]-()
        WITH source, target, rels, type(rels) AS relType
        CREATE (target)-[newRels:TRANSFERRED]->()
        SET newRels += rels
        DETACH DELETE source;
        """
    FIND_ALL_RELATIONSHIPS = """\
        MATCH (source)
        WHERE id(source) = {source_id}
        MATCH (source)-[rels]-()
        RETURN rels;
        """
    TRANSFER_RELATIONSHIP = """\
        MATCH (startNode), (endNode)
        WHERE id(startNode) = {start_id} AND id(endNode) = {end_id}
        CREATE (startNode)-[rel:`{relationship_type}` {relationship_properties}]->(endNode)
        RETURN startNode, endNode, rel
        """
    RENAME_LABEL = """\
        MATCH (current)
        WHERE id(current) = {current_id}
        REMOVE current:`{old_label}`
        SET current:`{new_label}`
        """
